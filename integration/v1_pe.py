"""Bounded PE32+ AMD64 import inspection; no execution or system DLL discovery."""
from pathlib import Path
import re
import struct

DLL_NAME = re.compile(r'[a-z0-9][a-z0-9_.-]{0,120}\.dll\Z')
SYSTEM_DLLS = frozenset(('advapi32 bcrypt cabinet cfgmgr32 comctl32 comdlg32 crypt32 cryptbase '
    'dbghelp dnsapi dwmapi gdi32 imm32 iphlpapi kernel32 kernelbase mpr msvcrt ncrypt netapi32 '
    'normaliz ntdll msasn1 mswsock wldap32 wintrust imagehlp shcore kernel.appcore dpapi ole32 oleaut32 powrprof propsys psapi rpcrt4 secur32 setupapi shell32 shlwapi '
    'sspicli ucrtbase user32 userenv usp10 version winhttp wininet winmm winspool ws2_32 wsock32 wtsapi32').split())


def system_dll(name):
    name = name.lower()
    return bool(DLL_NAME.fullmatch(name) and (name[:-4] in SYSTEM_DLLS or
                name.startswith(('api-ms-win-', 'ext-ms-win-'))))


def inspect(path, *, dll=False):
    """Reject wrong architectures/truncation and inventory normal/delay imports."""
    path = Path(path)
    if path.is_symlink() or not path.is_file() or not 256 <= path.stat().st_size <= 2 * 1024**3:
        raise ValueError('Bounded regular PE file required')
    size = path.stat().st_size
    with path.open('rb') as stream:
        def read(offset, count):
            if offset < 0 or count < 0 or offset + count > size:
                raise ValueError('PE data exceeds file')
            stream.seek(offset)
            value = stream.read(count)
            if len(value) != count:
                raise ValueError('Truncated PE data')
            return value
        dos = read(0, 64)
        pe = struct.unpack_from('<I', dos, 60)[0]
        if dos[:2] != b'MZ' or not 64 <= pe <= 1024**2:
            raise ValueError('PE DOS header differs')
        coff = read(pe, 24)
        machine, sections = struct.unpack_from('<HH', coff, 4)
        optional_size, characteristics = struct.unpack_from('<HH', coff, 20)
        if (coff[:4] != b'PE\0\0' or machine != 0x8664 or not characteristics & 2 or not 1 <= sections <= 96
                or not 240 <= optional_size <= 4096 or bool(characteristics & 0x2000) != dll):
            raise ValueError('PE AMD64 executable/DLL header differs')
        optional = read(pe + 24, optional_size)
        if struct.unpack_from('<H', optional)[0] != 0x20b or struct.unpack_from('<I', optional, 108)[0] < 14:
            raise ValueError('PE32+ import directory unavailable')
        headers_size = struct.unpack_from('<I', optional, 60)[0]
        mapping = []
        for index in range(sections):
            section = read(pe + 24 + optional_size + index * 40, 40)
            virtual_size, address, raw_size, offset = struct.unpack_from('<IIII', section, 8)
            mapping.append((address, max(virtual_size, raw_size), raw_size, offset))
        def rva(value, count):
            if value < headers_size and value + count <= headers_size:
                return value
            for address, extent, raw_size, offset in mapping:
                if address <= value < address + extent and value + count <= address + raw_size:
                    return offset + value - address
            raise ValueError('PE import RVA is not file backed')
        imports = set()
        for directory, stride, name_offset in ((1, 20, 12), (13, 32, 4)):
            address, count = struct.unpack_from('<II', optional, 112 + directory * 8)
            if not address and not count:
                continue
            if not address or not stride <= count <= 1024 * stride:
                raise ValueError('PE import directory outside bounds')
            terminated = False
            for index in range(count // stride):
                descriptor = read(rva(address + index * stride, stride), stride)
                if not any(descriptor):
                    terminated = True
                    break
                if directory == 13 and struct.unpack_from('<I', descriptor)[0] != 1:
                    raise ValueError('Only RVA-based PE delay imports are supported')
                name_rva = struct.unpack_from('<I', descriptor, name_offset)[0]
                name = bytearray()
                for offset in range(128):
                    char = read(rva(name_rva + offset, 1), 1)
                    if char == b'\0':
                        break
                    name.extend(char)
                else:
                    raise ValueError('PE DLL name exceeds bound')
                decoded = name.decode('ascii').lower()
                if not DLL_NAME.fullmatch(decoded):
                    raise ValueError('PE DLL name is unsafe')
                imports.add(decoded)
            if not terminated:
                raise ValueError('PE import directory is not terminated')
    return sorted(imports)
