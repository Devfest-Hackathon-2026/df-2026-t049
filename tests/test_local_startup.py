import io
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from reliefroute.bots import DEFAULT_CONFIG
from reliefroute.local_startup import configure_local_league
from reliefroute.wsgi import application

ROOT = Path(__file__).resolve().parents[1]


class LocalStartupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / 'nested' / 'league.sqlite3'
        self.env = dict(os.environ, RELIEFROUTE_LEAGUE_DB=str(self.db))
        self.env.pop('RELIEFROUTE_LEAGUE_BUCKET', None)

    def start(self, *command):
        process = subprocess.Popen([sys.executable, *command], cwd=ROOT, env=self.env,
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        def stop():
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=10)
            process.stdout.close()
        self.addCleanup(stop)
        lines = queue.Queue()
        def read():
            for line in process.stdout:
                lines.put(line.strip())
        threading.Thread(target=read, daemon=True).start()
        while True:
            line = lines.get(timeout=15)
            if line.startswith('ReliefRoute Arena: '):
                return process, line.split(': ', 1)[1]

    def request(self, base, path, data=None):
        req = Request(base + path, data=json.dumps(data).encode() if data is not None else None,
                      headers={'Content-Type': 'application/json'})
        with urlopen(req, timeout=10) as response:
            return json.load(response)

    def test_default_path_and_local_cloud_isolation(self):
        previous = Path.cwd()
        try:
            os.chdir(self.tmp.name)
            with patch.dict(os.environ, {'RELIEFROUTE_LEAGUE_BUCKET': 'must-not-contact'}, clear=True):
                path = configure_local_league()
                # Windows runners may expose the same directory through an 8.3 alias.
                self.assertTrue(path.samefile(Path.cwd() / 'outputs/local-league.sqlite3'))
                self.assertTrue(path.exists())
                self.assertNotIn('RELIEFROUTE_LEAGUE_BUCKET', os.environ)
                explicit = configure_local_league(self.db)
                self.assertTrue(explicit.samefile(self.db))
        finally:
            os.chdir(previous)

    def test_real_cli_empty_register_manage_restart(self):
        process, base = self.start('-m', 'reliefroute.server', '--port', '0')
        for path in ['/', '/league', '/health', '/app.js', '/league.js', '/map-geometry.js',
                     '/map-renderer.js', '/replay-controller.js', '/i18n.js', '/style.css']:
            with urlopen(base + path, timeout=10) as response:
                self.assertEqual(response.status, 200)
        empty = self.request(base, '/api/league')
        self.assertEqual(empty['ranking'], [])
        self.assertIsNone(empty['current']['hour'])
        bot = self.request(base, '/api/league/bots', {'name': 'Local parameter', 'config': DEFAULT_CONFIG})
        source = (ROOT / 'examples/decision_bot.py').read_text(encoding='utf-8')
        self.request(base, '/api/league/bots', {'name': 'Local program', 'source': source})
        with self.assertRaises(HTTPError) as caught:
            self.request(base, '/api/league/bots', {'name': 'Invalid', 'source': 'import os'})
        self.assertEqual(caught.exception.code, 400)
        for active in [False, True]:
            self.request(base, '/api/league/bots/active', {'id': bot['id'], 'token': bot['token'], 'active': active})
        before = self.request(base, '/api/league')
        self.assertNotIn(bot['token'], json.dumps(before))
        self.assertIsNone(before['current']['hour'])
        process.terminate(); process.wait(timeout=10)
        _, base = self.start('-m', 'reliefroute.server', '--port', '0')
        after = self.request(base, '/api/league')
        self.assertEqual(after['ranking'], before['ranking'])
        self.assertEqual(after['current'], before['current'])

    def test_demo_once_and_replay_persist_without_duplicate_settlement(self):
        command = [sys.executable, 'scripts/local_league.py', '--demo', '--once']
        subprocess.run(command, cwd=ROOT, env=self.env, check=True, capture_output=True)
        process, base = self.start('-m', 'reliefroute.server', '--port', '0')
        before = self.request(base, '/api/league')
        self.assertEqual(len(before['ranking']), 2)
        self.assertEqual(len(before['current']['results']), 2)
        hour = before['current']['hour']; bot = before['current']['results'][0]['bot_id']
        replay = self.request(base, f'/api/league/replay?hour={hour}&bot={bot}')
        self.assertEqual(len(replay['log']), 48)
        subprocess.run(command, cwd=ROOT, env=self.env, check=True, capture_output=True)
        subprocess.run([sys.executable, 'scripts/local_league.py', '--once'], cwd=ROOT,
                       env=self.env, check=True, capture_output=True)
        self.assertEqual(self.request(base, '/api/league')['ranking'], before['ranking'])
        process.terminate(); process.wait(timeout=10)
        _, base = self.start('-m', 'reliefroute.server', '--port', '0')
        self.assertEqual(self.request(base, f'/api/league/replay?hour={hour}&bot={bot}'), replay)

    def test_wsgi_still_requires_explicit_configuration(self):
        with patch.dict(os.environ, {}, clear=True):
            statuses = []
            application({'PATH_INFO': '/api/league', 'REQUEST_METHOD': 'GET',
                         'wsgi.input': io.BytesIO()}, lambda status, headers: statuses.append(status))
            self.assertTrue(statuses[0].startswith('503'))
            self.assertNotIn('RELIEFROUTE_LEAGUE_DB', os.environ)
