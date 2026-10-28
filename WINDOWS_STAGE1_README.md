# nxnative_win — Stage 1: Windows backend integration

This package is adapted from the **user-supplied working NX2Apple source export**, with its
`frontend-qt/nspb_qt/win` relative directory layout preserved. It does not contain games,
keys, SDKs, downloaded tools, compiled translator DLLs, or an entire nxnative checkout.

## Install into a separate fork checkout

Copy the contents of this archive into the **root of your separate nxnative_win checkout**, not
`E:\Nintendo Switch\NX2Apple`. Do not overwrite the working NX2Apple installation.

Files added:
- `frontend-qt/nspb_qt/win/` — source of Windows backend, including iOS launcher code
- `frontend-qt/nspb_qt/__init__.py` — package initializer
- `scripts/build_ipa_windows.py` — direct command-line entry point
- `scripts/check_windows_backend.py` — safe structural/AST check

## First checks (PowerShell, from your fork)

```powershell
py scripts/check_windows_backend.py
py scripts/build_ipa_windows.py --help
```

The second command can initialize the Python shim and may fail if upstream interfaces have
changed. Review its output before an actual IPA build.

## Then use your existing installed tools

```powershell
py scripts/build_ipa_windows.py "E:\Nintendo Switch\LuigisMansion" `
  -k "E:\Nintendo Switch\prod.keys" `
  -o "E:\NXBuild\Luigi3-test.ipa"
```

This is a **first integration**, not a validated finished port. Hardware/SDK/toolchain discovery,
shader-chain version lock consistency, and upstream compatibility require testing on the user's
Windows machine. In particular, this source export omits the Windows-built shader translator
DLLs and their lock-compatible binaries. Do not copy generated lock files or binary versions
without independently verifying their fingerprints.

Current scope does not include ROMFS/NSO/shader-splitting patches from the other uploads; those
should be applied in focused follow-up changes once the backend import and `--help` tests work.

Do not commit `prod.keys`, game assets, proprietary SDKs, compiled third-party binaries, or
local `.tools` directories.
