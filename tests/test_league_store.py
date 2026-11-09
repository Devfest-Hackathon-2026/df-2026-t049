import tempfile
import unittest
from pathlib import Path

from reliefroute.bots import DEFAULT_CONFIG
from reliefroute.league import League, hour_id
from reliefroute.league_store import Conflict, SnapshotLeague, StorageUnavailable, compress_snapshot, decompress_snapshot


class MemoryBackend:
    """Implements remote generation semantics, without Google credentials."""
    def __init__(self):
        self.generation = 0
        self.data = None
        self.on_save = None

    def load(self, path):
        if self.data is not None:
            Path(path).write_bytes(self.data)
        return self.generation

    def save(self, path, generation):
        if self.on_save:
            callback, self.on_save = self.on_save, None
            callback()
        if generation != self.generation:
            raise Conflict()
        self.data = Path(path).read_bytes()
        self.generation += 1


class SnapshotTests(unittest.TestCase):
    def test_compression_and_legacy_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            raw, packed, restored = [Path(directory)/name for name in ('raw','packed','restored')]
            league=League(raw)
            league.deploy('persistent',DEFAULT_CONFIG)
            compress_snapshot(raw,packed)
            self.assertLess(packed.stat().st_size,raw.stat().st_size)
            decompress_snapshot(packed,restored)
            self.assertEqual(League(restored).leaderboard(),league.leaderboard())
            decompress_snapshot(raw,restored)
            self.assertEqual(League(restored).leaderboard(),league.leaderboard())
            with self.assertRaises(StorageUnavailable):
                decompress_snapshot(packed,restored,limit=100)

    def test_concurrent_registration_preserves_winner(self):
        backend = MemoryBackend()
        first, other = SnapshotLeague(backend), SnapshotLeague(backend)
        backend.on_save = lambda: other.deploy('winner', DEFAULT_CONFIG)
        deployed = first.deploy('retried', DEFAULT_CONFIG)
        rows = first.leaderboard()
        self.assertEqual({r['name'] for r in rows}, {'winner','retried'})
        self.assertEqual(len(rows), 2)
        first.set_active(deployed['id'], deployed['token'], False)
        self.assertEqual(next(r['active'] for r in first.leaderboard() if r['id']==deployed['id']), 0)

    def test_concurrent_settlement_changes_ranking_once(self):
        backend = MemoryBackend()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'seed.sqlite3'
            local = League(path)
            local.register('one', DEFAULT_CONFIG, (hour_id()-1)*3600)
            local.register('two', dict(DEFAULT_CONFIG, priority_rule='fair'), (hour_id()-1)*3600)
            backend.save(path, 0)
        one, two = SnapshotLeague(backend), SnapshotLeague(backend)
        backend.on_save = lambda: two.run_hour()
        self.assertFalse(one.run_hour())
        self.assertTrue(all(row['played']==1 for row in one.leaderboard()))
        self.assertEqual(sum(row['rating'] for row in one.leaderboard()), 2000000)
        self.assertEqual(len(one.current()['results']), 2)

    def test_failed_write_does_not_claim_success(self):
        backend = MemoryBackend()
        def fail(path,generation):
            raise OSError('unavailable')
        backend.save = fail
        with self.assertRaises(StorageUnavailable):
            SnapshotLeague(backend).deploy('not saved', DEFAULT_CONFIG)
        self.assertEqual(SnapshotLeague(backend).leaderboard(), [])


if __name__ == '__main__':
    unittest.main()
