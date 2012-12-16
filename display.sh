#!/bin/bash

# get the directory in which this script is contained
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# copy any files used for display to the directory
cp tree.json $DIR

# only copy the rules file (for makes) if it exists
if [ -f rules.json ]; then
    cp rules.json $DIR
fi

# change to the directory
cd $DIR

# start an http server in the directory so the display page can be shown
python -m SimpleHTTPServer &

# track the pid of the server so it can be closed
PID=$!

# browse to the display page
chromium-browser "http://localhost:8000/display.htm?js=tree.json&rules=rules.json" &

# kill the server after a little while
sleep 5
kill -9 $PID
