#!/bin/sh
set -e
javac -d /app /app/app/Hello.java
java -cp /app Hello
