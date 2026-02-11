#!/bin/sh
set -e

MAIN_CLASS="${1:?Usage: compile.sh <MainClassName>}"

mkdir -p /workspace/compiled
javac -d /workspace/compiled /workspace/src/${MAIN_CLASS}.java
