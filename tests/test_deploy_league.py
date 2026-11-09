"""Check fresh/repeated provisioning plans without touching a cloud account."""
import unittest
from unittest.mock import patch
from scripts.deploy_league import deploy


class DeploymentPlanTests(unittest.TestCase):
    def test_new_and_existing_scheduler(self):
        for exists in (False, True):
            calls=[]
            def fake(*args, capture=False):
                calls.append(args)
                self.assertIn('--project', args)
                if not capture:
                    return None
                if args[:2]==('projects','describe'):
                    return '123456789'
                if args[:3]==('iam','service-accounts','list'):
                    return ''
                if args[:3]==('storage','buckets','list'):
                    return '[]'
                if args[:3]==('scheduler','jobs','list'):
                    return '[{"name":"projects/test-project/locations/asia-northeast1/jobs/reliefroute-hourly"}]' if exists else '[]'
                if args[:3]==('run','revisions','describe'):
                    return 'registry.example/image@sha256:abc'
                if '--format=value(status.latestReadyRevisionName)' in args:
                    return 'revision-1'
                return 'https://example.run.app'
            with patch('scripts.deploy_league.gcloud',side_effect=fake):
                self.assertEqual(deploy('test-project','asia-northeast1'),'https://example.run.app')
            scheduler=next(c for c in calls if c[:3]==('scheduler','jobs','update' if exists else 'create'))
            self.assertIn('--update-headers=Content-Type=application/json' if exists else '--headers=Content-Type=application/json',scheduler)
            self.assertIn('--oauth-service-account-email', scheduler)
            self.assertNotIn('--oidc-service-account-email', scheduler)
            self.assertEqual(scheduler[scheduler.index('--schedule')+1],'0 * * * *')
            job=next(c for c in calls if c[:3]==('run','jobs','deploy'))
            self.assertIn('registry.example/image@sha256:abc',job)


if __name__ == '__main__':
    unittest.main()
