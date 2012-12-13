#!/bin/bash

CMD=""
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

for arg in "$@"; do
    CMD="$CMD $arg"
done

make -dn > make_rules.txt
python "$DIR/parserules.py" make_rules.txt > rules.json

strace -s 256 -f -o strace.txt $CMD
python "$DIR/depread.py" strace.txt > deps.txt
python "$DIR/depgen.py" deps.txt > tree.json

bash "$DIR/display.sh"

