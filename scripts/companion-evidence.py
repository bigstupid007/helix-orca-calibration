#!/usr/bin/env python3
"""Verify the focused companion repair and preserve the prior native proof binding."""
import ast
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASELINE_COMMIT='b0484f29225dea2cc604ede978931035b9291e95'
BASELINE_PLUGIN_CONTRACT='c07d4171a6a090fdd4e192d738671b93e12055e82e7da18c930d89a53cbc93bb'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def plugin_contract(source):
    tree=ast.parse(source)
    found=0
    for node in tree.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='ROUND_TRIP_PAGE' for t in node.targets):
            node.value=ast.Constant(value='companion presentation excluded');found+=1
    if found!=1:raise ValueError('Missing or ambiguous companion page')
    return hashlib.sha256(ast.dump(tree,include_attributes=False).encode()).hexdigest()


def verify_binding(output,baseline,current):
    output=Path(output)
    companion=output/'companion'
    try:report=json.loads((companion/'report.json').read_text())
    except FileNotFoundError as exc:raise ValueError('Current source needs focused companion evidence') from exc
    if report['status']!='pass' or report['baseline_commit']!=BASELINE_COMMIT:
        raise ValueError('Focused companion proof is incomplete')
    if report['preserved_native_report_sha256']!=digest(output/'report.json') or report['preserved_browser_report_sha256']!=digest(output/'browser/report.json'):
        raise ValueError('Preserved proof changed')
    # The existing captures retain their original source identities. Only the
    # companion HTML changed; every Python reader, callback and guard is identical.
    if plugin_contract((ROOT/'plugin/helix_calibration.py').read_text())!=BASELINE_PLUGIN_CONTRACT:
        raise ValueError('Companion changed the qualified runtime contract')
    if report['current_runtime_candidate_files']!=current:
        raise ValueError('Focused proof does not bind current source')
    changed={key for key in set(baseline)|set(current) if baseline.get(key)!=current.get(key)}
    if changed!={'plugin/helix_calibration.py','scripts/temperature-evidence.py'}:
        raise ValueError('Changes exceed the companion presentation/evidence boundary')
    for key in ('scripts/companion-evidence.py','scripts/companion-browser-review.cjs'):
        if report['focused_source_files'].get(key)!=digest(ROOT/key):raise ValueError('Focused verifier/driver changed')
    browser=json.loads((companion/'browser-report.json').read_text())
    if browser['status']!='pass' or [c['width'] for c in browser['cases']]!=[360,440,640] or any(c['page_errors'] for c in browser['cases']):
        raise ValueError('Incomplete focused browser proof')
    windows=report['windows_validation']
    if windows['status']!='pass' or windows['target']!='Spare' or windows['build']!='210bc927' or windows['plugin_sha256']!=current['plugin/helix_calibration.py'] or windows['selected_temperature']!=205 or windows['not_applied'] is not True or report['normal_preservation']['unchanged'] is not True:
        raise ValueError('Missing actual qualified Windows companion proof')
    request=json.loads((companion/'request.json').read_text())
    result=json.loads((companion/'result.json').read_text())
    original=json.loads((output/'request.json').read_text())
    if any(request[key]!=original[key] for key in ('target','file','context_sha256','choices','mock_only')) or result['request_id']!=request['request_id'] or result['context_sha256']!=request['context_sha256'] or result['file_sha256']!=request['file']['sha256'] or result['value']!=205 or result['mock_only'] is not True:
        raise ValueError('Focused result does not match the preserved qualified context/file')
    required={'request.json','result.json','browser-report.json','windows-result-first.png'}|set(browser['frames'])
    if set(report['artifacts'])!=required or any(report['artifacts'].get(name)!=sha for name,sha in browser['frames'].items()):
        raise ValueError('Incomplete focused artifact inventory')
    for name,sha in report['artifacts'].items():
        path=Path(name)
        if path.is_absolute() or '..' in path.parts or digest(companion/path)!=sha:raise ValueError('Focused artifact mismatch')
    return report
