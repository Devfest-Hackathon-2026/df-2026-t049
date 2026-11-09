"""One-shot hourly settlement for a private Cloud Run Job.

Cloud Scheduler should invoke the Job API with its service identity, rather
than exposing a public HTTP endpoint that can settle arbitrary hours.
"""
from .league_store import configured_league


def main():
    league = configured_league()
    if league is None:
        raise RuntimeError('Configure durable league storage before starting the job')
    changed = league.run_hour()
    print('Hourly round settled' if changed else 'Hourly round already settled', flush=True)


if __name__ == '__main__':
    main()
