"""Deploy the pilot league from an authenticated Google Cloud Shell.

Run from the repository root: python3 scripts/deploy_league.py PROJECT_ID
Creates a private bucket, scoped service identities, a public Cloud Run service,
a private hourly job, and one Scheduler trigger. Does not print credentials.
"""
import argparse
import json
import subprocess
import sys
import re
from pathlib import Path


def gcloud(*args, capture=False):
    command = ['gcloud', *args, '--quiet']
    result = subprocess.run(command, check=True, text=True,
                            stdout=subprocess.PIPE if capture else None)
    return result.stdout.strip() if capture else None


def deploy(project, region):
    if not re.fullmatch(r'[a-z][a-z0-9-]{4,28}[a-z0-9]', project):
        raise ValueError('Invalid project ID')
    if not re.fullmatch(r'[a-z]+-[a-z]+[0-9]', region):
        raise ValueError('Invalid region')
    if not Path('reliefroute/league_job.py').is_file() or not Path('Dockerfile').is_file():
        raise ValueError('Run from the updated repository root')
    # Explicit project flags on every operation; do not change user's global config.
    def run(*args, capture=False):
        return gcloud(*args, '--project', project, capture=capture)
    number = run('projects', 'describe', project, '--format=value(projectNumber)', capture=True)
    bucket = f'{project}-{number}-league'
    runtime = f'reliefroute-league@{project}.iam.gserviceaccount.com'
    scheduler = f'reliefroute-clock@{project}.iam.gserviceaccount.com'
    service, job, clock = 'reliefroute-arena', 'reliefroute-hourly', 'reliefroute-hourly'
    run('services', 'enable', 'run.googleapis.com', 'cloudbuild.googleapis.com',
        'artifactregistry.googleapis.com', 'storage.googleapis.com',
        'cloudscheduler.googleapis.com', 'iam.googleapis.com')
    accounts = set(run('iam', 'service-accounts', 'list', '--format=value(email)', capture=True).splitlines())
    for name, email in [('reliefroute-league',runtime),('reliefroute-clock',scheduler)]:
        if email not in accounts:
            run('iam','service-accounts','create',name,'--display-name',name)
    buckets = json.loads(run('storage','buckets','list','--format=json(name)',capture=True))
    if bucket not in {item['name'] for item in buckets}:
        run('storage','buckets','create',f'gs://{bucket}','--location',region,
            '--uniform-bucket-level-access','--public-access-prevention')
    # Runtime gets object access only to this private bucket, not project-wide storage.
    run('storage','buckets','add-iam-policy-binding',f'gs://{bucket}',
        '--member',f'serviceAccount:{runtime}','--role','roles/storage.objectAdmin')
    run('run','deploy',service,'--source','.','--region',region,'--allow-unauthenticated',
        '--service-account',runtime,'--port','8080','--cpu','1','--memory','1Gi',
        '--min-instances','0','--max-instances','2','--concurrency','2','--timeout','120',
        '--update-env-vars',f'RELIEFROUTE_LEAGUE_BUCKET={bucket}')
    revision = run('run','services','describe',service,'--region',region,
                   '--format=value(status.latestReadyRevisionName)',capture=True)
    image = run('run','revisions','describe',revision,'--region',region,
                '--format=value(status.imageDigest)',capture=True)
    if not image or '@sha256:' not in image:
        raise RuntimeError('Cannot resolve immutable image digest for the hourly job')
    run('run','jobs','deploy',job,'--image',image,'--region',region,
        '--service-account',runtime,'--command','python','--args=-m,reliefroute.league_job',
        '--tasks','1','--parallelism','1','--max-retries','1','--task-timeout','600s',
        '--cpu','1','--memory','1Gi','--set-env-vars',f'RELIEFROUTE_LEAGUE_BUCKET={bucket}')
    run('run','jobs','add-iam-policy-binding',job,'--region',region,
        '--member',f'serviceAccount:{scheduler}','--role','roles/run.invoker')
    clocks = json.loads(run('scheduler','jobs','list','--location',region,'--format=json(name)',capture=True))
    exists = any(item['name'].split('/')[-1]==clock for item in clocks)
    run('scheduler','jobs','update' if exists else 'create','http',clock,'--location',region,
        '--schedule','0 * * * *','--time-zone','Etc/UTC','--http-method','POST',
        '--uri',f'https://run.googleapis.com/v2/projects/{project}/locations/{region}/jobs/{job}:run',
        '--oauth-service-account-email',scheduler,'--message-body={}',
        '--update-headers=Content-Type=application/json' if exists else '--headers=Content-Type=application/json',
        '--attempt-deadline','180s')
    run('run','jobs','execute',job,'--region',region,'--wait')
    url = run('run','services','describe',service,'--region',region,'--format=value(status.url)',capture=True)
    print(f'League URL: {url}/league')
    print('Initial job completed. New Bots join at the next UTC hour; verify that scheduled round separately.')
    return url


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project')
    parser.add_argument('--region',default='asia-northeast1')
    options=parser.parse_args()
    try:
        deploy(options.project,options.region)
    except (subprocess.CalledProcessError,ValueError,RuntimeError) as error:
        print(f'Deployment stopped: {error}',file=sys.stderr)
        sys.exit(1)
