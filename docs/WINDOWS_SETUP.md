# nxnative_win — Windows Setup Guide

Build unsigned iOS applications from supported Nintendo Switch game files using Windows.

This guide covers the command-line Windows build workflow. A Mac and Xcode
are not required for this tested build path.

## Requirements

- Windows 11 x64 (tested configuration; other Windows versions not yet verified)
- Python 3.12.x required, with the `py` launcher (Python 3.13 is not supported)
- Git for Windows
- .NET SDK 10
- LLVM-MinGW with ARM64 Apple cross-compilation support
- Mach-O-capable `ld64.lld`
- iPhoneOS SDK
- Apple's Metal Developer Tools for Windows
- SPIRV-Cross and zstd where required by the build
- Sufficient free disk space for game extraction, shaders, and build artifacts

The project has been tested with LLVM 23.1.4, .NET SDK 10.0.403,
iPhoneOS SDK 27.0, and the Windows Metal Developer Tools.

The dependency checker identifies missing tools and runs actual compilation
and linking probes.

## 1. Download the project

Open PowerShell:

```powershell
git clone -b windows-dev https://github.com/h3xphantom83/nxnative_win.git
cd nxnative_win
```

## 2. Run the Windows setup assistant

For a first-time installation, start with:

```powershell
py -3.12 scripts/setup_windows.py
```

The setup assistant:

- Validates the required Windows development tools
- Performs real ARM64 compiler and linker checks
- Tests Metal shader compilation
- Displays missing dependencies and suggested fixes
- Returns exit code 0 when all required checks pass

The assistant is diagnostic-only. It does not download, install,
uninstall, or modify any development dependencies.

If a required component is missing, resolve the reported issue and
run the assistant again.

## 3. Check the development environment



```powershell
py -3.12 scripts/check_windows_setup.py
```

For a faster check without compiler probes:

```powershell
py -3.12 scripts/check_windows_setup.py --no-probe
```

For machine-readable diagnostics:

```powershell
py -3.12 scripts/check_windows_setup.py --json
```

All required checks should pass before attempting a game build.

## 4. Install missing components

The existing Windows doctor supports several explicit installation actions.

Download the pinned LLVM-MinGW toolchain:

```powershell
py -3.12 scripts/check_windows_setup.py --fix
```

Import an existing iPhoneOS SDK:

```powershell
py -3.12 scripts/check_windows_setup.py --import-sdk "D:\SDKs\iPhoneOS27.0.sdk"
```

The doctor also supports `--sdk` and `--sdk-xip` for SDK acquisition.
Ensure that your SDK installation and use comply with applicable licenses.

Install Metal Developer Tools for Windows from Apple's official developer
downloads. Other dependencies must be installed or configured according
to the doctor's diagnostics.

After configuration, rerun the full dependency check.

## 5. Build an unsigned IPA

Place the base game and any supported update NSP files into the game's
input directory.

Example:

```powershell
py -u scripts/build_ipa_windows.py `
    "D:\Games\ExampleGame" `
    -k "D:\Keys\prod.keys" `
    --progress lines `
    -o "D:\Output\ExampleGame.ipa"
```

Use game files and keys obtained from hardware you own and are authorized
to use. Do not distribute decrypted game contents, private keys, or SDKs.

The build can reuse previously extracted data and compiled shaders
when its inputs are unchanged.

Depending on the Metal compiler and game profile, the build may require
`--allow-other-metal`. This option permits a compiler outside the tested
shader translation configuration; graphics correctness is not guaranteed.

## 6. Install and provide game data

The output is an unsigned IPA. Sign and install it using a compatible
iOS installation workflow.

For games using ROMFSARC, transfer the generated archive files into
the app's Documents directory using the iPhone Files app:

On My iPhone / [App Name] / romfs /

Typical ROMFSARC contents:

- romfs.idx
- romfs.00
- romfs.01
- Additional numbered shards

The index and shards must remain together. Do not extract these archives
into individual game files.

The Windows fork supports ROMFSARC startup detection and archive-backed
file access.

## 7. Troubleshooting

### Missing compiler or linker

Run:

```powershell
py -3.12 scripts/check_windows_setup.py
```

Review the detected tool paths and error messages. The checker searches
known installation locations as well as configured toolchain directories.

### Metal shader compilation fails

Confirm that Metal Developer Tools are installed and that the Metal probe
passes. The Windows build supports staging Metal files in temporary paths
to work around compiler limitations involving spaces in paths.

### Game files not found

Verify that the app's Documents/romfs directory contains the expected
game data. For ROMFSARC, verify that romfs.idx and its numbered shards
are together inside romfs.

For additional startup diagnostics, inspect Documents/log.txt.

### Application installs but fails to launch

Check IPA signing, device compatibility, the application log, and
runtime diagnostics. Successful compilation does not guarantee every
game is compatible.

## Tested configuration

- Host: Windows x64
- LLVM: 23.1.4
- .NET SDK: 10.0.403
- iPhoneOS SDK: 27.0
- Metal: Apple's Windows Metal Developer Tools
- Game tested: Luigi's Mansion 3, version 1.4.0
- Result: IPA generated on Windows, installed on a physical iPhone,
  and confirmed playable

Other games and developer configurations require separate validation.

## Developer diagnostics

```powershell
py -3.12 scripts/check_windows_setup.py --help
py -3.12 scripts/build_ipa_windows.py --help
py -3.12 scripts/check_windows_backend.py
```
