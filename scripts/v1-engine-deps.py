#!/usr/bin/env python3
"""Managed, capped download of exact upstream native dependency archives.

This development tool does not prepare G-code, contact a printer or qualify a
backend. It uses the shared host writer lock. No archive is executed here.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.parse
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / 'integration/v1-native-dependencies.json'
HELPER = Path('/home/dev/Projects/system/100-day-development-system/scripts/resource_lifecycle.py')
HELPER_SHA256 = '8a2cb48220f14c8f4ca5c2cc9f6fcdcdf28fa436fe4b7dd50cf6489178ba6fcc'
SOURCE = '6a7763f08d1a175a464a00ce13f0b5a815662fc4'
CAP = 2 * 1024**3


class HTTPSOnly(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(newurl).scheme != 'https':
            raise ValueError('Non-HTTPS dependency redirect refused')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_lock():
    lock = json.loads(LOCK.read_text())
    if lock['source_commit'] != SOURCE or lock['platform'] != 'Linux x86_64':
        raise ValueError('Dependency baseline/platform mismatch')
    for item in lock['sources']:
        if not re.fullmatch('dep_[A-Za-z0-9]+', item['target']) or not re.fullmatch('[a-f0-9]{64}', item['sha256']):
            raise ValueError('Malformed locked dependency')
        for url in item['url'].split(';'):
            parsed = urllib.parse.urlsplit(url)
            if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise ValueError('Malformed dependency URL')
    return lock


def download(cache):
    cache.mkdir(mode=0o700, parents=True, exist_ok=True)
    if cache.is_symlink() or cache.resolve() != cache.absolute():
        raise ValueError('Dependency cache may not be a symlink')
    lock = read_lock()
    used = sum(path.stat().st_size for path in cache.rglob('*') if path.is_file())
    opener = urllib.request.build_opener(HTTPSOnly())
    records = []
    report = {'source_commit': SOURCE, 'source_lock_sha256': sha(LOCK), 'cap_bytes': CAP, 'complete': False, 'archives': records}
    artifact = Path(os.environ['RUN_ARTIFACTS']) / 'dependency-download.json'
    try:
        for item in lock['sources']:
            urls = item['url'].split(';')
            name = Path(urllib.parse.urlsplit(urls[0]).path).name
            target = cache / (item['sha256'] + '-' + name)
            if target.exists():
                if target.is_symlink() or sha(target) != item['sha256']:
                    raise ValueError('Existing dependency archive differs: ' + item['target'])
                records.append(dict(item, path=str(target), size=target.stat().st_size, cached=True))
                continue
            # Do not silently switch unreviewed mirrors; use upstream's first pinned URL.
            partial = target.with_name(target.name + '.part-' + uuid.uuid4().hex)
            record = dict(item, path=str(partial), size=0, cached=False, verified=False)
            records.append(record)
            with opener.open(urllib.request.Request(urls[0], headers={'User-Agent': 'Helix-Orca-V1-source-build'}), timeout=30) as response:
                length = response.headers.get('Content-Length')
                if length is not None and used + int(length) > CAP:
                    raise ValueError('Dependency archive would exceed 2 GiB cache/download cap')
                with partial.open('xb') as stream:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        if used + len(chunk) > CAP:
                            raise ValueError('Dependency archive exceeded 2 GiB cache/download cap')
                        stream.write(chunk)
                        used += len(chunk)
                        record['size'] += len(chunk)
            if sha(partial) != item['sha256']:
                raise ValueError('Downloaded dependency SHA-256 differs: ' + item['target'])
            partial.rename(target)
            record.update(path=str(target), verified=True)
            print('VERIFIED ' + item['target'] + ' ' + str(record['size']), flush=True)
        report['complete'] = True
    finally:
        report['cache_bytes'] = used
        artifact.write_text(json.dumps(report, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['download', '_download'])
    parser.add_argument('--cache', type=Path, default=Path.home() / '.cache/helix-orca-calibration/v1-engine/downloads')
    args = parser.parse_args()
    if args.operation == '_download':
        download(args.cache)
        return
    args.cache.mkdir(mode=0o700, parents=True, exist_ok=True)
    if sha(HELPER) != HELPER_SHA256:
        raise ValueError('Shared managed-run helper differs from approved pin')
    spec = importlib.util.spec_from_file_location('v1_engine_resource', HELPER)
    resource = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(resource)
    commit = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    with resource.ManagedRun(app='helix-orca-v1-native-download', repo=str(ROOT),
                             issue='https://github.com/bigstupid007/helix-orca-calibration/issues/14',
                             commit=commit, dirty_input=sha(LOCK), paths=[str(args.cache), str(ROOT)],
                             reserve=10*1024**3, peak=CAP+64*1024**2, margin=2*1024**3, timeout=1800) as run:
        print('Managed dependency download: ' + str(run.directory), flush=True)
        run.execute([sys.executable, str(Path(__file__).resolve()), '_download', '--cache', str(args.cache)], cwd=ROOT)
        if run.data.get('exit_code') != 0:
            raise RuntimeError('Dependency download failed; retained manifest: ' + str(run.directory))
    if run.data['state'] != 'complete':
        raise RuntimeError('Dependency download lifecycle incomplete: ' + str(run.directory))
    print('COMPLETE ' + str(run.directory))


if __name__ == '__main__':
    main()
