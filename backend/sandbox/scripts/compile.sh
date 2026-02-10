#!/bin/sh
set -e

MAIN_CLASS="${1:?Usage: compile.sh <MainClassName>}"

mkdir -p /workspace/out
javac -d /workspace/out /workspace/src/*.java
