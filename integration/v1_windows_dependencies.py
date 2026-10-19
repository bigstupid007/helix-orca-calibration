"""Explicitly pinned public Windows dependency checkpoints, never qualification.

No cache discovery, network, execution or fallback. The caller supplies exact
reviewed producer/recipe provenance and owns the parent directories and budget.
Only complete regular-file inventories under prefix/downloads are bundled.
"""
from __future__ import annotations
import ctypes
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import re
import shutil
import stat
import sys
import tempfile
import zipfile

ORCA_SOURCE='6a7763f08d1a175a464a00ce13f0b5a815662fc4'
CONTRACT_SCHEMA='helix-orca-v1-windows-dependency-contract/v1'
BUNDLE_SCHEMA='helix-orca-v1-windows-dependency-bundle/v1'
RECEIPT_SCHEMA='helix-orca-v1-windows-dependency-receipt/v1'
MANIFEST='dependency-bundle.json'
MAX_FILES=50000
MAX_DIRECTORIES=100000
MAX_RAW_BYTES=4*1024**3
MAX_ZIP_BYTES=3*1024**3
MAX_MANIFEST_BYTES=16*1024**2
CHUNK=1024**2
TOOLS={'cl','link','cmake','ninja','perl','msbuild'}
CONTRACT_KEYS={'schema','source_commit','submodules','dependencies_lock_sha256','builder_sha256',
    'workflow_sha256','module_sha256','toolchain','environment','prefix','downloads'}
PUBLISHER_KEYS={'schema','repository','workflow','application_commit','run_id','run_attempt',
    'runner_image','image_version','toolchain','run_url'}
ROOT_NAMES={'prefix','downloads'}


class BundleError(ValueError):
    """A checkpoint is unavailable, changed, unsafe or not the expected producer."""


def _canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')


def _digest(value):return hashlib.sha256(_canonical(value)).hexdigest()


def _hex(value,length=64):
    if not isinstance(value,str) or re.fullmatch('[a-f0-9]{'+str(length)+'}',value) is None:
        raise BundleError('exact_lowercase_digest_required')
    return value


def _path(value,directory=None):
    path=Path(value)
    if '..' in path.parts or str(path).startswith(('\\','//')):raise BundleError('local_plain_path_required')
    path=path.absolute()
    for part in reversed((path,*path.parents)):
        data=part.lstat()
        if stat.S_ISLNK(data.st_mode) or getattr(data,'st_file_attributes',0)&0x400:
            raise BundleError('symlink_or_reparse_path_refused')
    mode=path.lstat().st_mode
    if directory is True and not stat.S_ISDIR(mode):raise BundleError('directory_required')
    if directory is False and not stat.S_ISREG(mode):raise BundleError('regular_file_required')
    if directory is None and not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
        raise BundleError('nonregular_path_refused')
    return path


def _parent(path):
    path=Path(path).absolute()
    if '..' in Path(path).parts or str(path).startswith(('\\','//')):raise BundleError('plain_destination_required')
    parent=_path(path.parent,True)
    if hasattr(os,'getuid') and parent.stat().st_uid!=os.getuid():
        raise BundleError('caller_owned_parent_required')
    return path


def _fresh(path):
    path=_parent(path)
    if path.exists() or path.is_symlink():raise BundleError('fresh_destination_required')
    return path


def _guard(guard):
    if not callable(guard):raise BundleError('guard_callback_required')
    guard()


def _sha(path,guard,maximum):
    path=_path(path,False)
    before=path.stat()
    if before.st_size>maximum:raise BundleError('file_size_bound_exceeded')
    digest=hashlib.sha256();size=0
    with path.open('rb') as stream:
        while True:
            _guard(guard);chunk=stream.read(CHUNK)
            if not chunk:break
            size+=len(chunk)
            if size>maximum:raise BundleError('file_size_bound_exceeded')
            digest.update(chunk)
    after=_path(path,False).stat()
    if (size!=before.st_size or (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)!=
            (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns)):
        raise BundleError('file_changed_while_reading')
    return dict(size=size,sha256=digest.hexdigest())


def _name(name):
    if not isinstance(name,str) or not 1<=len(name.encode('utf-8'))<=2048 or '\\' in name:
        raise BundleError('unsafe_archive_name')
    parts=name.split('/')
    if parts[0] not in ROOT_NAMES or any(not part or part in ('.','..') for part in parts):
        raise BundleError('archive_path_escape_or_unknown_root')
    for part in parts:
        stem=part.split('.',1)[0].upper()
        if (any(ord(char)<32 or char in '<>:"|?*' for char in part) or part.endswith(('.', ' '))
                or stem in {'CON','PRN','AUX','NUL'} or re.fullmatch('(COM|LPT)[1-9]',stem)):
            raise BundleError('unsafe_windows_archive_name')
    if PurePosixPath(name).as_posix()!=name:raise BundleError('noncanonical_archive_name')
    return name


