#!/usr/bin/env sh

set -e

. /usr/src/app/venv/bin/activate
python -u /usr/src/app/exporter.py $@
