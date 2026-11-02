$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    $env:PYTHONHASHSEED = '0'
    $env:SOURCE_DATE_EPOCH = '1793577600'
    if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
        py -3.12 -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Creating Python 3.12 virtual environment failed.' }
    }
    & '.venv\Scripts\python.exe' -m pip install -r requirements-build.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    & '.venv\Scripts\python.exe' -m unittest discover -p 'test_*.py' -v
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed; build stopped.' }
    & '.venv\Scripts\python.exe' -m PyInstaller --clean --noconfirm --onefile --windowed --name Ostrich2 --specpath build --version-file (Join-Path $PSScriptRoot 'windows-version.txt') ostrich_gui.py
    if ($LASTEXITCODE -ne 0) { throw 'GUI build failed.' }
    & '.venv\Scripts\python.exe' package_release.py
    if ($LASTEXITCODE -ne 0) { throw 'Release packaging failed.' }
    Write-Output 'Release complete: dist\ostrich2-v0.1.0-windows-x64.zip, source ZIP, and SHA256SUMS.'
} finally {
    Pop-Location
}
