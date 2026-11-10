#!/bin/bash
# Rebuild the PNG icons from templates/icons/app-icon.svg using headless Chrome.
# Only needed after editing the SVG; the PNGs are committed.
set -euo pipefail
cd "$(dirname "$0")/.."
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
SRC="$PWD/templates/icons/app-icon.svg"
tmp=$(mktemp -d)
for spec in "apple-touch-icon.png:180" "icon-192.png:192" "icon-512.png:512" "favicon-32.png:32"; do
  name=${spec%%:*}; size=${spec#*:}
  printf '<html><body style="margin:0"><img src="file://%s" width="%s" height="%s" style="display:block"></body></html>' "$SRC" "$size" "$size" > "$tmp/$name.html"
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
    --window-size="$size,$size" --screenshot="$PWD/templates/icons/$name" "file://$tmp/$name.html" 2>/dev/null
  echo "wrote templates/icons/$name ($size px)"
done
rm -rf "$tmp"
