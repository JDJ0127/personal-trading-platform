#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

NODE_BIN="${NODE_BIN:-$ROOT_DIR/.tools/node-v24.14.0-darwin-arm64/bin}"
if [[ -d "$NODE_BIN" ]]; then
  export PATH="$NODE_BIN:$PATH"
fi

if [[ -z "${CLOUDBASE_ENV_ID:-}" ]]; then
  cat >&2 <<'EOF'
Missing CLOUDBASE_ENV_ID.

Usage:
  CLOUDBASE_ENV_ID=<your-env-id> npm run deploy:cloudbase

Create or copy the environment ID from Tencent CloudBase console first.
EOF
  exit 2
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required. Make sure Node.js is installed or NODE_BIN points to a Node.js bin directory." >&2
  exit 2
fi

npm run build
npx --yes --package @cloudbase/cli@latest tcb hosting deploy dist -e "$CLOUDBASE_ENV_ID"
