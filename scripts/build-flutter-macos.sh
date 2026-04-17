#!/usr/bin/env zsh
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd)
PROJECT_DIR="$REPO_ROOT/flutter_app"
DIST_DIR="$REPO_ROOT/dist"
APP_BUNDLE_NAME="exif_editor_flutter.app"
APP_SOURCE="$PROJECT_DIR/build/macos/Build/Products/Release/$APP_BUNDLE_NAME"
APP_TARGET="$DIST_DIR/$APP_BUNDLE_NAME"
ZIP_TARGET="$DIST_DIR/exif_editor_flutter-macos.zip"

if ! xcodebuild -version >/dev/null 2>&1; then
  echo "Full Xcode is required for macOS release build."
  echo "Install Xcode first, then run:"
  echo "  sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer"
  echo "  sudo xcodebuild -runFirstLaunch"
  exit 1
fi

cd "$PROJECT_DIR"
flutter build macos --release "$@"

mkdir -p "$DIST_DIR"
rm -rf "$APP_TARGET"
cp -R "$APP_SOURCE" "$APP_TARGET"

rm -f "$ZIP_TARGET"
ditto -c -k --sequesterRsrc --keepParent "$APP_TARGET" "$ZIP_TARGET"

echo "Build complete:"
echo "  App: $APP_TARGET"
echo "  Zip: $ZIP_TARGET"
