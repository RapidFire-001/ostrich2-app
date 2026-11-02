# Windows release dependency notices

Creator of the new application contributions: Rapidfire. GitHub owner:
Rapidfire-001. Martin Strand's original work and public-domain declaration are
described in NOTICE.md and preserved under provenance/. MIT does not replace
third-party terms.

The source-only release does not include dependency source code or binaries.
The Windows executable embeds the following runtime components. Preserve this
document and the licenses/ directory when redistributing the Windows package.

| Component | Notice included |
| --- | --- |
| Python 3.12.14 and its standard library | licenses/Python.txt (PSF and historical terms, Windows redistribution conditions, bzip2 and Tcl/Tk notices) |
| Tcl/Tk 8.6 | licenses/Python.txt and licenses/Tk.txt |
| pyserial 3.5, Chris Liechti | licenses/pyserial.txt (BSD-3-Clause) |
| PyInstaller 6.22.3 bootloader and runtime hooks | licenses/PyInstaller.txt (GPL with bootloader exception; Apache-2.0 runtime-hook terms included) |
| OpenSSL 3.5.8 libcrypto | licenses/OpenSSL.txt (Apache-2.0) |
| libffi | licenses/libffi.txt (MIT-style license) |
| zlib 1.3.2 | licenses/zlib.txt |
| XZ Utils liblzma | licenses/liblzma.txt (upstream liblzma public-domain statement) |
| Microsoft Visual C/C++ and Windows runtime DLLs | Windows redistribution conditions in licenses/Python.txt |

The installed Python runtime's LICENSE.txt and Tk license.terms were copied
verbatim. PyInstaller's COPYING.txt was copied from its installed distribution.
The other texts were retrieved from upstream release source locations:

- https://github.com/pyserial/pyserial/blob/v3.5/LICENSE.txt
- https://github.com/openssl/openssl/blob/openssl-3.5.8/LICENSE.txt
- https://github.com/libffi/libffi/blob/v3.4.4/LICENSE
- https://github.com/madler/zlib/blob/v1.3.2/zlib.h (opening license comment)
- https://github.com/tukaani-project/xz/blob/v5.2.5/COPYING

These notices do not imply endorsement by any third-party author. Dependency
versions may change in future builds; rebuilders must review the notices when
changing the Python runtime or dependency versions. The bundled Python runtime
provides some libraries statically, so the table is a notice inventory rather
than a promise that each component is a separate DLL.
