"""Persistent hourly league core. Run with python -m reliefroute.league.

SQLite is for a single worker on a persistent volume, not ephemeral Cloud Run
storage. Public hosting must supply durable storage before enabling this mode.
"""
import argparse
import hashlib
import hmac
import json
import secrets
import sqlite3
import time
import uuid
from contextlib import contextmanager

from .bots import configured_bot, validate_config
from .engine import Engine, canonical
from .scenario import hourly_scenario
from .program_bot import program_bot, VERSION as PROGRAM_VERSION


def hour_id(timestamp=None):
    return int(time.time() if timestamp is None else timestamp) // 3600


def rating_deltas(scores):
    """Pairwise actual minus neutral expectation; ties contribute zero.

    Integer micro-points avoid floating drift. This is transparent rank-point
    scoring, not Elo; one round can change a rating by at most 16 points.
    """
    n = len(scores)
    if n < 2:
        return {key: 0 for key in scores}
    # Keep each pair exactly zero-sum, including non-divisible field sizes.
    unit = 16000 // (n - 1)
    return {key: unit * sum((score > other) - (score < other)
                           for other in scores.values())
            for key, score in scores.items()}


class League:
    def __init__(self, path):
        self.path = str(path)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS bots (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, config TEXT NOT NULL,
                    created_hour INTEGER NOT NULL, active INTEGER NOT NULL DEFAULT 1,
                    rating INTEGER NOT NULL DEFAULT 1000000, played INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS rounds (
                    hour INTEGER PRIMARY KEY, scenario TEXT NOT NULL, completed INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS bot_owners (
                    bot_id TEXT PRIMARY KEY, token_hash TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS bot_programs (
                    bot_id TEXT PRIMARY KEY, source TEXT NOT NULL, version TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS results (
                    hour INTEGER NOT NULL, bot_id TEXT NOT NULL, name TEXT NOT NULL,
                    config TEXT NOT NULL, score TEXT NOT NULL, delta INTEGER NOT NULL,
                    replay TEXT, PRIMARY KEY(hour, bot_id)
                );
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def register(self, name, config, timestamp=None):
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 40:
            raise ValueError('Bot name must contain 1–40 characters')
        config = validate_config(config)
        bot_id = uuid.uuid4().hex
        with self.connect() as db:
            db.execute('INSERT INTO bots(id,name,config,created_hour) VALUES(?,?,?,?)',
                       (bot_id, name.strip(), canonical(config), hour_id(timestamp)))
        return bot_id

    def deploy(self, name, config, source=None):
        """Issue a one-time management capability; never expose it publicly."""
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 40:
            raise ValueError('Bot name must contain 1–40 characters')
        config = validate_config(config)
        if source is not None:
            program_bot(source)
        bot_id, token = uuid.uuid4().hex, secrets.token_urlsafe(32)
        created = hour_id()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT COUNT(*) FROM bots').fetchone()[0] >= 100:
                raise ValueError('Pilot registration limit reached')
            db.execute('INSERT INTO bots(id,name,config,created_hour) VALUES(?,?,?,?)',
                       (bot_id, name.strip(), canonical(config), created))
            db.execute('INSERT INTO bot_owners VALUES(?,?)',
                       (bot_id, hashlib.sha256(token.encode()).hexdigest()))
            if source is not None:
                db.execute('INSERT INTO bot_programs VALUES(?,?,?)', (bot_id, source, PROGRAM_VERSION))
        return {'id': bot_id, 'token': token, 'starts_hour': created + 1}

    def set_active(self, bot_id, token, active):
        if not isinstance(token, str) or not isinstance(bot_id, str) or type(active) is not bool:
            raise ValueError('Invalid management request')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            owner = db.execute('SELECT token_hash FROM bot_owners WHERE bot_id=?', (bot_id,)).fetchone()
            if not owner or not hmac.compare_digest(owner['token_hash'], hashlib.sha256(token.encode()).hexdigest()):
                raise PermissionError('Invalid management token')
            # On resumption wait until next boundary, same as newly deployed bots.
            db.execute('UPDATE bots SET active=?,created_hour=? WHERE id=?',
                       (int(active), hour_id(), bot_id))

    def run_hour(self, hour=None):
        hour = hour_id() if hour is None else hour
        scenario = hourly_scenario(hour)
        with self.connect() as db:
            # Serialize selection, simulation and settlement. A crash rolls back
            # everything; two workers cannot settle the same round twice.
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM rounds WHERE hour=?', (hour,)).fetchone():
                return False
            latest = db.execute('SELECT MAX(hour) FROM rounds').fetchone()[0]
            if latest is not None and hour < latest:
                raise ValueError('Cannot settle historical rounds out of order')
            # Freeze participants at the hour boundary. New entries start next hour.
            bots = db.execute('SELECT * FROM bots WHERE active=1 AND created_hour<? ORDER BY id',
                              (hour,)).fetchall()
            records = {}
            for bot in bots:
                program = db.execute('SELECT source,version FROM bot_programs WHERE bot_id=?', (bot['id'],)).fetchone()
                policy = program_bot(program['source']) if program else configured_bot(json.loads(bot['config']))
                record = Engine(scenario).run(policy)
                record.update(bot='custom', bot_id=bot['id'], bot_name=bot['name'],
                              bot_config=json.loads(bot['config']), bot_version='1.0', league_hour=hour)
                if program:
                    record.update(bot='program', bot_version=program['version'],
                                  source_hash=hashlib.sha256(program['source'].encode()).hexdigest())
                    record.pop('bot_config')
                records[bot['id']] = record
            deltas = rating_deltas({key: value['score']['total'] for key, value in records.items()})
            # Only the latest round retains large replays; compact results persist.
            db.execute('UPDATE results SET replay=NULL WHERE replay IS NOT NULL')
            db.execute('INSERT INTO rounds VALUES(?,?,1)', (hour, canonical(scenario)))
            for bot in bots:
                record, delta = records[bot['id']], deltas[bot['id']]
                db.execute('INSERT INTO results VALUES(?,?,?,?,?,?,?)',
                           (hour, bot['id'], bot['name'], bot['config'], canonical(record['score']),
                            delta, canonical(record)))
                db.execute('UPDATE bots SET rating=rating+?,played=played+1 WHERE id=?',
                           (delta, bot['id']))
        return True

    def leaderboard(self):
        with self.connect() as db:
            return [dict(row) for row in db.execute(
                'SELECT id,name,rating,played,active FROM bots ORDER BY rating DESC,id')]

    def current(self):
        with self.connect() as db:
            row = db.execute('SELECT hour,scenario FROM rounds ORDER BY hour DESC LIMIT 1').fetchone()
            if row is None:
                return {'hour': None, 'results': []}
            results = []
            for item in db.execute('SELECT bot_id,name,score,delta FROM results WHERE hour=? ORDER BY bot_id',
                                   (row['hour'],)):
                item = dict(item)
                item['score'] = json.loads(item['score'])
                results.append(item)
            # Complete scenario plans are not exposed until the round is settled.
            return {'hour': row['hour'], 'scenario': json.loads(row['scenario']), 'results': results}

    def replay(self, hour, bot_id):
        with self.connect() as db:
            row = db.execute('SELECT replay FROM results WHERE hour=? AND bot_id=?',
                             (hour, bot_id)).fetchone()
            return json.loads(row['replay']) if row and row['replay'] else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True, help='Durable SQLite path')
    parser.add_argument('--once', action='store_true', help='Settle the current UTC hour and exit')
    args = parser.parse_args()
    league = League(args.db)
    while True:
        league.run_hour()
        if args.once:
            break
        time.sleep(min(30, 3600 - time.time() % 3600))


if __name__ == '__main__':
    main()
