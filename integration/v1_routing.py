"""One explicit stock/native generation policy; never silently change a route."""
from integration import v1_contract as contract
from integration import v1_generation as stock
from integration import v1_engine as native
from integration.v1_qualification import PACKAGE_BINDING_KEY, runtime_build_qualification

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
    qualification = None
    if config.get('build_qualification') is not None:
        qualification = runtime_build_qualification(config)
    stock_caps = {item['id']: item for item in stock.capabilities(config)}
    native_caps = {item['id']: item for item in native.capabilities(config.get('native_engine'))}
    result = []
    for kind in contract.CALIBRATIONS:
        source = stock_caps if chosen[kind] == 'stock-cli' else native_caps
        item = source.get(kind, dict(available=False, reason='This calibration has no supported native-engine route.'))
        reason = str(item['reason']).encode('utf-8')[:512].decode('utf-8', errors='ignore')
        build_qualified = qualification is not None and qualification['routes'][kind]['qualified'] is True
        expected_route = 'stock-cli-recipe-v2' if chosen[kind] == 'stock-cli' else 'native-engine-v2'
        build_qualified = build_qualified and qualification['routes'][kind]['route_id'] == expected_route if qualification is not None else False
        available = item['available'] is True and (qualification is None or build_qualified)
        if qualification is not None:
            reason = (('Build-qualified ' + chosen[kind] + ' route; each exact job still validates context, '
                       'processing, artifact and warning acknowledgement.') if available else
                      ('Build-level route qualification/resource unavailable. ' + reason))
        row = dict(id=kind, available=available, reason=reason)
        if qualification is not None:
            row['qualification_sha256'] = contract.digest(qualification)
        result.append(row)
    return result


def generate(request, snapshot, output_dir, config):
    kind = request.get('calibration')
    if kind not in DEFAULT_ROUTES:
        raise contract.ContractError('Unknown calibration')
    # Current V2 qualification is attached to a build/route matrix, never to
    # one request's G-code catalog membership. Stock recipes and the adapter
    # both finish through Orca's ordinary slicing/export path.
    selected = routes(config)[kind]
    if selected == 'native-engine':
        try:
            native_config = dict(config.get('native_engine', {}))
            if request.get('schema') == 'helix-orca-v1-request/v2':
                if config.get('build_qualification') is not None:
                    native_config['build_qualification'] = config['build_qualification']
                    native_config['qualification_closure'] = config.get('qualification_closure')
                    if PACKAGE_BINDING_KEY in config:
                        native_config[PACKAGE_BINDING_KEY] = config[PACKAGE_BINDING_KEY]
                else:
                    native_config['qualification_intent'] = config.get('qualification_intent')
                    native_config['qualification_authorizer'] = config.get('qualification_authorizer')
            return native.generate(request, snapshot, output_dir, native_config)
        except native.NativeEngineBlocked as exc:
            raise stock.GenerationBlocked(exc.code, exc.reason) from exc
    return stock.generate(request, snapshot, output_dir, config)