def _tools(value):
    if not isinstance(value,dict) or set(value)!=TOOLS:raise BundleError('exact_toolchain_required')
    for record in value.values():
        if not isinstance(record,dict) or set(record)!={'size','sha256'} or type(record['size']) is not int or not 0<record['size']<=2*1024**3:
            raise BundleError('exact_tool_record_required')
        _hex(record['sha256'])


def _provenance(contract,publisher,prefix,downloads,guard):
    if not isinstance(contract,dict) or set(contract)!=CONTRACT_KEYS or contract['schema']!=CONTRACT_SCHEMA or contract['source_commit']!=ORCA_SOURCE:
        raise BundleError('exact_dependency_contract_required')
    for key in ('dependencies_lock_sha256','builder_sha256','workflow_sha256','module_sha256'):_hex(contract[key])
    if _sha(Path(__file__),guard,1024**2)['sha256']!=contract['module_sha256']:
        raise BundleError('dependency_module_source_changed')
    modules=contract['submodules']
    if (not isinstance(modules,list) or len(modules)>512
            or any(not isinstance(row,str) or re.fullmatch(r' [0-9a-f]{40} [^\x00\r\n]{1,2048}',row) is None for row in modules)
            or len(set(modules))!=len(modules)):
        raise BundleError('exact_initialized_submodules_required')
    _tools(contract['toolchain'])
    environment=contract['environment']
    if (not isinstance(environment,dict) or not 1<=len(environment)<=128
            or any(not isinstance(key,str) or re.fullmatch('[A-Za-z_][A-Za-z_0-9]{0,127}',key) is None
                   or not isinstance(value,str) or len(value)>32768 or '\0' in value for key,value in environment.items())):
        raise BundleError('explicit_build_environment_required')
    if contract['prefix']!=str(prefix) or contract['downloads']!=str(downloads):
        raise BundleError('fixed_dependency_prefix_or_download_path_changed')
    if not isinstance(publisher,dict) or set(publisher)!=PUBLISHER_KEYS:
        raise BundleError('exact_publisher_required')
    if (publisher['schema']!='helix-orca-v1-windows-builder/v1'
            or publisher['repository']!='bigstupid007/helix-orca-calibration'
            or publisher['workflow']!='.github/workflows/v1-windows-engine.yml'
            or publisher['runner_image']!='windows-2022'
            or not isinstance(publisher['image_version'],str) or not 1<=len(publisher['image_version'])<=128):
        raise BundleError('publisher_identity_mismatch')
    _hex(publisher['application_commit'],40)
    for key in ('run_id','run_attempt'):
        if not isinstance(publisher[key],str) or re.fullmatch('[1-9][0-9]{0,31}',publisher[key]) is None:
            raise BundleError('exact_publisher_run_required')
    if publisher['run_url']!='https://github.com/bigstupid007/helix-orca-calibration/actions/runs/'+publisher['run_id']:
        raise BundleError('publisher_run_url_mismatch')
    _tools(publisher['toolchain'])
    if _canonical(publisher['toolchain'])!=_canonical(contract['toolchain']):raise BundleError('publisher_toolchain_mismatch')
    if prefix==downloads or prefix.is_relative_to(downloads) or downloads.is_relative_to(prefix):
        raise BundleError('distinct_closed_dependency_roots_required')


def validate_provenance(contract,publisher,prefix,downloads,guard):
    """Fail fast on exact recipe/producer pins before dependency commands.

    Root parents must already exist and belong to the caller; the roots may
    be absent before a cold build. No directories or artifacts are created.
    An empty initialized submodule inventory is valid for a source with no
    gitlinks. Bundle creation/restoration repeat these checks independently.
    """
    _guard(guard)
    prefix=_parent(prefix);downloads=_parent(downloads)
    for root in (prefix,downloads):
        if root.exists() or root.is_symlink():_path(root,True)
    _provenance(contract,publisher,prefix,downloads,guard)


