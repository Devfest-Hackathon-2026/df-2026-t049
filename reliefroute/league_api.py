"""Opt-in public league API shared by local and production HTTP adapters."""
import json
import re
import sqlite3
from http import HTTPStatus as S
from urllib.parse import parse_qs, urlsplit

from .league import hour_id
from .league_store import configured_league, StorageUnavailable
from .bots import DEFAULT_CONFIG

MIME = 'application/json; charset=utf-8'


def handle(target, method='GET', body=b'', content_type=''):
    if len(target) > 2048 or len(body) > 8192:
        return S.REQUEST_ENTITY_TOO_LARGE, {'error': 'Request too large'}, MIME
    url = urlsplit(target)
    try:
        league = configured_league()
        if league is None:
            return S.SERVICE_UNAVAILABLE, {'error': 'Hourly league has not been enabled on this server'}, MIME
        if method in ('GET', 'HEAD'):
            if url.path == '/api/league' and not url.query:
                return S.OK, {'current': league.current(), 'ranking': league.leaderboard(),
                              'server_hour': hour_id(), 'next_round_at': (hour_id() + 1) * 3600,
                              'rating_scale': 1000}, MIME
            if url.path == '/api/league/replay':
                query = parse_qs(url.query, keep_blank_values=True, max_num_fields=2)
                if set(query) != {'hour', 'bot'} or any(len(v) != 1 for v in query.values()):
                    raise ValueError('Expected hour and bot')
                if not re.fullmatch('[0-9a-f]{32}', query['bot'][0]):
                    raise ValueError('Invalid bot ID')
                record = league.replay(int(query['hour'][0]), query['bot'][0])
                return (S.OK, record, MIME) if record else (S.NOT_FOUND, {'error': 'Replay expired or not found'}, MIME)
        elif method == 'POST' and not url.query:
            if content_type.split(';')[0].strip().lower() != 'application/json':
                return S.UNSUPPORTED_MEDIA_TYPE, {'error': 'Use application/json'}, MIME
            payload = json.loads(body)
            if not isinstance(payload, dict):
                raise ValueError('Expected JSON object')
            if url.path == '/api/league/bots':
                if set(payload) == {'name', 'source'}:
                    if not isinstance(payload['source'], str):
                        raise ValueError('Source must be text')
                    return S.CREATED, league.deploy(payload['name'], DEFAULT_CONFIG, payload['source']), MIME
                if set(payload) != {'name', 'config'}:
                    raise ValueError('Expected name and config')
                return S.CREATED, league.deploy(payload['name'], payload['config']), MIME
            if url.path == '/api/league/bots/active':
                if set(payload) != {'id', 'token', 'active'}:
                    raise ValueError('Expected id, token and active')
                league.set_active(payload['id'], payload['token'], payload['active'])
                return S.OK, {'ok': True}, MIME
        else:
            return S.METHOD_NOT_ALLOWED, {'error': 'Unsupported method'}, MIME
        return S.NOT_FOUND, {'error': 'Not found'}, MIME
    except PermissionError as exc:
        return S.FORBIDDEN, {'error': str(exc)}, MIME
    except (ValueError, UnicodeError) as exc:
        return S.BAD_REQUEST, {'error': str(exc)}, MIME
    except (sqlite3.Error, StorageUnavailable):
        return S.SERVICE_UNAVAILABLE, {'error': 'League storage temporarily unavailable'}, MIME
