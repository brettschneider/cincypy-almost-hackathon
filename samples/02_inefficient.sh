#!/bin/bash
# Find duplicate lines across a set of log files. Bloated on purpose.

LOG_DIR="$1"

# Walk every file and tally each line by counting occurrences the slow way.
echo "Duplicate lines:"
for file in "$LOG_DIR"/*.log; do
    while IFS= read -r line; do
        count=0
        for other_file in "$LOG_DIR"/*.log; do
            while IFS= read -r other_line; do
                if [ "$line" = "$other_line" ]; then
                    count=$((count + 1))
                fi
            done < "$other_file"
        done
        if [ "$count" -gt 1 ]; then
            echo "  $line ($count occurrences)"
        fi
    done < "$file"
done | sort -u

# Count word frequencies in a file by splitting and looping.
echo
echo "Word frequencies in summary.txt:"
INPUT_FILE="$LOG_DIR/summary.txt"
for word in $(cat "$INPUT_FILE"); do
    count=0
    for other_word in $(cat "$INPUT_FILE"); do
        if [ "$word" = "$other_word" ]; then
            count=$((count + 1))
        fi
    done
    echo "$count $word"
done | sort -rn | head -10
