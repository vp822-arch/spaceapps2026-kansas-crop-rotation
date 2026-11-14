#!/usr/bin/env bash
# run_weekly.sh - one command to refresh the Kansas crop rotation advice.
# Written by Claude (Anthropic AI) for Varun Pisharody's Space Apps 2026 team.
# Run in WSL Ubuntu from the project folder:   bash scripts/run_weekly.sh
# Extra options are passed through, e.g.:      bash scripts/run_weekly.sh --no-load
# uv sets up Python 3.12 and the exact library versions the analysis was built and checked with.
set -euo pipefail
cd "$(dirname "$0")/.."
uv run --no-project --python 3.12 \
  --with pandas==2.3.3 --with numpy==2.2.6 --with scikit-learn==1.7.2 \
  --with scipy==1.15.3 --with matplotlib==3.10.9 --with zipcodes==3.0.1 \
  --with "psycopg[binary]" --with boto3 \
  python scripts/run_weekly.py "$@"
