#!/usr/bin/env bash
# Build the PyInstaller bundle and stage it into the Tauri binaries dir
# under the platform-specific name Tauri's externalBin resolver expects.
#
# Local dev:  pnpm --filter theridion-studio sidecar:bundle
# CI:         called from the desktop matrix job before `tauri build`.
set -euo pipefail

cd "$(dirname "$0")/.."

# Cross-compiling the sidecar isn't on the table for now (PyInstaller
# bundles native binaries from the host), so the target triple has to
# come from rustc's host.
TARGET=$(rustc -vV | grep "^host:" | awk '{print $2}')
if [[ -z "$TARGET" ]]; then
  echo "fatal: could not determine host target triple via rustc" >&2
  exit 1
fi

OUT="../desktop/src-tauri/binaries"
mkdir -p "$OUT"

uv sync --all-extras
uv run pyinstaller sidecar.spec --clean --noconfirm

# PyInstaller emits dist/theridion-sidecar (with .exe on Windows).
SRC="dist/theridion-sidecar"
EXT=""
if [[ "$TARGET" == *windows* ]]; then
  SRC="${SRC}.exe"
  EXT=".exe"
fi

DEST="${OUT}/theridion-sidecar-${TARGET}${EXT}"
cp "$SRC" "$DEST"
chmod +x "$DEST"

echo "✓ staged $(du -h "$DEST" | cut -f1) at $DEST"