def _inventory(roots,guard):
    files={};directories=set();names=set();total=0
    def failed(error):raise error
    for root_name,root in sorted(roots.items()):
        _path(root,True)
        for directory,dirs,leafs in os.walk(root,followlinks=False,onerror=failed):
            _guard(guard)
            current=_path(directory,True)
            rel=current.relative_to(root)
            name=_name(root_name+('/'+rel.as_posix() if rel.parts else ''))
            if name.casefold() in names:raise BundleError('duplicate_casefold_inventory_name')
            names.add(name.casefold());directories.add(name)
            if len(directories)>MAX_DIRECTORIES:raise BundleError('directory_count_bound_exceeded')
            for entry in dirs:_path(current/entry,True)
            for leaf in sorted(leafs):
                _guard(guard)
                path=_path(current/leaf,False)
                name=_name(root_name+'/'+path.relative_to(root).as_posix())
                if name.casefold() in names:raise BundleError('duplicate_casefold_inventory_name')
                names.add(name.casefold())
                record=_sha(path,guard,MAX_RAW_BYTES)
                total+=record['size']
                if len(files)>=MAX_FILES or total>MAX_RAW_BYTES:raise BundleError('dependency_inventory_bound_exceeded')
                files[name]=record
    return dict(files=files,directories=sorted(directories),file_count=len(files),uncompressed_bytes=total)


def _manifest(data,contract,publisher):
    expected={'schema','contract','publisher','files','directories','file_count','uncompressed_bytes','qualified'}
    if not isinstance(data,dict) or set(data)!=expected or data['schema']!=BUNDLE_SCHEMA or data['qualified'] is not False:
        raise BundleError('dependency_manifest_schema_mismatch')
    if _canonical(data['contract'])!=_canonical(contract):raise BundleError('dependency_contract_mismatch')
    if _canonical(data['publisher'])!=_canonical(publisher):raise BundleError('dependency_publisher_mismatch')
    files=data['files'];directories=data['directories']
    if not isinstance(files,dict) or len(files)>MAX_FILES or not isinstance(directories,list) or len(directories)>MAX_DIRECTORIES:
        raise BundleError('dependency_inventory_bound_exceeded')
    names=set();total=0
    for name in directories:
        _name(name)
        if name.casefold() in names:raise BundleError('duplicate_inventory_name')
        names.add(name.casefold())
    if not ROOT_NAMES.issubset(set(directories)):raise BundleError('dependency_root_inventory_missing')
    for name,record in files.items():
        _name(name)
        if name.casefold() in names:raise BundleError('duplicate_inventory_name')
        names.add(name.casefold())
        if not isinstance(record,dict) or set(record)!={'size','sha256'} or type(record['size']) is not int or record['size']<0:
            raise BundleError('invalid_inventory_file_record')
        _hex(record['sha256']);total+=record['size']
        if name.rsplit('/',1)[0] not in directories:raise BundleError('inventory_parent_missing')
    for name in directories:
        if name not in ROOT_NAMES and name.rsplit('/',1)[0] not in directories:raise BundleError('inventory_directory_parent_missing')
    if (type(data['file_count']) is not int or data['file_count']!=len(files)
            or type(data['uncompressed_bytes']) is not int or data['uncompressed_bytes']!=total or total>MAX_RAW_BYTES):
        raise BundleError('inventory_size_or_count_mismatch')
    return data


def _zip_manifest(archive,contract,publisher):
    infos=archive.infolist()
    if len(infos)>MAX_FILES+1:raise BundleError('archive_entry_count_exceeded')
    entries={};total=0
    for info in infos:
        if (info.filename.casefold() in entries or info.is_dir() or info.flag_bits&1
                or info.compress_type not in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED)
                or stat.S_IFMT(info.external_attr>>16) not in (0,stat.S_IFREG)
                or info.external_attr&0x410):
            raise BundleError('unsafe_or_duplicate_zip_entry')
        if info.filename!=MANIFEST:_name(info.filename)
        entries[info.filename.casefold()]=info
        total+=info.file_size
        if total>MAX_RAW_BYTES+MAX_MANIFEST_BYTES:raise BundleError('archive_uncompressed_bound_exceeded')
    if MANIFEST not in entries or entries[MANIFEST].file_size>MAX_MANIFEST_BYTES:raise BundleError('bounded_dependency_manifest_required')
    raw=archive.read(entries[MANIFEST])
    def unique(pairs):
        value={}
        for key,item in pairs:
            if key in value:raise BundleError('duplicate_manifest_key')
            value[key]=item
        return value
    manifest=_manifest(json.loads(raw,object_pairs_hook=unique),contract,publisher)
    if set(entries)!={MANIFEST,*[name.casefold() for name in manifest['files']]}:
        raise BundleError('closed_archive_inventory_mismatch')
    for name,record in manifest['files'].items():
        info=entries[name.casefold()]
        if info.filename!=name or info.file_size!=record['size']:raise BundleError('archive_file_size_or_case_mismatch')
    return manifest,raw


