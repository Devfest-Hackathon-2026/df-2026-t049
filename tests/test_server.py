import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import urlopen

from reliefroute.server import Handler


class QuietHandler(Handler):
    def log_message(self, *args):
        pass


class WebIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def get(self, path):
        return urlopen(self.base + path, timeout=5)

    def test_static_assets_and_no_arbitrary_files(self):
        for path, content_type in [('/', 'text/html'), ('/app.js', 'text/javascript'), ('/i18n.js', 'text/javascript'), ('/style.css', 'text/css')]:
            with self.get(path) as response:
                self.assertEqual(response.status, 200)
                self.assertIn(content_type, response.headers['Content-Type'])
                self.assertGreater(len(response.read()), 100)
        for path in ['/AGENTS.md', '/.git/config', '/../README.md', '/%2e%2e/README.md', '/missing']:
            with self.assertRaises(HTTPError) as caught:
                self.get(path)
            self.assertEqual(caught.exception.code, 404)

    def test_match_runs_real_engine_and_returns_replay(self):
        with self.get('/api/match?scenario=events&seed=11&bot=urgency') as response:
            record = json.load(response)
        self.assertEqual(record['score']['total'], 78.009259)
        self.assertEqual(record['summary']['delivered'], 70)
        self.assertEqual(len(record['log']), 24)
        self.assertEqual(record['bot'], 'urgency')
        self.assertEqual(record['log'][3]['events'][0]['type'], 'road_closed')
        self.assertNotIn('event_plan', record['log'][0]['state'])
        with self.get('/api/match?scenario=fixture&seed=0&bot=nearest') as response:
            fixture = json.load(response)
        self.assertEqual(fixture['score']['total'], 95)
        self.assertEqual(fixture['summary']['delivered'], 60)

    def test_bad_parameters_are_client_errors(self):
        for query in ['seed=1.5', 'seed=', 'seed=2147483648', 'seed=11&seed=22',
                      'bot=uploaded', 'scenario=unknown', 'scenario=fixture&seed=11', 'score=100']:
            with self.subTest(query=query):
                with self.assertRaises(HTTPError) as caught:
                    self.get('/api/match?' + query)
                self.assertEqual(caught.exception.code, 400)
                self.assertIn('error', json.load(caught.exception))

    def test_comparison_exposes_all_six_matches_and_correct_ranking(self):
        with self.get('/api/compare') as response:
            comparison = json.load(response)
        self.assertEqual(len(comparison['matches']), 6)
        self.assertEqual(comparison['seeds'], [11, 22, 33])
        self.assertEqual(comparison['ranking'], [
            {'bot': 'urgency', 'mean_score': 78.350051},
            {'bot': 'nearest', 'mean_score': 73.506944}])


if __name__ == '__main__':
    unittest.main()
