#!/usr/bin/env bash
set -euo pipefail

echo "Starting province-economy analysis engine..." >&2
exec python main.py "$@"