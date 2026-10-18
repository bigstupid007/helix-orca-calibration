"""One explicit stock/native generation policy; never silently change a route."""
from integration import v1_contract as contract
from integration import v1_generation as stock
from integration import v1_engine as native

DEFAULT_ROUTES = {kind: ('stock-cli' if kind in ('temperature', 'flow_ratio_yolo') else 'native-engine')
                  for kind in contract.CALIBRATIONS}


def routes(config):
    if not isinstance(config, dict):
        raise contract.ContractError('Private generator configuration must be an object')
    chosen = config.get('routes', {})
    if not isinstance(chosen, dict) or set(chosen) - set(DEFAULT_ROUTES):
        raise contract.ContractError('Unknown calibration route configuration')
    result = dict(DEFAULT_ROUTES, **chosen)
    if any(value not in ('stock-cli', 'native-engine') for value in result.values()):
        raise contract.ContractError('Unsupported generator route; no fallback is permitted')
    return result


def capabilities(config=None):
    config = config or {}
    chosen = routes(config)
    stock_caps = {item['id']: item for item in stock.capabilities(config)}
    native_caps = {item['id']: item for item in native.capabilities(config.get('native_engine'))}
    result = []
    for kind in contract.CALIBRATIONS:
        source = stock_caps if chosen[kind] == 'stock-cli' else native_caps
        item = source.get(kind, dict(available=False, reason='This calibration has no supported native-engine route.'))
        reason = str(item['reason']).encode('utf-8')[:512].decode('utf-8', errors='ignore')
        result.append(dict(id=kind, available=item['available'] is True, reason=reason))
    return result


def generate(request, snapshot, output_dir, config):
    kind = request.get('calibration')
    if kind not in DEFAULT_ROUTES:
        raise contract.ContractError('Unknown calibration')
    selected = routes(config)[kind]
    if selected == 'native-engine':
        try:
            return native.generate(request, snapshot, output_dir, config.get('native_engine', {}))
        except native.NativeEngineBlocked as exc:
            raise stock.GenerationBlocked(exc.code, exc.reason) from exc
    return stock.generate(request, snapshot, output_dir, config)
