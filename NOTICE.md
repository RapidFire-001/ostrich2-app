# Attribution and license scope

This project derives from Martin Strand's **ostrich2**,
https://github.com/mstrand/ostrich2, commit
`6e8e00730644bc4d77695d8ad3ccf692c044948c` (2012-06-13).
The original author's name, original README, and original packaging declaration
are preserved under `provenance/`. The upstream `setup.py` states
`license='Public domain'`. The inspected upstream commit has no separate LICENSE
or COPYING file. That declaration is reported as found, without substituting a
different license or asserting that it is a complete legal dedication.

The new contributions that Rapidfire has rights to license are provided
under the MIT License in `LICENSE`, copyright (c) 2026 Rapidfire. These
include the GUI, protocol corrections, memory viewer, erase controls, tests,
and new documentation/build preparation. Preserve the MIT copyright and
permission notice when copying or redistributing these contributions.

This MIT grant does not claim authorship of Martin Strand's original work,
replace his original public-domain declaration, or license any third-party work
on its owner's behalf. The original upstream README and setup declaration in
`provenance/` retain their upstream provenance. Modified source files combine
that upstream work with the new contributions described here.

The Moates protocol spreadsheet shipped in the upstream repository is omitted
from this snapshot. Its redistribution terms were not established. Personal
calibration/tune binaries, backups, FTDI driver installers, dependency bundles,
and generated executables are also omitted.

Python, Tcl/Tk, pyserial, PyInstaller and their build/runtime dependencies are
separate third-party works. Runtime license texts and notices for the Windows
release are bundled in `licenses/` and THIRD_PARTY_NOTICES.md. In particular,
preserve
PyInstaller's bootloader exception and the licenses of Python, Tcl/Tk, and
pyserial before distributing a binary release. The build tool's own license is
not assigned to this application's source.

Moates, Ostrich, and FTDI names identify compatible hardware. No affiliation or
endorsement is claimed.
