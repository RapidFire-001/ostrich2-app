"""Build a source allowlist package and validate a Windows app before release.

Copyright (c) 2026 Rapidfire. MIT; see LICENSE and NOTICE.md.
"""
import argparse
import hashlib
import importlib.metadata
import json
import marshal
import platform
from pathlib import Path
from types import CodeType
import zipfile

from PyInstaller.archive.readers import CArchiveReader
import pefile

VERSION = '0.1.0'
SOURCE_FILES = (
    '.gitignore', 'LICENSE', 'NOTICE.md', 'README.md', 'build.ps1',
    'ostrich2.py', 'ostrich_gui.py', 'ostrich2/__init__.py',
    'provenance/upstream-README.md', 'provenance/upstream-setup.py.txt',
    'pyproject.toml', 'requirements-build.txt', 'requirements.txt', 'setup.py',
    'test_gui.py', 'test_protocol.py', 'windows-version.txt',
    'THIRD_PARTY_NOTICES.md', 'RELEASE-NOTES.txt', 'package_release.py',
    'licenses/Python.txt', 'licenses/Tk.txt', 'licenses/PyInstaller.txt',
    'licenses/pyserial.txt', 'licenses/OpenSSL.txt', 'licenses/libffi.txt',
    'licenses/zlib.txt', 'licenses/liblzma.txt',
)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def normalize(code):
    return code.replace(co_filename='<source>', co_consts=tuple(
        normalize(c) if isinstance(c, CodeType) else c for c in code.co_consts))

def write_zip(path, files):
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 2, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    with zipfile.ZipFile(path) as archive:
        if set(archive.namelist()) != set(files):
            raise RuntimeError('Archive allowlist mismatch')
        if archive.testzip() is not None:
            raise RuntimeError('Archive CRC validation failed')

def main():
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, default=root/'dist/Ostrich2.exe')
    parser.add_argument('--output', type=Path, default=root/'dist')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    source = {name: (root/name).read_bytes() for name in SOURCE_FILES}
    exe_data = args.exe.read_bytes()
    archive = CArchiveReader(str(args.exe))
    built = {
        'ostrich_gui.py': marshal.loads(archive.extract('ostrich_gui')),
        'ostrich2/__init__.py': archive.open_embedded_archive('PYZ.pyz').extract('ostrich2'),
    }
    correspondence = {}
    for name, code in built.items():
        correspondence[name] = normalize(code) == normalize(compile(source[name], '<source>', 'exec'))
    if not all(correspondence.values()):
        raise RuntimeError('Executable does not match supplied application source')
    pe = pefile.PE(data=exe_data)
    version_strings = {}
    for group in pe.FileInfo:
        for item in group:
            if hasattr(item, 'StringTable'):
                for table in item.StringTable:
                    version_strings.update({k.decode(): v.decode() for k,v in table.entries.items()})
    if version_strings.get('CompanyName') != 'Rapidfire' or version_strings.get('ProductVersion') != VERSION:
        raise RuntimeError('Executable creator/version metadata mismatch')
    if pe.FILE_HEADER.Machine != 0x8664:
        raise RuntimeError('Executable is not Windows x64')
    source_name = f'ostrich2-v{VERSION}-source.zip'
    source_path = args.output/source_name
    write_zip(source_path, {'ostrich2-app/'+name: data for name,data in source.items()})
    manifest = {
        'version': VERSION, 'creator': 'Rapidfire', 'github_owner': 'Rapidfire-001',
        'source_upstream': 'mstrand/ostrich2@6e8e00730644bc4d77695d8ad3ccf692c044948c',
        'python': platform.python_version(), 'architecture': platform.machine(),
        'dependencies': {name: importlib.metadata.version(name) for name in (
            'pyserial', 'pyinstaller', 'setuptools', 'altgraph', 'packaging',
            'pefile', 'pyinstaller-hooks-contrib', 'pywin32-ctypes')},
        'embedded_application_code_matches_source': correspondence,
        'windows_metadata': version_strings,
        'executable_sha256': sha(exe_data),
        'source_archive_sha256': sha(source_path.read_bytes()),
        'source_manifest': {name: sha(data) for name,data in source.items()},
        'excluded_user_data': 'No tunes, firmware, ROMs, BINs, settings, logs or backups; explicit source allowlist only',
        'hardware_verification': 'No end-to-end physical-device certification; see RELEASE-NOTES.txt',
        'reproducibility': 'Pinned recipe and deterministic archive timestamps; cross-toolchain byte-identical EXEs not claimed',
    }
    release_files = {name: data for name,data in source.items() if name.startswith(('licenses/', 'provenance/')) or name in ('LICENSE','NOTICE.md','THIRD_PARTY_NOTICES.md','README.md','RELEASE-NOTES.txt')}
    release_files['Ostrich2.exe'] = exe_data
    release_files['source/'+source_name] = source_path.read_bytes()
    release_files['BUILD-MANIFEST.json'] = (json.dumps(manifest, indent=2, sort_keys=True)+'\n').encode()
    inner_checksums = ''.join(f'{sha(data)}  {name}\n' for name,data in sorted(release_files.items()))
    release_files['SHA256SUMS.txt'] = inner_checksums.encode()
    release_path = args.output/f'ostrich2-v{VERSION}-windows-x64.zip'
    write_zip(release_path, release_files)
    checksum_path = args.output/f'ostrich2-v{VERSION}-SHA256SUMS.txt'
    checksum_path.write_text(''.join(f'{sha(p.read_bytes())}  {p.name}\n' for p in (release_path, source_path)), encoding='utf-8')
    (args.output/f'ostrich2-v{VERSION}-BUILD-MANIFEST.json').write_text(json.dumps(manifest, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    print(json.dumps({'release': str(release_path), 'source': str(source_path), 'checksums': str(checksum_path), 'source_files': len(source), 'embedded_code_matches': correspondence, 'creator': version_strings['CompanyName']}, indent=2))

if __name__ == '__main__':
    main()
