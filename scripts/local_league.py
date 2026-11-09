"""Local-only persistent league preview. Never contacts cloud services."""
import argparse, sys, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from reliefroute.league import League
from reliefroute.local_startup import configure_local_league
p=argparse.ArgumentParser()
p.add_argument('--db',help='Local SQLite path; defaults to RELIEFROUTE_LEAGUE_DB or outputs/local-league.sqlite3')
p.add_argument('--port',type=int,default=8016)
p.add_argument('--demo',action='store_true',help='Seed two local reference Bots if empty and settle the current hour')
p.add_argument('--once',action='store_true',help='Settle current hour and exit')
a=p.parse_args();path=configure_local_league(a.db)
l=League(path)
if a.demo and not l.leaderboard():
 for rule in ['nearest','urgency']:
  l.register('Local demo '+rule,{'priority_rule':rule,'load_rule':'full','dispatch_rule':'any'},timestamp=time.time()-3600)
if a.demo or a.once:l.run_hour()
print('Local database:',path,flush=True)
if not a.once:
 from reliefroute.server import main
 sys.argv=[sys.argv[0],'--port',str(a.port)];main()
