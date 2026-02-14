#!/bin/sh
set -e

MAIN_CLASS="${1:?Usage: run.sh <MainClassName>}"
TIMEOUT="${2:-10}"

timeout "${TIMEOUT}" java -cp /workspace/compiled "$MAIN_CLASS" < /workspace/input/input.txt
