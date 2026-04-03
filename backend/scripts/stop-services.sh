#!/bin/sh

set -e

echo "Stopping services..."
if uname -s | grep -i 'darwin'; then
    brew services stop redis
    brew services stop postgresql@17
elif uname -s | grep -i 'linux'; then
    sudo systemctl stop redis-server
    sudo systemctl stop postgresql@17
else
    echo "Not on macOS or Linux, skipping service stop"
fi
