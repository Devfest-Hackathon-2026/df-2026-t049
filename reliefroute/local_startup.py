"""Local CLI storage setup only; never invoked by the production WSGI adapter."""
import os
from pathlib import Path

from .league import League


def configure_local_league(database=None):
    """Reuse the existing SQLite schema without creating Bots or settling rounds."""
    path = Path(database or os.environ.get('RELIEFROUTE_LEAGUE_DB')
                or 'outputs/local-league.sqlite3').expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    League(path)
    # A local preview must never select the production GCS backend.
    if os.environ.pop('RELIEFROUTE_LEAGUE_BUCKET', None):
        print('Local mode: ignoring RELIEFROUTE_LEAGUE_BUCKET; using SQLite.', flush=True)
    os.environ['RELIEFROUTE_LEAGUE_DB'] = str(path)
    return path
