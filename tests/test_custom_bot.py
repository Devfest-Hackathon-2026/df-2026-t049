import itertools
import json
import unittest

from reliefroute.bots import CONFIG_OPTIONS, DEFAULT_CONFIG, configured_bot, validate_config
from reliefroute.engine import Engine
from reliefroute.scenario import event_scenario, fixed_scenario
from reliefroute.scoring import score_record
from reliefroute.server import compare_matches, run_match
from reliefroute.wsgi import application


class CustomBotTests(unittest.TestCase):
    def test_all_configs_reproducible_legal_and_conserve_supply(self):
        for values in itertools.product(*CONFIG_OPTIONS.values()):
            config = dict(zip(CONFIG_OPTIONS, values))
            for seed in (11, 22, 33):
                with self.subTest(config=config, seed=seed):
                    records = [Engine(event_scenario(seed)).run(configured_bot(config)) for _ in range(3)]
                    self.assertEqual(records[0], records[1])
                    self.assertEqual(records[1], records[2])
                    record = records[0]
                    self.assertEqual(score_record(json.loads(json.dumps(record))), record['score'])
                    for row in record['log']:
                        self.assertTrue(all(action['accepted'] for action in row['actions']))
                        state = row['state']
                        delivered = sum(b['received'] for s in state['shelters'] for b in s['batches'])
                        self.assertEqual(state['depot']['stock'] + sum(v['cargo'] for v in state['vehicles']) + delivered, 70)
                        self.assertNotIn('event_plan', row['observation']['observation'])

    def test_each_parameter_changes_decisions(self):
        request = Engine(event_scenario(11)).observe()
        urgent = configured_bot(DEFAULT_CONFIG)(request)
        near = configured_bot({**DEFAULT_CONFIG, 'priority_rule': 'nearest'})(request)
        self.assertNotEqual(urgent, near)
        half = configured_bot({**DEFAULT_CONFIG, 'load_rule': 'half'})(request)
        self.assertTrue(all(a['quantity'] == 5 for a in half['actions']))
        self.assertNotEqual(half, urgent)
        request['observation']['depot']['stock'] = 3
        self.assertTrue(configured_bot(DEFAULT_CONFIG)(request)['actions'])
        self.assertEqual(configured_bot({**DEFAULT_CONFIG, 'dispatch_rule': 'full_load'})(request)['actions'], [])

    def test_fair_priority_accounts_for_incoming_cargo(self):
        request = Engine(fixed_scenario()).observe()
        policy = configured_bot({**DEFAULT_CONFIG, 'priority_rule': 'fair'})
        self.assertEqual([a['target_shelter_id'] for a in policy(request)['actions']], ['S1', 'S2', 'S3'])
        first = request['observation']['vehicles'][0]
        first.update(status='delivering', leg='delivering', target='S1', cargo=10)
        self.assertEqual(policy(request)['actions'][0]['target_shelter_id'], 'S2')

    def test_config_is_strict_and_copied(self):
        for config in (None, [], {}, {**DEFAULT_CONFIG, 'code': 'anything'},
                       {**DEFAULT_CONFIG, 'load_rule': 5}, {**DEFAULT_CONFIG, 'priority_rule': 'unknown'}):
            with self.assertRaises(ValueError):
                validate_config(config)
        config = dict(DEFAULT_CONFIG)
        bot = configured_bot(config)
        config['priority_rule'] = 'nearest'
        self.assertEqual(bot(Engine(event_scenario(11)).observe()), configured_bot(DEFAULT_CONFIG)(Engine(event_scenario(11)).observe()))

    def test_match_and_comparison_keep_config_and_baselines(self):
        params = {'bot': ['custom'], **{key: [value] for key, value in DEFAULT_CONFIG.items()}}
        record = run_match(params)
        self.assertEqual(record['bot_config'], DEFAULT_CONFIG)
        self.assertEqual(record['bot_version'], '1.0')
        self.assertEqual(record['score']['total'], 78.009259)
        comparison = compare_matches(DEFAULT_CONFIG)
        self.assertEqual(len(comparison['matches']), 9)
        baseline = compare_matches()
        self.assertEqual([r for r in comparison['matches'] if r['bot'] != 'custom'], baseline['matches'])
        for row in comparison['matches']:
            if row['bot'] == 'custom':
                self.assertEqual(row['bot_config'], DEFAULT_CONFIG)
        for bad in ({'bot': ['custom']}, {'bot': ['nearest'], 'load_rule': ['half']}):
            with self.assertRaises(ValueError):
                run_match(bad)


class WSGITests(unittest.TestCase):
    def request(self, path, query='', method='GET'):
        response = []
        body = b''.join(application({'PATH_INFO': path, 'QUERY_STRING': query, 'REQUEST_METHOD': method},
                                   lambda status, headers: response.extend([status, dict(headers)])))
        return response[0], response[1], body

    def test_routes_and_http_contract(self):
        for path in ('/', '/app.js', '/i18n.js', '/style.css', '/health'):
            status, headers, body = self.request(path)
            self.assertTrue(status.startswith('200'))
            self.assertEqual(int(headers['Content-Length']), len(body))
            self.assertTrue(body)
            self.assertEqual(self.request(path, method='HEAD')[2], b'')
        self.assertTrue(self.request('/.git/config')[0].startswith('404'))
        self.assertTrue(self.request('/api/match', method='POST')[0].startswith('405'))
        self.assertTrue(self.request('/api/match', 'seed=' + '1' * 2100)[0].startswith('414'))
        self.assertTrue(self.request('/api/compare', 'anything=1')[0].startswith('400'))
        self.assertTrue(self.request('/api/compare', 'load_rule=full&load_rule=half')[0].startswith('400'))

    def test_custom_api_end_to_end(self):
        query = 'priority_rule=fair&load_rule=full&dispatch_rule=any'
        status, _, body = self.request('/api/match', 'bot=custom&seed=22&' + query)
        self.assertTrue(status.startswith('200'))
        record = json.loads(body)
        self.assertEqual(len(record['log']), 24)
        self.assertEqual(record['score'], score_record(record))
        status, _, body = self.request('/api/compare', query)
        self.assertTrue(status.startswith('200'))
        self.assertEqual(len(json.loads(body)['matches']), 9)
