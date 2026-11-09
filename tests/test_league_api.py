import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from reliefroute.bots import DEFAULT_CONFIG
from reliefroute.league import League, hour_id
from reliefroute.league_api import handle
from reliefroute.wsgi import application


class LeagueAPITests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = str(Path(self.directory.name) / 'league.sqlite3')
        self.environment = patch.dict(os.environ, {'RELIEFROUTE_LEAGUE_DB': self.path})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def post(self, path, value):
        return handle(path, 'POST', json.dumps(value).encode(), 'application/json')

    def test_deploy_manage_settle_watch(self):
        status, deployed, _ = self.post('/api/league/bots', {'name':'User <Bot>', 'config':DEFAULT_CONFIG})
        self.assertEqual(status, 201)
        status, public, _ = handle('/api/league')
        self.assertEqual(status, 200)
        self.assertNotIn(deployed['token'], json.dumps(public))
        self.assertEqual(public['ranking'][0]['name'], 'User <Bot>')
        credentials = {'id': deployed['id'], 'token': deployed['token'], 'active': False}
        self.assertEqual(self.post('/api/league/bots/active', dict(credentials, token='bad'))[0], 403)
        self.assertEqual(self.post('/api/league/bots/active', credentials)[0], 200)
        league = League(self.path)
        league.run_hour(hour_id() + 1)
        self.assertEqual(league.current()['results'], [])
        self.assertEqual(self.post('/api/league/bots/active', dict(credentials, active=True))[0], 200)
        league.run_hour(hour_id() + 2)
        status, record, _ = handle(f"/api/league/replay?hour={hour_id()+2}&bot={deployed['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(len(record['log']), 48)
        self.assertEqual(record['bot_name'], 'User <Bot>')
        self.assertNotIn(deployed['token'], json.dumps(record))

    def test_wsgi_post_and_validation(self):
        body=json.dumps({'name':'WSGI', 'config':DEFAULT_CONFIG}).encode()
        response=[]
        chunks=application({'PATH_INFO':'/api/league/bots','REQUEST_METHOD':'POST',
                            'CONTENT_TYPE':'application/json','CONTENT_LENGTH':str(len(body)),
                            'wsgi.input':io.BytesIO(body)}, lambda status,headers:response.append(status))
        self.assertTrue(response[0].startswith('201'))
        self.assertIn('token', json.loads(b''.join(chunks)))
        self.assertEqual(handle('/api/league/bots','POST',b'{}','text/plain')[0],415)
        self.assertEqual(handle('/api/league/bots','POST',b'[]','application/json')[0],400)
        self.assertEqual(handle('/api/league/bots','POST',b'X'*8193,'application/json')[0],413)
        self.assertEqual(handle('/api/league/replay?hour=1&hour=2&bot=x')[0],400)

    def test_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(handle('/api/league')[0],503)

    def test_code_registration_and_rejection(self):
        source = (Path(__file__).resolve().parents[1]/'examples/decision_bot.py').read_text(encoding='utf-8')
        status, data, _ = self.post('/api/league/bots', {'name':'code via API','source':source})
        self.assertEqual(status,201)
        league=League(self.path)
        league.run_hour(hour_id()+1)
        self.assertEqual(league.replay(hour_id()+1,data['id'])['bot'],'program')
        self.assertEqual(self.post('/api/league/bots', {'name':'bad','source':'import os'})[0],400)
        self.assertEqual(len(league.leaderboard()),1)


if __name__ == '__main__':
    unittest.main()
