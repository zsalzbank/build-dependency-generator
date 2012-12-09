#!/bin/bash

CMD=""
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

for arg in "$@"; do
    CMD="$CMD $arg"
done

strace -f -o strace.txt $CMD
python "$DIR/depread.py" strace.txt > deps.txt
python "$DIR/depgen.py" deps.txt > tree.json
cp tree.json $DIR

cd $DIR
python -m SimpleHTTPServer &
PID=$!
chromium-browser "http://localhost:8000/display.htm?js=tree.json"
kill -9 $PID
