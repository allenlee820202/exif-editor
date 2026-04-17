#!/usr/bin/env zsh
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd)
PROJECT_DIR="$REPO_ROOT/flutter_app"
DIST_DIR="$REPO_ROOT/dist/web"

cd "$PROJECT_DIR"
flutter build web --release "$@"

rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"
cp -R "$PROJECT_DIR/build/web"/* "$DIST_DIR"/

echo "Build complete:"
echo "  Web bundle: $DIST_DIR"
