#!/usr/bin/env bash
# run_weekly.sh - one command to refresh the Kansas crop rotation advice.
# Written by Claude (Anthropic AI) for Varun Pisharody's Space Apps 2026 team.
# Run in WSL Ubuntu from the project folder:   bash scripts/run_weekly.sh
# Extra options are passed through, e.g.:      bash scripts/run_weekly.sh --no-load
#
# Security: every library (including the ones they depend on) is installed from requirements.lock,
# which pins exact versions AND their SHA-256 fingerprints. If any downloaded package doesn't match
# its fingerprint, the install stops and nothing runs. The environment lives in .venv-weekly/
# (gitignored) and is synced to exactly the lock file on every run.
set -euo pipefail
cd "$(dirname "$0")/.."
VENV=.venv-weekly
[ -x "$VENV/bin/python" ] || uv venv -q --python 3.12 "$VENV"
VIRTUAL_ENV="$VENV" uv pip sync -q --require-hashes requirements.lock
"$VENV/bin/python" scripts/run_weekly.py "$@"
