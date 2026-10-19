#!/usr/bin/env python3
"""Real Windows AMD64 native-package generation and independent strict parity.

Public qualification tooling only. Profiles/G-code remain Windows-local; no
printer interface, profile writeback, simulated generator or warning waiver.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.abc
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import stat
import sys
import time
import types

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
c = e = p = pe = None
PIN = '6a7763f08d1a175a464a00ce13f0b5a815662fc4'
SCHEMA = 'helix-orca-v1-windows-native-qualification/v1'
SOURCE_SCHEMA = 'helix-orca-v1-reviewed-python-source/v1'
CALIBRATIONS = ('pressure_advance_pattern','retraction','max_volumetric_speed','temperature')
MODULE_NAMES = frozenset('integration.'+name for name in ('v1_contract','v1_engine','v1_parity','v1_pe'))
SOURCE_NAMES = (
    'integration/v1-native-engine/windows-cmake/FindEXPAT.cmake',
    'integration/v1_contract.py','integration/v1_parity.py','integration/v1_engine.py','integration/v1_pe.py',
    'integration/v1-native-dependencies.json','integration/v1-native-engine/main.cpp',
    'integration/v1-native-engine/add-target.cmake','integration/v1-native-engine/temperature_prepare.hpp',
    'integration/v1-native-build-tools.py','scripts/v1-engine-native.py',
    'integration/v1-native-windows-dependencies.json','scripts/v1-engine-windows.py',
    '.github/workflows/v1-windows-engine.yml',
    'scripts/v1-windows-native-qualify.py','scripts/v1-windows-parity.py')


class Refused(ValueError):
    pass


def safe_path(path, directory=False):
    """Reject path traversal and every symlink/reparse component before resolve."""
    path = Path(path)
    if str(path).startswith(('\\', '//')) or '..' in path.parts:
        raise Refused('reviewed_source_path_unsafe')
    path = path.absolute()
    for component in reversed((path, *path.parents)):
        status = component.lstat()
        if stat.S_ISLNK(status.st_mode) or getattr(status,'st_file_attributes',0) & 0x400:
            raise Refused('reviewed_source_link_or_reparse')
    status = path.lstat()
    if not (stat.S_ISDIR(status.st_mode) if directory else stat.S_ISREG(status.st_mode)):
        raise Refused('reviewed_source_not_regular')
    return path


class ReviewedSource:
    """Execute captured, externally pinned source bytes; never import .pyc."""
    def __init__(self, manifest_path, expected_sha256):
        self.root = safe_path(ROOT,directory=True)
        self.manifest = safe_path(manifest_path)
        if self.manifest.suffix != '.json' or self.manifest in {self.root/name for name in SOURCE_NAMES}:
            raise Refused('reviewed_source_manifest_path_mismatch')
        self.manifest_sha256 = digest_arg(expected_sha256)
        data = self.manifest.read_bytes()
        if len(data)>1048576 or hashlib.sha256(data).hexdigest()!=self.manifest_sha256:
            raise Refused('reviewed_source_manifest_digest_mismatch')
        manifest = json.loads(data)
        if (not isinstance(manifest,dict) or set(manifest)!= {'schema','files'}
                or manifest['schema']!=SOURCE_SCHEMA or not isinstance(manifest['files'],dict)
                or set(manifest['files'])!=set(SOURCE_NAMES)):
            raise Refused('reviewed_source_inventory_mismatch')
        self.files = {name:digest_arg(value) for name,value in manifest['files'].items()}
        self.bytes = self.recheck()
        if safe_path(__file__) != self.root/'scripts/v1-windows-native-qualify.py':
            raise Refused('reviewed_helper_path_mismatch')

    def recheck(self):
        manifest_bytes = safe_path(self.manifest).read_bytes()
        if len(manifest_bytes)>1048576 or hashlib.sha256(manifest_bytes).hexdigest()!=self.manifest_sha256:
            raise Refused('reviewed_source_manifest_changed')
        safe_path(self.root,directory=True)
        allowed = {self.root/name for name in SOURCE_NAMES}
        if self.manifest.is_relative_to(self.root): allowed.add(self.manifest)
        allowed_dirs = {self.root}
        for path in allowed:
            allowed_dirs.update(parent for parent in path.parents if parent.is_relative_to(self.root))
        for directory, dirs, files in os.walk(self.root,followlinks=False):
            for name in dirs:
                path = safe_path(Path(directory)/name,directory=True)
                if path not in allowed_dirs: raise Refused('unexpected_owned_source_directory_or_bytecode')
            for name in files:
                path = safe_path(Path(directory)/name)
                if path not in allowed: raise Refused('unexpected_owned_source_file_or_bytecode')
        captured = {}
        for name,expected in self.files.items():
            path = safe_path(self.root/name)
            data = path.read_bytes()
            if len(data)>1048576 or hashlib.sha256(data).hexdigest()!=expected:
                raise Refused('reviewed_source_file_changed')
            captured[name] = data
        return captured

    def execute(self,name,relative):
        module = types.ModuleType(name)
        module.__file__ = str(self.root/relative)
        module.__package__ = name.rpartition('.')[0]
        # Compile only the captured, hash-verified source. A loader cannot pick
        # stale bytecode or race a second unverified disk read.
        exec(compile(self.bytes[relative],module.__file__,'exec'),module.__dict__)
        return module


def load_owned(reviewed):
    global c,e,p,pe
    if any(name=='integration' or name.startswith('integration.') for name in sys.modules):
        raise Refused('owned_modules_already_loaded')
    class Loader(importlib.abc.Loader):
        def __init__(self,relative): self.relative = relative
        def create_module(self,spec): return None
        def exec_module(self,module):
            module.__file__ = str(reviewed.root/self.relative)
            exec(compile(reviewed.bytes[self.relative],module.__file__,'exec'),module.__dict__)
    class Finder(importlib.abc.MetaPathFinder):
        def find_spec(self,fullname,path=None,target=None):
            if fullname.startswith('integration.'):
                relative = fullname.replace('.','/')+'.py'
                if fullname not in MODULE_NAMES: raise Refused('unexpected_owned_module_import')
                return importlib.util.spec_from_loader(fullname,Loader(relative),origin=str(reviewed.root/relative))
    package = types.ModuleType('integration');package.__path__=[]
    package.__package__='integration'
    sys.modules['integration']=package
    sys.meta_path.insert(0,Finder())
    from integration import v1_contract,v1_engine,v1_parity,v1_pe
    c,e,p,pe = v1_contract,v1_engine,v1_parity,v1_pe
    reviewed.recheck()


def digest_arg(value):
    if not isinstance(value,str) or re.fullmatch('[a-f0-9]{64}',value) is None:
        raise Refused('invalid_expected_digest')
    return value


def commit_arg(value):
    if re.fullmatch('[a-f0-9]{40}',value) is None: raise Refused('invalid_application_commit')
    return value


def sha(path,maximum=2*1024**3):
    path = safe_path(path)
    if path.stat().st_size > maximum: raise Refused('local_file_oversized')
    with path.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()


def read_json(path,maximum=1048576):
    sha(path,maximum)
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write_json(path,value):
    with Path(path).open('xb') as stream: stream.write(c.canonical(value))


class PinnedInputs:
    """Preserve external input pins and receipt-derived DLL/resource closure."""
    def __init__(self): self.files = {}
    def add(self,path,expected,maximum=2*1024**3):
        path = safe_path(path)
        expected = digest_arg(expected)
        if sha(path,maximum)!=expected: raise Refused('qualification_input_digest_mismatch')
        if path in self.files and self.files[path][0]!=expected:
            raise Refused('qualification_input_pin_conflict')
        if path in self.files: maximum=min(maximum,self.files[path][1])
        self.files[path]=(expected,maximum)
        return path
    def recheck(self):
        for path,(expected,maximum) in self.files.items():
            if sha(path,maximum)!=expected: raise Refused('qualification_input_changed')


def checked_context(args,pinned):
    pinned.add(args.context,args.context_sha256,1048576)
    pinned.add(args.parameters,args.parameters_sha256,16384)
    pinned.add(args.native,args.native_sha256,p.MAX_GCODE_BYTES)
    context = c.validate_context(read_json(args.context))
    if context['runtime']!=p.PINS[PIN]: raise Refused('exact_october15_context_required')
    parameters = c.validate_parameters(args.calibration,read_json(args.parameters,16384))
    return context,parameters


def request_for(context,calibration,parameters):
    now = int(time.time())
    request = dict(schema='helix-orca-v1-request/v1',request_id=secrets.token_hex(16),
        origin_id=context['origin_id'],context_sha256=c.digest(context),calibration=calibration,
        parameters=parameters,created_at=now,expires_at=now+3600,not_applied=True)
    return c.validate_request(request,now=now)


def prepare_output(args,reviewed):
    destination = Path(args.output_dir).absolute()
    if destination.is_relative_to(reviewed.root) or destination.exists() or destination.is_symlink():
        raise Refused('new_private_output_outside_source_required')
    safe_path(destination.parent,directory=True)
    destination.mkdir(mode=0o700)
    return destination


def reference_for(args,context,parameters,pinned):
    pinned.add(args.native_manifest,args.native_manifest_sha256,1048576)
    manifest = read_json(args.native_manifest)
    inputs = p.generation_inputs(dict(calibration=args.calibration,parameters=parameters,
        context_sha256=c.digest(context)),context,PIN)
    evidence = manifest.get('evidence',[])
    if (manifest.get('schema')!='helix-orca-v1-native-reference/v1' or manifest.get('method')!='native_orca_ui'
            or manifest.get('imported_candidate') is not False or manifest.get('inputs_sha256')!=c.digest(inputs)
            or manifest.get('source_commit')!=PIN or manifest.get('runtime')!=p.PINS[PIN]
            or manifest.get('artifact')!=p.file_record(args.native) or not 3<=len(evidence)<=17):
        raise Refused('independent_native_reference_mismatch')
    paths = set()
    for item in evidence:
        artifact = item['artifact']
        path = pinned.add(item['path'],artifact['sha256'],p.MAX_GCODE_BYTES)
        if p.file_record(path)!=artifact: raise Refused('independent_native_evidence_changed')
        paths.add(path)
    if len(paths)!=len(evidence) or safe_path(args.context) not in paths:
        raise Refused('distinct_native_context_and_ui_evidence_required')
    return manifest,inputs


def register_reference(args,reviewed,pinned,context,parameters):
    if not 2<=len(args.native_evidence)<=16 or len(args.native_evidence)!=len(args.native_evidence_sha256):
        raise Refused('two_distinct_hash_pinned_native_ui_pngs_required')
    evidence = []
    for path,expected in zip(args.native_evidence,args.native_evidence_sha256):
        path = pinned.add(path,expected,16*1024**2)
        with path.open('rb') as stream:
            if path.suffix.lower()!='.png' or stream.read(8)!=b'\x89PNG\r\n\x1a\n':
                raise Refused('native_ui_png_evidence_required')
        evidence.append(path)
    if len(set([safe_path(args.context),*evidence]))!=len(evidence)+1:
        raise Refused('distinct_native_context_and_ui_evidence_required')
    manifest = p.create_native_reference(args.native,context,args.calibration,parameters,PIN,[args.context,*evidence])
    inputs = p.generation_inputs(dict(calibration=args.calibration,parameters=parameters,
        context_sha256=c.digest(context)),context,PIN)
    destination = prepare_output(args,reviewed)
    try:
        invariants = p.invariants(Path(args.native).read_text(encoding='utf-8'),inputs)
    except Exception as error:
        reviewed.recheck();pinned.recheck()
        write_json(destination/'native-invariant-failure.json',dict(qualified=False,prepared=False,
            calibration=args.calibration,parameters=parameters,context_sha256=c.digest(context),
            type=type(error).__name__,detail=str(error)))
        raise Refused('native_invariant_rejected') from error
    reviewed.recheck();pinned.recheck()
    summary = dict(schema=SCHEMA,success=True,mode='register-native-only',calibration=args.calibration,
        parameters=parameters,context_sha256=c.digest(context),context_file_sha256=args.context_sha256,
        native=dict(size=p.file_record(args.native)['size'],sha256=args.native_sha256),
        native_manifest_sha256=c.digest(manifest),inputs_sha256=c.digest(inputs),
        native_invariants_passed=True,qualified=False,prepared=False,
        source_files=reviewed.files,reviewed_source_manifest_sha256=reviewed.manifest_sha256,
        physical_actions=False,physical_readiness=False,not_applied=True)
    summary['invariants']={key:invariants[key] for key in ('model_moves','layers','executable_commands')
                           if type(invariants.get(key)) is int}
    write_json(destination/'native-reference.json',manifest)
    write_json(destination/'native-inspection.json',dict(inputs=inputs,invariants=invariants,qualified=False,prepared=False))
    reviewed.recheck();pinned.recheck()
    write_json(destination/'summary.json',summary)
    return summary


def backend_for(args,pinned):
    required = ('native_executable','native_executable_sha256','build_receipt','build_receipt_sha256',
                'build_inputs','build_inputs_sha256','resources','native_manifest','native_manifest_sha256')
    if any(getattr(args,key,None) is None for key in required): raise Refused('complete_native_package_and_reference_required')
    for name,maximum in (('native_executable',2*1024**3),('build_receipt',1048576),('build_inputs',1048576)):
        pinned.add(getattr(args,name),getattr(args,name+'_sha256'),maximum)
    resources = safe_path(args.resources,directory=True)
    config = dict(native_executable=dict(path=str(safe_path(args.native_executable)),sha256=args.native_executable_sha256),
        build_receipt=dict(path=str(safe_path(args.build_receipt)),sha256=args.build_receipt_sha256),
        build_inputs=dict(path=str(safe_path(args.build_inputs)),sha256=args.build_inputs_sha256),
        native_resources=str(resources),timeout_seconds=args.timeout_seconds)
    backend = e._backend(config)
    receipt = backend['receipt']
    if receipt.get('target')!=e._WINDOWS_TARGET: raise Refused('actual_windows_amd64_package_required')
    if args.application_commit and receipt.get('application_commit')!=args.application_commit:
        raise Refused('expected_application_commit_mismatch')
    for name,record in receipt['runtime_dlls'].items():
        if not pe.DLL_NAME.fullmatch(name): raise Refused('unsafe_runtime_dll_name')
        pinned.add(backend['executable'].parent/name,record['sha256'],256*1024**2)
    for name,expected in receipt['resources'].items():
        if name not in e._NATIVE_ASSETS: raise Refused('unexpected_native_resource')
        pinned.add(resources/name,expected,32*1024**2)
    return config,backend


def verify_all(reviewed,pinned,config=None):
    reviewed.recheck();pinned.recheck()
    if config is not None: e._backend(config)


def native_reference_config(args,inputs,pinned):
    """Catalog selection changes no current reference, request or context."""
    catalog_path = getattr(args,'native_catalog',None)
    catalog_sha = getattr(args,'native_catalog_sha256',None)
    if catalog_path is None:
        if catalog_sha is not None: raise Refused('native_catalog_path_and_digest_required')
        return dict(native_reference=dict(
            manifest=dict(path=str(safe_path(args.native_manifest)),sha256=args.native_manifest_sha256),
            gcode=dict(path=str(safe_path(args.native)),sha256=args.native_sha256)))
    if catalog_sha is None: raise Refused('native_catalog_path_and_digest_required')
    pinned.add(catalog_path,catalog_sha,1048576)
    catalog = read_json(catalog_path)
    config = dict(native_references=catalog)
    selected = e.select_native_reference(config,c.digest(inputs))
    for reference in catalog.values():
        pinned.add(reference['manifest']['path'],reference['manifest']['sha256'],1048576)
        pinned.add(reference['gcode']['path'],reference['gcode']['sha256'],p.MAX_GCODE_BYTES)
    if selected is not None:
        if (safe_path(selected['manifest']['path'])!=safe_path(args.native_manifest)
                or selected['manifest']['sha256']!=args.native_manifest_sha256
                or safe_path(selected['gcode']['path'])!=safe_path(args.native)
                or selected['gcode']['sha256']!=args.native_sha256):
            raise Refused('catalog_selection_differs_from_expected_native_reference')
    # A missing key deliberately reaches the real generator. Native warnings
    # retain priority; after successful processing the unchanged parity gate
    # reports this exact context/parameter combination as unqualified.
    return config


def blocked_summary(args,request,destination,reviewed,pinned,config,error):
    verify_all(reviewed,pinned,config)
    code = error.code if isinstance(error,e.NativeEngineBlocked) else 'native_generation_failed'
    if not isinstance(code,str) or re.fullmatch('[a-z0-9_]{1,64}',code) is None: code='native_generation_failed'
    value = dict(schema=SCHEMA,success=False,qualified=False,prepared=False,blocker=code,
        calibration=request['calibration'],parameters=request['parameters'],request_id=request['request_id'],
        request_sha256=c.digest(request),context_sha256=request['context_sha256'],
        reviewed_source_manifest_sha256=reviewed.manifest_sha256,source_files=reviewed.files,
        physical_actions=False,physical_readiness=False,not_applied=True)
    if getattr(args,'native_catalog',None) is not None:
        value['native_catalog_sha256'] = args.native_catalog_sha256
    if code=='native_reference_missing':
        value['blocker_reason']='No native catalog entry matches the exact context and selected parameters; original values were preserved.'
    elif code=='native_reference_unavailable':
        value['blocker_reason']='The exact catalog reference is unavailable for parity verification; inspect the retained private report.'
    processing_path = destination/'job/native-processing.json'
    if processing_path.is_file():
        processing = read_json(processing_path,65536)
        failure = e._processing_failure(processing)
        if failure:
            value['blocker'] = failure[1]
            value['blocker_reason'] = failure[0]
            value['warning_codes'] = [item['error_code'] for item in processing['warnings']]
            value['processor_error_mask'] = processing['error_code']
            value['processing_sha256'] = sha(processing_path,65536)
    artifact = destination/'job/native-calibration.gcode'
    if artifact.is_file():
        value['candidate'] = dict(size=artifact.stat().st_size,sha256=sha(artifact,p.MAX_GCODE_BYTES))
    verify_all(reviewed,pinned,config)
    write_json(destination/'blocked-summary.json',value)
    return value


def run(args):
    if os.name!='nt': raise Refused('windows_execution_required')
    if not sys.flags.isolated or not sys.flags.no_site: raise Refused('isolated_no_site_interpreter_required')
    if type(args.timeout_seconds) is not int or not 1<=args.timeout_seconds<=120:
        raise Refused('native_deadline_must_be_1_through_120_seconds')
    reviewed = ReviewedSource(args.source_manifest,args.source_manifest_sha256)
    load_owned(reviewed)
    pinned = PinnedInputs()
    context,parameters = checked_context(args,pinned)
    if args.register_native_only:
        if getattr(args,'native_catalog',None) is not None or getattr(args,'native_catalog_sha256',None) is not None:
            raise Refused('native_catalog_is_for_generation_only')
        return register_reference(args,reviewed,pinned,context,parameters)
    config,backend = backend_for(args,pinned)
    manifest,inputs = reference_for(args,context,parameters,pinned)
    config.update(native_reference_config(args,inputs,pinned))
    request = request_for(context,args.calibration,parameters)
    destination = prepare_output(args,reviewed)
    for name,value in (('request.json',request),('source-files.json',reviewed.files),('generation-config.json',config)):
        write_json(destination/name,value)
    verify_all(reviewed,pinned,config)
    try:
        prepared = e.generate(request,context,destination/'job',config)
    except e.NativeEngineBlocked as error:
        write_json(destination/'generation-failure.json',dict(type=type(error).__name__,detail=str(error),
            blocker=error.code,qualified=False,prepared=False,request_sha256=c.digest(request),not_applied=True))
        return blocked_summary(args,request,destination,reviewed,pinned,config,error)
    verify_all(reviewed,pinned,config)
    prepared = c.validate_prepared(prepared,request)
    artifact = destination/'job/native-calibration.gcode'
    report = read_json(destination/'job/parity.json')
    if (prepared['artifact']!=p.file_record(artifact) or prepared['parity']['report_sha256']!=c.digest(report)
            or prepared['generator']!={'build':PIN,'route':'native-engine-v1'}
            or report.get('inputs_sha256')!=c.digest(inputs)
            or prepared['parity']['qualified'] is not report.get('qualified')):
        raise Refused('actual_native_prepared_or_parity_binding_failed')
    if report.get('qualified') is True and not p.verify_report(report,prepared):
        raise Refused('strict_native_parity_revalidation_failed')
    if (report.get('qualified') is not True and report.get('reference') is None
            and 'native_references' in config):
        code = ('native_reference_missing' if e.select_native_reference(config,c.digest(inputs)) is None
                else 'native_reference_unavailable')
        return blocked_summary(args,request,destination,reviewed,pinned,config,
            e.NativeEngineBlocked('Exact-input native catalog reference unavailable',code))
    sanitizer = reviewed.execute('native_qualification_sanitizer','scripts/v1-windows-parity.py')
    summary = sanitizer.sanitized(report,prepared,manifest,reviewed.files)
    verify_all(reviewed,pinned,config)
    provenance = dict(schema=SCHEMA,source_files=reviewed.files,
        reviewed_source_manifest_sha256=reviewed.manifest_sha256,request_sha256=c.digest(request),
        context_sha256=c.digest(context),context_file_sha256=args.context_sha256,
        parameters_sha256=args.parameters_sha256,build_receipt_sha256=args.build_receipt_sha256,
        build_inputs_sha256=args.build_inputs_sha256,native_executable_sha256=args.native_executable_sha256,
        native_manifest_file_sha256=args.native_manifest_sha256,native_sha256=args.native_sha256,
        application_commit=backend['receipt']['application_commit'],prepared_sha256=c.digest(prepared),
        report_sha256=c.digest(report),timeout_seconds=args.timeout_seconds,not_applied=True,
        physical_actions=False,physical_readiness=False)
    if getattr(args,'native_catalog',None) is not None:
        provenance['native_catalog_sha256'] = args.native_catalog_sha256
    summary.update(schema=SCHEMA,mode='native-package-generation',calibration=args.calibration,
        parameters=parameters,request_id=request['request_id'],request_sha256=c.digest(request),
        context_sha256=c.digest(context),prepared=bool(report.get('qualified') is True),
        production_generator='integration.v1_engine.generate',timeout_seconds=args.timeout_seconds,
        build_receipt_sha256=args.build_receipt_sha256,build_inputs_sha256=args.build_inputs_sha256,
        native_executable_sha256=args.native_executable_sha256,
        reviewed_source_manifest_sha256=reviewed.manifest_sha256,
        generation_provenance_sha256=c.digest(provenance))
    if getattr(args,'native_catalog',None) is not None:
        summary['native_catalog_sha256'] = args.native_catalog_sha256
    if len(c.canonical(summary))>65536: raise Refused('summary_too_large')
    verify_all(reviewed,pinned,config)
    write_json(destination/'generation-provenance.json',provenance)
    write_json(destination/'summary.json',summary)
    return summary


class Parser(argparse.ArgumentParser):
    def error(self,message): raise Refused('invalid_cli_arguments')


def main():
    try:
        parser = Parser(description=__doc__)
        parser.add_argument('--calibration',required=True,choices=CALIBRATIONS)
        parser.add_argument('--register-native-only',action='store_true')
        for name in ('source-manifest','context','parameters','native','output-dir'):
            parser.add_argument('--'+name,required=True,type=Path)
        for name in ('source-manifest-sha256','context-sha256','parameters-sha256','native-sha256'):
            parser.add_argument('--'+name,required=True,type=digest_arg)
        for name in ('native-manifest','native-executable','build-receipt','build-inputs','resources','native-catalog'):
            parser.add_argument('--'+name,type=Path)
        for name in ('native-manifest-sha256','native-executable-sha256','build-receipt-sha256','build-inputs-sha256','native-catalog-sha256'):
            parser.add_argument('--'+name,type=digest_arg)
        parser.add_argument('--native-evidence',action='append',type=Path,default=[])
        parser.add_argument('--native-evidence-sha256',action='append',type=digest_arg,default=[])
        parser.add_argument('--application-commit',type=commit_arg)
        parser.add_argument('--timeout-seconds',type=int,default=120)
        result = run(parser.parse_args())
        print(c.canonical(result).decode())
        return 0 if result.get('qualified') or result.get('mode')=='register-native-only' else 2
    except Exception as error:
        code = str(error) if isinstance(error,Refused) else error.code if e is not None and isinstance(error,e.NativeEngineBlocked) else 'local_native_qualification_failed'
        print(json.dumps(dict(schema=SCHEMA,success=False,qualified=False,prepared=False,failure=code,
            physical_actions=False,physical_readiness=False),sort_keys=True))
        return 2


if __name__=='__main__': raise SystemExit(main())
