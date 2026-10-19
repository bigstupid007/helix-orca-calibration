"""Read-only local owner-private regular-file validation for deployment records.

No policy or ACL is changed. Windows checks use current process token and the
file's security descriptor directly; no shell, PowerShell, credential or network
operation is used. The caller still validates bounded contents and their hashes.
"""
from pathlib import Path
import os
import re
import stat

from integration.v1_contract import ContractError


def _denied(message):
    raise ContractError("Local private file refused: " + message)


def _windows_acl(path):
    import ctypes
    from ctypes import wintypes

    pointer = ctypes.c_void_p
    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    advapi.GetNamedSecurityInfoW.argtypes = [wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD,
        ctypes.POINTER(pointer), ctypes.POINTER(pointer), ctypes.POINTER(pointer), ctypes.POINTER(pointer), ctypes.POINTER(pointer)]
    advapi.GetNamedSecurityInfoW.restype = wintypes.DWORD
    advapi.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    advapi.OpenProcessToken.restype = wintypes.BOOL
    advapi.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, pointer, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    advapi.GetTokenInformation.restype = wintypes.BOOL
    advapi.EqualSid.argtypes = [pointer, pointer]; advapi.EqualSid.restype = wintypes.BOOL
    advapi.IsValidSid.argtypes = [pointer]; advapi.IsValidSid.restype = wintypes.BOOL
    advapi.GetLengthSid.argtypes = [pointer]; advapi.GetLengthSid.restype = wintypes.DWORD
    advapi.GetAclInformation.argtypes = [pointer, pointer, wintypes.DWORD, ctypes.c_int]
    advapi.GetAclInformation.restype = wintypes.BOOL
    advapi.GetAce.argtypes = [pointer, wintypes.DWORD, ctypes.POINTER(pointer)]
    advapi.GetAce.restype = wintypes.BOOL
    kernel.GetCurrentProcess.argtypes = []; kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]; kernel.CloseHandle.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [pointer]; kernel.LocalFree.restype = pointer

    class SidAndAttributes(ctypes.Structure):
        _fields_ = [("sid", pointer), ("attributes", wintypes.DWORD)]
    class AclSize(ctypes.Structure):
        _fields_ = [("count", wintypes.DWORD), ("used", wintypes.DWORD), ("free", wintypes.DWORD)]
    class AceHeader(ctypes.Structure):
        _fields_ = [("kind", wintypes.BYTE), ("flags", wintypes.BYTE), ("size", wintypes.WORD)]

    token = wintypes.HANDLE()
    descriptor, owner, dacl = pointer(), pointer(), pointer()
    try:
        if not advapi.OpenProcessToken(kernel.GetCurrentProcess(), 0x0008, ctypes.byref(token)):
            _denied("current process identity unavailable")
        length = wintypes.DWORD()
        advapi.GetTokenInformation(token, 1, None, 0, ctypes.byref(length))  # TokenUser
        if not 0 < length.value <= 65536:
            _denied("current process token outside bound")
        buffer = ctypes.create_string_buffer(length.value)
        if not advapi.GetTokenInformation(token, 1, buffer, length.value, ctypes.byref(length)):
            _denied("current process identity unavailable")
        user = ctypes.cast(buffer, ctypes.POINTER(SidAndAttributes)).contents.sid
        if not user or not advapi.IsValidSid(user):
            _denied("current process SID unavailable")
        result = advapi.GetNamedSecurityInfoW(str(path), 1, 0x00000005,
            ctypes.byref(owner), None, ctypes.byref(dacl), None, ctypes.byref(descriptor))
        if result != 0 or not owner or not advapi.IsValidSid(owner) or not advapi.EqualSid(owner, user):
            _denied("file owner is not the current user")
        if not dacl:
            _denied("null DACL grants unrestricted access")
        size = AclSize()
        if not advapi.GetAclInformation(dacl, ctypes.byref(size), ctypes.sizeof(size), 2):  # AclSizeInformation
            _denied("DACL cannot be inspected")
        if size.used < 8 or size.used > 65535 or size.count > 8192:
            _denied("DACL outside structural bound")
        for index in range(size.count):
            ace = pointer()
            if not advapi.GetAce(dacl, index, ctypes.byref(ace)) or not ace:
                _denied("DACL entry cannot be inspected")
            address = ace.value
            if address < dacl.value + 8 or address + ctypes.sizeof(AceHeader) > dacl.value + size.used:
                _denied("DACL entry outside descriptor")
            header = ctypes.cast(ace, ctypes.POINTER(AceHeader)).contents
            if header.size < 16 or address + header.size > dacl.value + size.used:
                _denied("DACL entry outside structural bound")
            # Standard ACCESS_ALLOWED_ACE / ACCESS_DENIED_ACE only. Object,
            # callback, conditional or otherwise complex ACEs fail closed.
            if header.kind not in (0, 1):
                _denied("unsupported complex DACL entry")
            sid = pointer(address + 8)  # ACE_HEADER (4) + ACCESS_MASK (4)
            if not advapi.IsValidSid(sid) or advapi.GetLengthSid(sid) > header.size - 8:
                _denied("invalid DACL identity")
            if header.kind == 0 and not advapi.EqualSid(sid, user):
                _denied("DACL grants access to another principal")
    finally:
        if descriptor:
            kernel.LocalFree(descriptor)
        if token:
            kernel.CloseHandle(token)


def private_file(path) -> Path:
    """Return an existing ordinary absolute current-user-only regular Path.

    Every existing ancestor is checked without following links; Windows reparse
    points, UNC/device paths and alternate streams are unsupported. This returns
    a Path, not a locked handle; callers must retain the private runtime directory
    and independently bind the bounded contents to the reviewed source/config.
    """
    if not isinstance(path, (str, os.PathLike)):
        _denied("explicit absolute path required")
    value = os.fspath(path)
    if not isinstance(value, str) or not value or any(ord(c) < 32 for c in value):
        _denied("ordinary local path required")
    candidate = Path(value)
    if not candidate.is_absolute() or ".." in candidate.parts:
        _denied("explicit ordinary absolute path required")
    if os.name == "nt":
        if re.fullmatch(r"[A-Za-z]:\\.*", value) is None:
            _denied("network/device paths unsupported")
        if any(part.endswith((".", " ")) or any(c in part for c in ':<>|?*"') for part in candidate.parts[1:]):
            _denied("alternate streams or ambiguous Windows path unsupported")
    try:
        observed = None
        for item in (candidate, *candidate.parents):
            sample = item.lstat()
            if stat.S_ISLNK(sample.st_mode) or getattr(sample, "st_file_attributes", 0) & 0x0400:
                _denied("linked/reparse path or ancestor")
            if item == candidate:
                observed = sample
            elif not stat.S_ISDIR(sample.st_mode):
                _denied("non-directory ancestor")
        if observed is None or not stat.S_ISREG(observed.st_mode):
            _denied("regular existing file required")
        if os.name == "nt":
            _windows_acl(candidate)
        elif observed.st_uid != os.getuid() or stat.S_IMODE(observed.st_mode) & 0o077:
            _denied("file owner/mode is not current-user-only")
        after = candidate.lstat()
        if (after.st_dev, after.st_ino, after.st_mode, after.st_size, after.st_mtime_ns) != (observed.st_dev, observed.st_ino, observed.st_mode, observed.st_size, observed.st_mtime_ns):
            _denied("file changed during identity inspection")
    except OSError as exc:
        raise ContractError("Local private file inspection unavailable") from exc
    return candidate
