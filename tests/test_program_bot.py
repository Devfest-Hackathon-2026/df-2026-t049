import json
import tempfile
import unittest
from pathlib import Path

from reliefroute.bots import DEFAULT_CONFIG
from reliefroute.engine import Engine, canonical
from reliefroute.league import League, hour_id
from reliefroute.program_bot import ProgramError, program_bot
from reliefroute.scenario import hourly_scenario

EXAMPLE = (Path(__file__).resolve().parents[1] / 'examples/decision_bot.py').read_text(encoding='utf-8')


class ProgramTests(unittest.TestCase):
    def test_real_decisions_reproducible_and_legal(self):
        scenario = hourly_scenario(498000)
        first = Engine(scenario).run(program_bot(EXAMPLE))
        self.assertEqual(canonical(first), canonical(Engine(scenario).run(program_bot(EXAMPLE))))
        self.assertGreater(first['summary']['delivered'], 0)
        self.assertTrue(all(action['accepted'] for row in first['log'] for action in row['actions']))

    def test_forbidden_host_capabilities(self):
        bodies = ["import os", "return request.__class__", "return open('secret')",
                  "return eval('1')", "return __import__('os')", "while True:\n        pass",
                  "return [0] * 1000000000", "return 2 ** 1000000000",
                  "request['turn'] = 0", "return (x for x in request)"]
        # Numeric-only multiplication rejects list allocation at runtime.
        for body in bodies:
            with self.subTest(body=body):
                with self.assertRaises((ValueError, TypeError)):
                    bot = program_bot('def decide(request):\n    '+body)
                    bot({'turn':0})

    def test_budget_and_oversized_numeric_operations(self):
        source = '''def decide(request):
    for a in request['items']:
        for b in request['items']:
            for c in request['items']:
                x = 1
    return None
'''
        with self.assertRaises(ProgramError):
            program_bot(source)({'items':list(range(100))})
        with self.assertRaises(ProgramError):
            program_bot('def decide(request):\n    return 1000000000000 * 1000000000000')({})
        nested = '''def decide(request):
    value = []
    for item in request['items']:
        value = [value, value]
    return value
'''
        with self.assertRaises(ProgramError):
            program_bot(nested)({'items':list(range(50))})

    def test_invalid_decisions_still_use_engine_judge(self):
        source = '''def decide(request):
    return {'protocol_version':'0.1', 'turn':request['turn'], 'actions':[
        {'vehicle_id':'V1','type':'dispatch','target_shelter_id':'S1','quantity':999999}]}
'''
        result = Engine(hourly_scenario(10)).run(program_bot(source))
        self.assertEqual(result['summary']['delivered'],0)
        self.assertTrue(all(r['actions'][0]['reason']=='over_capacity' for r in result['log']))
        failing = Engine(hourly_scenario(10)).run(program_bot('def decide(request):\n    return 1 / 0'))
        self.assertEqual(len(failing['log']),48)
        self.assertTrue(all(r['actions'][0]['reason']=='bot_error' for r in failing['log']))
        self.assertEqual(failing['log'][0]['actions'][0]['detail'], 'Line 2: Division by zero')
        missing = Engine(hourly_scenario(10)).run(program_bot("def decide(request):\n    return request['absent']"))
        self.assertEqual(missing['log'][0]['actions'][0]['detail'], 'Line 2: Unknown variable or dictionary key')

    def test_deployed_code_runs_without_browser(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'league.sqlite3'
            league = League(path)
            deployed = league.deploy('Code pilot',DEFAULT_CONFIG,EXAMPLE)
            League(path).run_hour(hour_id()+1)
            record = league.replay(hour_id()+1,deployed['id'])
            self.assertEqual(record['bot'],'program')
            self.assertEqual(len(record['source_hash']),64)
            self.assertGreater(record['summary']['delivered'],0)
            self.assertNotIn(EXAMPLE, json.dumps(record))


if __name__ == '__main__':
    unittest.main()
