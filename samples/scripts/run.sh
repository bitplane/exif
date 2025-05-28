#!/bin/bash

# Read commands from stdin and execute them
# Shows progress as [n/count]: command

total=$(wc -l < /dev/stdin)
count=0

while IFS= read -r cmd; do
    count=$((count + 1))
    echo "[${count}/${total}]: $cmd"
    eval "$cmd"
done