#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:-0.2.0}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python scripts/build_desktop.py

APP="$ROOT/dist/COSMOS-Media.app"
CLI="$ROOT/dist/cosmos-media"
DMG="$ROOT/dist/COSMOS-Media-macOS.dmg"
STAGE="$ROOT/dist/dmg-stage"

if [[ ! -d "$APP" ]]; then
  echo "Expected macOS app bundle missing: $APP" >&2
  exit 2
fi
if [[ ! -f "$CLI" ]]; then
  echo "Expected CLI binary missing: $CLI" >&2
  exit 2
fi

codesign --force --deep --sign - "$APP"
rm -rf "$STAGE"
mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/COSMOS-Media.app"
cp "$CLI" "$STAGE/cosmos-media"
ln -s /Applications "$STAGE/Applications"
cat > "$STAGE/README.txt" <<EOF
COSMOS Media ${VERSION}

Drag COSMOS-Media.app to Applications, then open it.
The bundled cosmos-media binary is the CLI/integration bridge.

This public build is ad-hoc signed. A notarized Developer ID build requires
Apple signing/notarization credentials supplied by the release owner.
EOF

rm -f "$DMG"
hdiutil create \
  -volname "COSMOS Media ${VERSION}" \
  -srcfolder "$STAGE" \
  -ov \
  -format UDZO \
  "$DMG"

(cd "$ROOT/dist" && ditto -c -k --sequesterRsrc --keepParent "COSMOS-Media.app" "COSMOS-Media-macOS.app.zip")

echo "macOS app: $APP"
echo "macOS DMG: $DMG"
