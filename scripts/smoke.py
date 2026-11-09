"""Verify a running local container or deployed Cloud Run URL without credentials."""
import json
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

base = sys.argv[1].rstrip('/')
if not base.startswith(('http://', 'https://')):
    raise SystemExit('Provide an http(s) base URL')
for attempt in range(20):
    try:
        with urlopen(base + '/health', timeout=10) as response:
            assert json.load(response)['status'] == 'ok'
        break
    except (URLError, ConnectionError, TimeoutError):
        if attempt == 19:
            raise
        time.sleep(1)
for path in ('/', '/app.js', '/i18n.js', '/style.css'):
    with urlopen(base + path, timeout=10) as response:
        assert response.status == 200 and len(response.read()) > 100
query = 'priority_rule=fair&load_rule=full&dispatch_rule=any'
with urlopen(base + '/api/match?bot=custom&seed=22&' + query, timeout=30) as response:
    record = json.load(response)
    assert record['bot_config']['priority_rule'] == 'fair'
    assert len(record['log']) == 24
with urlopen(base + '/api/compare?' + query, timeout=30) as response:
    comparison = json.load(response)
    assert len(comparison['matches']) == 9
    assert {r['bot']: r['mean_score'] for r in comparison['ranking']}['nearest'] == 73.506944
print('PASS: health, assets, custom match, nine-match comparison at ' + base)
