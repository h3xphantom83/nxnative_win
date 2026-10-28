param(
    [string] $Python = 'E:\nxnative_clean_test\.venv\Scripts\python.exe',
    [string] $Version = '0.1.0'
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $repo
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) { throw "Python missing: $Python" }
if (-not (Test-Path -LiteralPath (Join-Path $repo 'scripts\build_ipa_windows.py'))) { throw 'Missing nxnative_win build script' }
if (-not (Test-Path -LiteralPath (Join-Path $repo 'nxnative_gui_paths.py'))) { throw 'Missing repository locator module' }
& $Python -m PyInstaller --version
if ($LASTEXITCODE -ne 0) { throw 'Install PyInstaller using this Python environment first.' }
& $Python -m PyInstaller --noconfirm --clean --onedir --windowed `
    --name 'nxnative-gui' `
    --paths $repo `
    --distpath (Join-Path $repo 'dist') `
    --workpath (Join-Path $repo 'build\pyinstaller') `
    --specpath (Join-Path $repo 'build\pyinstaller') `
    (Join-Path $repo 'nxnative_windows_gui.py')
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed.' }
$folder = Join-Path $repo 'dist\nxnative-gui'
$exe = Join-Path $folder 'nxnative-gui.exe'
if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw 'Missing packaged executable.' }
$release = Join-Path $repo 'releases'
New-Item -ItemType Directory -Force -Path $release | Out-Null
$zip = Join-Path $release "nxnative-gui-v$Version-win64.zip"
if (Test-Path -LiteralPath $zip) { Remove-Item -LiteralPath $zip -Force }
Compress-Archive -Path $folder -DestinationPath $zip -CompressionLevel Optimal
if (-not (Test-Path -LiteralPath $zip)) { throw 'ZIP creation failed.' }
Write-Host "EXE: $exe" -ForegroundColor Green
Write-Host "ZIP: $zip" -ForegroundColor Green
Get-FileHash -LiteralPath $zip -Algorithm SHA256 | Format-List
