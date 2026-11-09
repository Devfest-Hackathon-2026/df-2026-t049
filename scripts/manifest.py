"""Refresh/check the repository source inventory (text hashes normalized to LF)."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--check', action='store_true')
args = parser.parse_args()
paths = subprocess.check_output(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=root).decode().split('\0')
files = {}
for name in sorted(set(paths) - {'', 'MANIFEST.json'}):
    path = root / name
    if not path.is_file():
        continue
    data = path.read_bytes()
    if path.suffix.lower() not in ('.png', '.jpg', '.mp4'):
        data = data.replace(b'\r\n', b'\n')
    files[name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
manifest = {'package_version': '0.4-mvp-candidate', 'text_line_endings': 'LF', 'files': files}
target = root / 'MANIFEST.json'
if args.check:
    if json.loads(target.read_text(encoding='utf-8')) != manifest:
        raise SystemExit('Manifest differs; run python scripts/manifest.py')
    print(f'PASS: {len(files)} source files match MANIFEST.json')
else:
    target.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Updated {len(files)} source files')