def _rename_fresh(source,destination):
    _fresh(destination)
    if os.name=='nt':
        os.rename(source,destination)  # Windows refuses an existing target.
    elif sys.platform.startswith('linux'):
        libc=ctypes.CDLL(None,use_errno=True)
        rename=getattr(libc,'renameat2',None)
        if rename is None:raise BundleError('atomic_no_replace_unavailable')
        rename.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
        rename.restype=ctypes.c_int
        if rename(-100,os.fsencode(source),-100,os.fsencode(destination),1):
            code=ctypes.get_errno();raise OSError(code,os.strerror(code))
    else:raise BundleError('atomic_no_replace_unavailable')


def _identity(path):
    data=_path(path).stat();return data.st_dev,data.st_ino


def _remove_owned(path,identity):
    try:
        if _identity(path)==identity:
            if path.is_dir():shutil.rmtree(path)
            else:path.unlink()
    except (FileNotFoundError,BundleError):pass  # A replaced path is never ours to delete.


def _receipt(path,record,manifest,raw,restored):
    return dict(schema=RECEIPT_SCHEMA,path=str(path),size=record['size'],sha256=record['sha256'],
        manifest_sha256=hashlib.sha256(raw).hexdigest(),contract_sha256=_digest(manifest['contract']),
        publisher=manifest['publisher'],file_count=manifest['file_count'],
        uncompressed_bytes=manifest['uncompressed_bytes'],restored=restored,qualified=False)


def create_bundle(path,prefix,downloads,contract,publisher,guard):
    """Atomically create a closed dependency ZIP; never overwrite an artifact."""
    contract=json.loads(_canonical(contract));publisher=json.loads(_canonical(publisher))
    _guard(guard);path=_fresh(path);prefix=_path(prefix,True);downloads=_path(downloads,True)
    _provenance(contract,publisher,prefix,downloads,guard)
    roots=dict(prefix=prefix,downloads=downloads)
    if any(path.is_relative_to(root) for root in roots.values()):raise BundleError('archive_must_be_outside_dependency_roots')
    inventory=_inventory(roots,guard)
    manifest=dict(schema=BUNDLE_SCHEMA,contract=contract,publisher=publisher,qualified=False,**inventory)
    raw=_canonical(manifest)
    if len(raw)>MAX_MANIFEST_BYTES:raise BundleError('manifest_size_bound_exceeded')
    fd,temporary=tempfile.mkstemp(prefix='.dependency-bundle-',suffix='.partial',dir=path.parent)
    partial=Path(temporary);os.close(fd);partial_id=_identity(partial);promoted=None
    class Limited:
        def __init__(self,stream):self.stream=stream
        def __getattr__(self,name):return getattr(self.stream,name)
        def write(self,value):
            if self.stream.tell()+len(value)>MAX_ZIP_BYTES:raise BundleError('archive_size_bound_exceeded')
            return self.stream.write(value)
    try:
        with partial.open('w+b') as stream:
            with zipfile.ZipFile(Limited(stream),'w',zipfile.ZIP_DEFLATED,compresslevel=3,allowZip64=True) as archive:
                archive.writestr(MANIFEST,raw)
                for name,expected in sorted(inventory['files'].items()):
                    _guard(guard);root_name,relative=name.split('/',1)
                    source=_path(roots[root_name]/relative,False)
                    digest=hashlib.sha256();count=0
                    info=zipfile.ZipInfo(name);info.compress_type=zipfile.ZIP_DEFLATED
                    info.create_system=3;info.external_attr=(stat.S_IFREG|0o600)<<16
                    with source.open('rb') as original,archive.open(info,'w',force_zip64=True) as output:
                        while True:
                            _guard(guard);chunk=original.read(CHUNK)
                            if not chunk:break
                            count+=len(chunk)
                            if count>expected['size']:raise BundleError('dependency_file_grew_while_archiving')
                            output.write(chunk);digest.update(chunk)
                    if dict(size=count,sha256=digest.hexdigest())!=expected:raise BundleError('dependency_file_changed_while_archiving')
            stream.flush();os.fsync(stream.fileno())
        if _inventory(roots,guard)!=inventory:raise BundleError('closed_source_inventory_changed')
        _provenance(contract,publisher,prefix,downloads,guard)
        with zipfile.ZipFile(partial) as archive:_zip_manifest(archive,contract,publisher)
        record=_sha(partial,guard,MAX_ZIP_BYTES)
        _guard(guard)
        os.link(partial,path)  # Atomic, no replacement; source and target share parent.
        promoted=_identity(path)
        if _sha(path,guard,MAX_ZIP_BYTES)!=record:raise BundleError('promoted_archive_changed')
        return _receipt(path,record,manifest,raw,False)
    except BaseException:
        if promoted is not None:_remove_owned(path,promoted)
        raise
    finally:_remove_owned(partial,partial_id)


