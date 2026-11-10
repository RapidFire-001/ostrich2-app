# ostrich2-app

A Windows desktop interface and Python command line client for the Moates
Ostrich 2.0 EPROM emulator, derived from
[Martin Strand's ostrich2](https://github.com/mstrand/ostrich2).

GitHub repository:
`Rapidfire-001/ostrich2-app`. New contributions that Rapidfire has rights to
license use the [MIT License](LICENSE). See [NOTICE.md](NOTICE.md) for license
scope, Martin Strand's attribution, and the preserved upstream public-domain
declaration. This is separate from any Moates BURN1 project; it does not
implement BURN1 programming.

## Features

- COM-port selection and device information.
- Read the current I/O bank into a hex viewer; optionally save a BIN snapshot.
- Read a selected address range to a file and write a BIN at a selected address.
- I/O and emulation bank controls.
- Memory map with session transfer records and bank-aware erase updates.
- Erase a range or the whole 512 KiB device using FF fill and readback verification.
- Background transfers, progress display, and error reporting.

The device stores bytes, not a filesystem: tune filenames cannot be recovered
from it. The indicator tracks operations in this app session, not changes from
other software. Erasing removes overlapping loaded records. Existing contents
remain unknown until read. The snapshot viewer displays raw bytes rather than
identifying an ECU calibration or validating its suitability for a vehicle.

## Run from source

Use Windows with Python 3.12 including Tcl/Tk. Install the appropriate FTDI VCP
driver from the [official FTDI site](https://ftdichip.com/drivers/vcp-drivers/).
Drivers and firmware are not included. Close other programs using the COM port.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe ostrich_gui.py
```

Select the actual COM port and click **Check device** or **Read device**. The
latter reads 64 KiB for the current I/O bank 0–7, or all 512 KiB when I/O bank 8
is already selected. It does not switch banks. The hex viewer can save the
snapshot. Reading does not change tune memory.

Range endpoints are inclusive; numbers accept decimal or `0x` hexadecimal.
Writes and erases require complete 256-byte pages. Check the correct bank and
address for your hardware before writing. The app does not automatically place
files based on ECU type. **Apply bank** changes I/O and both current and saved
emulation bank settings. **Erase whole device** asks for confirmation, selects
full-memory I/O mode, fills all 512 KiB with FF, verifies it, and attempts to
restore the original I/O bank. It does not change emulation bank settings.

Back up memory before writing or erasing. Do not perform destructive operations
while the emulator is running an engine. Interrupted operations can leave
partially changed memory; restoration of bank settings requires a working
connection.

## Command line

```powershell
.\.venv\Scripts\python.exe ostrich2.py --help
.\.venv\Scripts\python.exe ostrich2.py --device COM4 version
.\.venv\Scripts\python.exe ostrich2.py --device COM4 read 0x0000 0xffff backup.bin
.\.venv\Scripts\python.exe ostrich2.py --device COM4 write --address 0xc000 tune.bin
```

Replace COM4, filenames, and addresses as appropriate. Filename arguments avoid
binary redirection differences in PowerShell. Serial communication uses
921600 baud, 8-N-1. The serial-number response checksum includes its NS request;
memory response checksums cover the returned payload.

## Tests and Windows builds

```powershell
.\.venv\Scripts\python.exe -m unittest discover -p 'test_*.py' -v
.\build.ps1
```

`build.ps1` creates a virtual environment if needed, installs pinned build
requirements, runs all tests, and builds `dist/Ostrich2.exe` with Rapidfire
creator/version metadata. `package_release.py` verifies embedded application
code against the supplied source and creates Windows/source ZIPs, SHA256SUMS,
and a build manifest. The ZIPs use explicit file allowlists and fixed timestamps.
This is an unsigned release with a repeatable recipe; byte-identical executable
builds across differing toolchains are not claimed. The reference runtime is
Python 3.12.14, Windows x64. Do not commit `dist/`, environments, personal BINs,
backups, credentials, or driver packages. Preserve the bundled licenses and
[third-party notices](THIRD_PARTY_NOTICES.md) when redistributing binaries.

> **Microsoft Edge download notice:** Edge may show a warning or block a download from this repository. If the page or download is unavailable in Edge, you can also open the official GitHub page in Firefox or Chrome. If your browser or antivirus flags a file as malware, please report the exact warning and the file name or release version so I can investigate.

To run a downloaded Windows release, extract its complete ZIP, then double-click
`Ostrich2.exe`. No separate Python installation is required. Source is included
inside the release and as a separate download. See RELEASE-NOTES.txt for the
verification limits. `SHA256SUMS` identifies the supplied files; it is not a
digital signature or proof of publisher identity.

The 21 tests simulate a serial device and exercise GUI flows using Tcl/Tk; they
need a desktop/display. They do not require connected hardware and do not
modify it. Hardware read diagnostics were reported by a user during development;
the complete release has not received an end-to-end physical-device test.

## Known limitations

- Bank-window range validation is still incomplete: in I/O banks 0–7, keep
  addresses within 0x0000–0xFFFF. Use I/O bank 8 for the full address space.
- Normal BIN writes rely on device acknowledgements and do not automatically
  read back the complete file. Erase operations do verify readback.
- Memory records are session-local, and remain operation records rather than
  an authoritative directory of tunes. A device reset on the same port is not
  automatically detected.
- GUI tests use simulated devices and do not replace hardware validation.

## Contributing

Keep changes focused and run the existing tests. Do not submit proprietary tune
files, firmware dumps, credentials, or vendor driver packages. New contributions
should be submitted under MIT while preserving third-party attribution and the
license scope in NOTICE.md. Do not contribute material you lack rights to share.
