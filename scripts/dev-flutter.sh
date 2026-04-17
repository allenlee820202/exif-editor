#!/usr/bin/env zsh
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd)
BACKEND_HOST=${BACKEND_HOST:-127.0.0.1}
BACKEND_PORT=${BACKEND_PORT:-8765}

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT INT TERM

cd "$REPO_ROOT"

if ! command -v flutter >/dev/null 2>&1; then
  echo "flutter command not found. Install Flutter SDK first."
  exit 1
fi

if ! xcodebuild -version >/dev/null 2>&1; then
  echo "Full Xcode is required to run macOS Flutter app."
  echo "Install Xcode, then run:"
  echo "  sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer"
  echo "  sudo xcodebuild -runFirstLaunch"
  exit 1
fi

echo "Starting Python backend on ${BACKEND_HOST}:${BACKEND_PORT}..."
uv run python "$REPO_ROOT/flutter_backend.py" --host "$BACKEND_HOST" --port "$BACKEND_PORT" &
BACKEND_PID=$!

for _ in {1..40}; do
  if curl --silent --fail "http://${BACKEND_HOST}:${BACKEND_PORT}/health" >/dev/null; then
    break
  fi
  sleep 0.25
done

if ! curl --silent --fail "http://${BACKEND_HOST}:${BACKEND_PORT}/health" >/dev/null; then
  echo "Backend failed to start."
  exit 1
fi

echo "Launching Flutter desktop app..."
cd "$REPO_ROOT/flutter_app"
flutter run -d macos --dart-define=BACKEND_BASE_URL="http://${BACKEND_HOST}:${BACKEND_PORT}" "$@"
