#!/usr/bin/env bash
# Rebuilds every result of the paper: downloads the raw data, then runs the ten scripts in order.
set -e
cd "$(dirname "$0")"
for script in src/*.py; do
  echo "== $script"
  python "$script"
done
