#!/usr/bin/env bash
# SocialHub — one-command local dev startup
# Usage: ./scripts/dev_up.sh

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "$ROOT/scripts/dev_up.py" "$@"
