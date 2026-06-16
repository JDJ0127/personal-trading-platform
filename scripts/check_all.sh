#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/env.sh"

echo "== Backend tests =="
python3 -m unittest discover -s backend/tests

echo "== Frontend build =="
npm run build

echo "== CLI smoke =="
cli --help > /dev/null
cli paper-pipeline --help > /dev/null

echo "All checks passed."
