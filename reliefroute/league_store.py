"""Cloud Storage compare-and-swap snapshots for the small pilot league.

Only the remote generation is authoritative. Temporary SQLite files are never
reused across requests. Conflicting writers recompute against the winner.
"""
import os
import gzip
import shutil
import tempfile
from pathlib import Path

from .league import League


class Conflict(Exception):
    pass


class StorageUnavailable(RuntimeError):
    pass


def compress_snapshot(source, target):
    with open(source, 'rb') as incoming, gzip.GzipFile(filename=str(target),mode='wb',mtime=0) as outgoing:
        shutil.copyfileobj(incoming,outgoing)


def decompress_snapshot(source, target, limit=128 * 1024 * 1024):
    """Accept original raw SQLite and compressed snapshots; bound expansion."""
    with open(source,'rb') as probe:
        compressed = probe.read(2) == b'\x1f\x8b'
    opener = gzip.open if compressed else open
    size=0
    with opener(source,'rb') as incoming, open(target,'wb') as outgoing:
        while True:
            chunk=incoming.read(1024*1024)
            if not chunk:
                break
            size+=len(chunk)
            if size>limit:
                raise StorageUnavailable('League snapshot exceeds pilot capacity')
            outgoing.write(chunk)


class GCSBackend:
    def __init__(self, bucket, object_name='league/state.sqlite3'):
        from google.cloud import storage
        self.bucket = storage.Client().bucket(bucket)
        self.object_name = object_name

    def load(self, path):
        from google.api_core.exceptions import NotFound, PreconditionFailed
        blob = self.bucket.get_blob(self.object_name, timeout=20)
        if blob is None:
            return 0
        try:
            packed = Path(str(path)+'.download')
            blob.download_to_filename(str(packed), if_generation_match=int(blob.generation), timeout=20)
            decompress_snapshot(packed,path)
        except (NotFound, PreconditionFailed) as exc:
            raise Conflict() from exc
        return int(blob.generation)

    def save(self, path, generation):
        from google.api_core.exceptions import PreconditionFailed
        blob = self.bucket.blob(self.object_name)
        try:
            packed=Path(str(path)+'.gz')
            compress_snapshot(path,packed)
            blob.upload_from_filename(str(packed), content_type='application/octet-stream',
                                      if_generation_match=generation, timeout=40)
        except PreconditionFailed as exc:
            raise Conflict() from exc


class SnapshotLeague:
    def __init__(self, backend):
        self.backend = backend

    def _call(self, method, *args):
        write = method in ('deploy', 'set_active', 'run_hour')
        for _ in range(5):
            with tempfile.TemporaryDirectory(prefix='reliefroute-') as directory:
                path = Path(directory) / 'state.sqlite3'
                try:
                    generation = self.backend.load(path)
                    result = getattr(League(path), method)(*args)
                    if write and not (method == 'run_hour' and result is False):
                        self.backend.save(path, generation)
                    return result
                except Conflict:
                    continue
                except (ValueError, PermissionError):
                    raise
                except Exception as exc:
                    raise StorageUnavailable('League storage temporarily unavailable') from exc
        raise StorageUnavailable('League is busy; retry shortly')

    def deploy(self, name, config, source=None):
        return self._call('deploy', name, config, source)

    def set_active(self, bot_id, token, active):
        return self._call('set_active', bot_id, token, active)

    def run_hour(self, hour=None):
        return self._call('run_hour', hour)

    def current(self):
        return self._call('current')

    def leaderboard(self):
        return self._call('leaderboard')

    def replay(self, hour, bot_id):
        return self._call('replay', hour, bot_id)


def configured_league():
    bucket = os.environ.get('RELIEFROUTE_LEAGUE_BUCKET')
    if bucket:
        try:
            return SnapshotLeague(GCSBackend(bucket))
        except Exception as exc:
            raise StorageUnavailable('Unable to connect to league storage') from exc
    path = os.environ.get('RELIEFROUTE_LEAGUE_DB')
    return League(path) if path else None