def restore_bundle(path,expected_sha256,prefix,downloads,contract,expected_publisher,guard):
    """Restore only an externally pinned bundle into two fresh fixed roots.

    Each directory promotion is atomic/no-replace. Failure rolls back only this
    call's identity-checked new roots; existing destinations are never removed.
    """
    contract=json.loads(_canonical(contract));expected_publisher=json.loads(_canonical(expected_publisher))
    _guard(guard);path=_path(path,False);expected_sha256=_hex(expected_sha256)
    prefix=_fresh(prefix);downloads=_fresh(downloads)
    _provenance(contract,expected_publisher,prefix,downloads,guard)
    if path.is_relative_to(prefix) or path.is_relative_to(downloads):raise BundleError('archive_must_be_outside_dependency_roots')
    containers=[];promoted=[]
    try:
        for root in (prefix,downloads):
            container=Path(tempfile.mkdtemp(prefix='.dependency-restore-',dir=root.parent))
            containers.append((container,_identity(container)))
        captured=containers[0][0]/'verified-bundle.zip'
        digest=hashlib.sha256();size=0
        with path.open('rb') as original,captured.open('xb') as output:
            while True:
                _guard(guard);chunk=original.read(CHUNK)
                if not chunk:break
                size+=len(chunk)
                if size>MAX_ZIP_BYTES:raise BundleError('archive_size_bound_exceeded')
                output.write(chunk);digest.update(chunk)
            output.flush();os.fsync(output.fileno())
        if digest.hexdigest()!=expected_sha256:raise BundleError('external_archive_digest_mismatch')
        record=dict(size=size,sha256=digest.hexdigest())
        roots=dict(prefix=containers[0][0]/'prefix',downloads=containers[1][0]/'downloads')
        with zipfile.ZipFile(captured) as archive:
            manifest,raw=_zip_manifest(archive,contract,expected_publisher)
            for name in sorted(manifest['directories'],key=lambda value:(value.count('/'),value)):
                _guard(guard);root_name,*parts=name.split('/')
                (roots[root_name].joinpath(*parts)).mkdir()
            for name,expected in sorted(manifest['files'].items()):
                _guard(guard);root_name,relative=name.split('/',1);target=roots[root_name]/relative
                digest=hashlib.sha256();count=0
                with archive.open(name) as original,target.open('xb') as output:
                    while True:
                        _guard(guard);chunk=original.read(CHUNK)
                        if not chunk:break
                        count+=len(chunk)
                        if count>expected['size']:raise BundleError('extracted_file_exceeds_inventory')
                        output.write(chunk);digest.update(chunk)
                    output.flush();os.fsync(output.fileno())
                if dict(size=count,sha256=digest.hexdigest())!=expected:raise BundleError('extracted_file_digest_mismatch')
                if _sha(target,guard,MAX_RAW_BYTES)!=expected:raise BundleError('extracted_file_changed')
        expected_inventory={key:manifest[key] for key in ('files','directories','file_count','uncompressed_bytes')}
        if _inventory(roots,guard)!=expected_inventory:raise BundleError('staged_inventory_changed')
        if _sha(captured,guard,MAX_ZIP_BYTES)!=record or _sha(path,guard,MAX_ZIP_BYTES)!=record:
            raise BundleError('archive_changed_before_promotion')
        for key,destination in (('prefix',prefix),('downloads',downloads)):
            _guard(guard);identity=_identity(roots[key]);_rename_fresh(roots[key],destination)
            promoted.append((destination,identity))
        if _inventory(dict(prefix=prefix,downloads=downloads),guard)!=expected_inventory:
            raise BundleError('promoted_dependency_inventory_changed')
        _provenance(contract,expected_publisher,prefix,downloads,guard)
        return _receipt(path,record,manifest,raw,True)
    except BaseException:
        for destination,identity in reversed(promoted):_remove_owned(destination,identity)
        raise
    finally:
        for container,identity in reversed(containers):_remove_owned(container,identity)
