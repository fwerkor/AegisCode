#!/usr/bin/env sh
set -eu

OS=$(uname -s | tr '[:upper:]' '[:lower:]')
case "$OS" in
  linux) OS="linux" ;;
  darwin) OS="macos" ;;
  *) echo "unsupported OS for standalone binary: $OS" >&2; exit 1 ;;
esac

ARCH=$(uname -m)
case "$ARCH" in
  x86_64|amd64) ARCH="x86_64" ;;
  *) echo "standalone binary is not published for arch: $ARCH" >&2; echo "Use: pipx install git+https://github.com/fwerkor/AegisCode.git" >&2; exit 1 ;;
esac

VERSION=${AEGISCODE_VERSION:-latest}
BASE="https://github.com/fwerkor/AegisCode/releases"
if [ "$VERSION" = "latest" ]; then
  URL="$BASE/latest/download/aegiscode-$OS-$ARCH"
else
  URL="$BASE/download/$VERSION/aegiscode-$OS-$ARCH"
fi

DEST=${AEGISCODE_INSTALL_DIR:-"$HOME/.local/bin"}
mkdir -p "$DEST"
TMP=$(mktemp)
trap 'rm -f "$TMP"' EXIT
curl -fsSL "$URL" -o "$TMP"
chmod +x "$TMP"
mv "$TMP" "$DEST/aegiscode"
echo "installed aegiscode to $DEST/aegiscode"
