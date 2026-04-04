#!/bin/sh

set -e

echo "Starting services..."
if uname -s | grep -i 'darwin'; then
    brew services start redis
    brew services start postgresql@17
elif uname -s | grep -i 'linux'; then
    sudo systemctl start redis-server
    sudo systemctl start postgresql@17
else
    echo "Not on macOS or Linux, skipping service start"
fi
