"""Source-bound native Temperature mesh preparation; no slicing or parity claim.

The caller supplies a trusted native build configuration. Retained profiles and
hooks stay in the private job directory. Only a mesh descriptor is returned for
the existing stock recipe; its ordinary independent parity gate is unchanged.
"""
from __future__ import annotations
import json
import math
import os
from pathlib import Path
import struct
import subprocess

from integration import v1_contract as contract
from integration import v1_engine as engine


class TemperatureGeometryBlocked(RuntimeError):
    pass


def inspect_stl(path):
    """Independently reject truncated/nonfinite/degenerate native STL exports."""
    path = Path(path)
    if path.is_symlink() or not path.is_file() or not 84 <= path.stat().st_size <= 32 * 1024**2:
        raise TemperatureGeometryBlocked('Bounded regular native STL required')
    data = path.read_bytes()
    count = struct.unpack_from('<I', data, 80)[0]
    if count < 1 or len(data) != 84 + 50 * count:
        raise TemperatureGeometryBlocked('Native STL triangle inventory differs')
    lower, upper = [math.inf] * 3, [-math.inf] * 3
    for offset in range(84, len(data), 50):
        values = struct.unpack_from('<12f', data, offset)
        if not all(math.isfinite(v) for v in values):
            raise TemperatureGeometryBlocked('Native STL has nonfinite coordinates')
        a, b, c = values[3:6], values[6:9], values[9:12]
        ab, ac = [b[i] - a[i] for i in range(3)], [c[i] - a[i] for i in range(3)]
        cross = (ab[1]*ac[2]-ab[2]*ac[1], ab[2]*ac[0]-ab[0]*ac[2], ab[0]*ac[1]-ab[1]*ac[0])
        if all(value == 0 for value in cross):
            raise TemperatureGeometryBlocked('Native STL has a degenerate triangle')
        for vertex in (a, b, c):
            for i, value in enumerate(vertex):
                lower[i], upper[i] = min(lower[i], value), max(upper[i], value)
    if any(hi <= lo for lo, hi in zip(lower, upper)):
        raise TemperatureGeometryBlocked('Native STL has an empty extent')
    return {'triangles': count, 'lower_mm': lower, 'upper_mm': upper}


def prepare(request, snapshot, output_dir, config):
    """Run only real native Cut/scale preparation with source-bound provenance."""
    request = contract.validate_request(request, now=config.get('now'))
    snapshot = contract.validate_context(snapshot)
    if request['calibration'] != 'temperature':
        raise TemperatureGeometryBlocked('Native geometry preparation supports Temperature only')
    if (request['context_sha256'] != contract.digest(snapshot) or
            request['origin_id'] != snapshot['origin_id']):
        raise TemperatureGeometryBlocked('Temperature request differs from immutable context')
    if snapshot['runtime'] != {'version': '2.5.0-dev', 'build': '6a7763f0'}:
        raise TemperatureGeometryBlocked('Exact October 15 context required')
    try:
        nozzle = float(snapshot['effective']['nozzle_diameter'])
    except (KeyError, TypeError, ValueError) as exc:
        raise TemperatureGeometryBlocked('Effective single nozzle is unavailable') from exc
    if not math.isfinite(nozzle) or nozzle != snapshot['nozzle_mm']:
        raise TemperatureGeometryBlocked('Effective nozzle differs from immutable context')
    if snapshot['effective'].get('belt_printer') not in ('0', 'false'):
        raise TemperatureGeometryBlocked('Native standard Temperature requires explicit non-belt context')
    timeout = config.get('timeout_seconds', 60)
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 1 <= timeout <= 300:
        raise TemperatureGeometryBlocked('Native preparation deadline must be 1 through 300 seconds')
    backend = engine.require_native_generation('temperature', config)
    destination = Path(output_dir)
    if destination.is_symlink() or destination.exists():
        raise TemperatureGeometryBlocked('Native preparation requires a new private job directory')
    destination.mkdir(mode=0o700, parents=True)
    destination = destination.resolve()
    (destination / 'request.json').write_bytes(contract.canonical(request))
    (destination / 'context.json').write_bytes(contract.canonical(snapshot))
    argv = [str(backend['executable']), '--prepare-temperature',
            str(destination / 'request.json'), str(destination / 'context.json'),
            str(backend['resources']), str(destination)]
    invocation = {'argv': argv, 'source_commit': engine.ORCA_SOURCE,
                  'executable_sha256': backend['receipt']['adapter']['sha256'],
                  'build_receipt_sha256': backend['receipt_sha256'],
                  'build_inputs_sha256': backend['inputs_sha256']}
    (destination / 'invocation.json').write_bytes(contract.canonical(invocation))
    runner = config.get('runner')
    if runner:
        code = runner(argv, destination)
    else:
        environment = os.environ.copy()
        environment['OMP_NUM_THREADS'] = '2'
        with (destination / 'prepare.log').open('xb') as log:
            try:
                code = subprocess.run(argv, cwd=destination, stdin=subprocess.DEVNULL,
                    stdout=log, stderr=subprocess.STDOUT, env=environment,
                    timeout=timeout, check=False).returncode
            except subprocess.TimeoutExpired as exc:
                raise TemperatureGeometryBlocked('Native geometry preparation exceeded its deadline') from exc
    if code != 0:
        raise TemperatureGeometryBlocked('Native geometry preparation failed; inspect private prepare.log')
    # No slicing or fake result can be smuggled into this preparation stage.
    if any(destination.glob('*.gcode')) or (destination / 'prepared.json').exists():
        raise TemperatureGeometryBlocked('Geometry-only preparation unexpectedly produced G-code or Prepared')
    metadata_path = destination / 'temperature-geometry.json'
    if metadata_path.is_symlink() or not metadata_path.is_file() or metadata_path.stat().st_size > 16384:
        raise TemperatureGeometryBlocked('Native geometry metadata unavailable')
    metadata = json.loads(metadata_path.read_text())
    expected = {'schema': 'helix-orca-v1-native-temperature-geometry/v1',
                'source_commit': engine.ORCA_SOURCE, 'calibration': 'temperature',
                'request_id': request['request_id'], 'origin_id': request['origin_id'],
                'context_sha256': request['context_sha256'], 'parameters': request['parameters'],
                'nozzle_mm': snapshot['nozzle_mm'], 'model': 'model.stl',
                'gcode_generated': False, 'qualified': False, 'not_applied': True}
    if any(contract.canonical(metadata.get(k)) != contract.canonical(v) for k, v in expected.items()):
        raise TemperatureGeometryBlocked('Native geometry metadata differs from exact request')
    metrics = inspect_stl(destination / 'model.stl')
    if any(metadata.get(k) != v for k, v in metrics.items()):
        raise TemperatureGeometryBlocked('Native geometry metadata differs from exported STL')
    model = {'path': str(destination / 'model.stl'),
             'sha256': engine._sha_file(destination / 'model.stl'),
             'source_commit': engine.ORCA_SOURCE, 'nozzle_mm': snapshot['nozzle_mm'],
             'parameters': request['parameters']}
    receipt = dict(expected, model=model, request_sha256=contract.digest(request),
                   native_metadata_sha256=engine._sha_file(metadata_path), metrics=metrics,
                   build_receipt_sha256=backend['receipt_sha256'],
                   build_inputs_sha256=backend['inputs_sha256'],
                   executable_sha256=backend['receipt']['adapter']['sha256'])
    (destination / 'geometry-receipt.json').write_bytes(contract.canonical(receipt))
    (destination / 'temperature-model.json').write_bytes(contract.canonical({'temperature_model': model}))
    return receipt
