#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cp tree.json $DIR
cp rules.json $DIR

cd $DIR
python -m SimpleHTTPServer &
PID=$!
chromium-browser "http://localhost:8000/display.htm?js=tree.json&rules=rules.json" &
sleep 5
kill -9 $PID
