#!/bin/bash

# directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# get the command to be used for the build
CMD=""
for arg in "$@"; do
    CMD="$CMD $arg"
done

# remove any previous results
if [ -f rules.json]; then
    rm rules.json
fi

# if this is a make command, run the additional parsing on the makefile
if [[ "$CMD" =~ make* ]]; then
    # alter the make command to just print the targets
    MCMD=${CMD/make/make -dn}

    # run the altered command
    $MCMD > make_rules.txt

    # parse the results
    python "$DIR/parsemake.py" make_rules.txt > rules.json 2> /dev/null
fi

# run strace on the build
strace -s 256 -f -o strace.txt $CMD

# read the output from strace
python "$DIR/depread.py" strace.txt > deps.txt

# remove any previous results
if [ -f tree.json]; then
    rm tree.json
fi

# generate the file used for displaying the results
python "$DIR/depgen.py" deps.txt > tree.json

# display the output
bash "$DIR/display.sh"

