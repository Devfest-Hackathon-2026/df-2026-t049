import concurrent.futures
import tempfile
import unittest
from pathlib import Path

from reliefroute.bots import DEFAULT_CONFIG, configured_bot
from reliefroute.engine import Engine, canonical, shortest_path
from reliefroute.league import League, rating_deltas
from reliefroute.scenario import hourly_scenario
from reliefroute.scoring import score_record


class HourlyScenarioTests(unittest.TestCase):
    def test_generation_and_simulation(self):
        for hour in (0, 100, 498360):
            scenario = hourly_scenario(hour)
            self.assertEqual(scenario, hourly_scenario(hour))
            self.assertNotEqual(scenario['seed'], hourly_scenario(hour + 1)['seed'])
            for removed in scenario['roads']:
                roads = [r for r in scenario['roads'] if r != removed]
                for shelter in scenario['shelters']:
                    self.assertIsNotNone(shortest_path(roads, 'N0', shelter['node_id']))
            record = Engine(scenario).run(configured_bot(DEFAULT_CONFIG))
            self.assertEqual(len(record['log']), 48)
            self.assertEqual(record['score'], score_record(record))
            self.assertEqual(canonical(record), canonical(Engine(scenario).run(configured_bot(DEFAULT_CONFIG))))
            for row in record['log']:
                state = row['state']
                delivered = sum(b['received'] for s in state['shelters'] for b in s['batches'])
                self.assertEqual(state['depot']['stock'] + sum(v['cargo'] for v in state['vehicles']) + delivered, 160)
                self.assertNotIn('event_plan', row['observation'])
                self.assertTrue(all(e['turn'] <= row['turn'] for e in row['observation']['observation']['events']))


class LeagueTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'league.sqlite3'
        self.league = League(self.path)

    def test_boundary_persistence_idempotency_and_retention(self):
        first = self.league.register('first', DEFAULT_CONFIG, timestamp=99 * 3600)
        second = self.league.register('next hour', DEFAULT_CONFIG, timestamp=100 * 3600)
        self.assertTrue(self.league.run_hour(100))
        self.assertEqual([r['bot_id'] for r in self.league.current()['results']], [first])
        self.assertIsNotNone(self.league.replay(100, first))
        self.assertFalse(League(self.path).run_hour(100))
        self.assertEqual(self.league.leaderboard()[0]['played'] + self.league.leaderboard()[1]['played'], 1)
        self.assertTrue(self.league.run_hour(101))
        self.assertIsNone(self.league.replay(100, first))
        self.assertIsNotNone(self.league.replay(101, second))
        self.assertEqual(len(self.league.current()['results']), 2)
        with self.assertRaises(ValueError):
            self.league.run_hour(98)

    def test_competing_workers_settle_once(self):
        self.league.register('bot', DEFAULT_CONFIG, timestamp=0)
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda _: League(self.path).run_hour(2), range(2)))
        self.assertEqual(sorted(results), [False, True])
        self.assertEqual(self.league.leaderboard()[0]['played'], 1)

    def test_transaction_rolls_back_on_engine_failure(self):
        from unittest.mock import patch
        self.league.register('bot', DEFAULT_CONFIG, timestamp=0)
        with patch('reliefroute.league.Engine.run', side_effect=RuntimeError('crash')):
            with self.assertRaises(RuntimeError):
                self.league.run_hour(1)
        self.assertIsNone(self.league.current()['hour'])
        self.assertEqual(self.league.leaderboard()[0]['played'], 0)
        self.assertTrue(self.league.run_hour(1))

    def test_rank_points(self):
        self.assertEqual(rating_deltas({'a': 5}), {'a': 0})
        self.assertEqual(rating_deltas({'a': 5, 'b': 5}), {'a': 0, 'b': 0})
        deltas = rating_deltas({'a': 90, 'b': 50, 'c': 20})
        self.assertEqual(deltas, {'a': 16000, 'b': 0, 'c': -16000})
        self.assertEqual(sum(rating_deltas(dict(enumerate(range(8)))).values()), 0)


if __name__ == '__main__':
    unittest.main()
