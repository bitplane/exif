#!/bin/bash

# Interactive terminal browser for testing filter results
# Watches build_makefile.py for changes and regenerates file list

FILTER_SCRIPT="./scripts/test_filter.py"
WATCH_FILE="./scripts/build_makefile.py"
BUFFER1="/tmp/screen_buffer.1"
BUFFER2="/tmp/screen_buffer.2"
OUTPUT_FILE="/tmp/filter_output"

# Terminal state
line_num=0
col_num=0
last_changed=0
screen_width=80
screen_height=24
md5_last=""

# Exit handler to restore terminal
cleanup() {
    echo -e "\033[?1049l\033[?25h" # Restore alt screen and show cursor
    if [[ -n "$STTY_ORIG" ]]; then
        stty "$STTY_ORIG" 2>/dev/null || stty sane 2>/dev/null
    else
        stty sane 2>/dev/null
    fi
    exit 0
}
trap cleanup EXIT INT TERM

# Save terminal state and enter alt screen + raw mode
echo -e "\033[?1049h\033[?25l" # Alt screen + hide cursor
# Save current stty settings
STTY_ORIG=$(stty -g 2>/dev/null || echo "")
stty -echo -icanon min 0 time 0 2>/dev/null || {
    echo "Warning: Could not set terminal to raw mode" >&2
}

# Get initial screen size
get_screen_size() {
    if command -v tput >/dev/null 2>&1; then
        screen_width=$(tput cols 2>/dev/null || echo 80)
        screen_height=$(tput lines 2>/dev/null || echo 24)
    else
        # Fallback if tput doesn't exist
        screen_width=${COLUMNS:-80}
        screen_height=${LINES:-24}
    fi
}

# Generate filter output if file changed
update_output() {
    local mtime=$(stat -c %Y "$WATCH_FILE" 2>/dev/null || echo 0)
    if [[ $mtime -gt $last_changed ]]; then
        echo "Regenerating filter output..." >&2
        $FILTER_SCRIPT > "$OUTPUT_FILE" 2>/dev/null || {
            echo "Error running filter script" > "$OUTPUT_FILE"
        }
        last_changed=$mtime
    fi
}

# Render screen buffer
render_screen() {
    get_screen_size
    
    # Clear screen buffer
    > "$BUFFER2"
    
    # Add clear screen codes
    echo -e "\033[2J\033[H" >> "$BUFFER2"
    
    # Calculate visible window
    local total_lines=$(wc -l < "$OUTPUT_FILE" 2>/dev/null || echo 0)
    local max_line=$((line_num + screen_height - 1))
    
    # Show lines with head/tail and cut for width (reserve last line for status)
    local content_height=$((screen_height - 1))
    if [[ $total_lines -gt 0 ]]; then
        tail -n +$((line_num + 1)) "$OUTPUT_FILE" | \
        head -n $content_height | \
        cut -c $((col_num + 1))-$((col_num + screen_width)) >> "$BUFFER2"
    fi
    
    # Add status line (no newline to avoid scrolling)
    printf "\033[${screen_height};1H\033[7m Line: $line_num/$total_lines Col: $col_num | q=quit ↑↓←→=move PgUp/PgDn=page Home/End=jump \033[0m" >> "$BUFFER2"
    
    # Check if screen changed
    local md5_new=$(md5sum "$BUFFER2" | cut -d' ' -f1)
    if [[ "$md5_new" != "$md5_last" ]]; then
        cat "$BUFFER2"
        md5_last="$md5_new"
        cp "$BUFFER2" "$BUFFER1"
    fi
}

# Handle keypress
handle_key() {
    local key
    read -t 0.2 -n 1 key || return
    
    case "$key" in
        'q'|'Q') exit 0 ;;
        $'\033') # Escape sequence
            read -t 0.1 -n 1 key || return
            if [[ "$key" == "[" ]]; then
                read -t 0.1 -n 1 key || return
                case "$key" in
                    'A') # Up arrow
                        line_num=$((line_num > 0 ? line_num - 1 : 0))
                        ;;
                    'B') # Down arrow  
                        local total_lines=$(wc -l < "$OUTPUT_FILE" 2>/dev/null || echo 0)
                        local content_height=$((screen_height - 1))
                        local max_line=$((total_lines - content_height))
                        line_num=$((line_num + 1))
                        if [[ $line_num -gt $max_line ]]; then line_num=$max_line; fi
                        if [[ $line_num -lt 0 ]]; then line_num=0; fi
                        ;;
                    'C') # Right arrow
                        col_num=$((col_num + 1))
                        ;;
                    'D') # Left arrow
                        col_num=$((col_num > 0 ? col_num - 1 : 0))
                        ;;
                    '5') # Page up (Ctrl+Page Up sends [5~)
                        read -t 0.1 -n 1 tilde || return
                        if [[ "$tilde" == "~" ]]; then
                            local content_height=$((screen_height - 1))
                            line_num=$((line_num - content_height))
                            if [[ $line_num -lt 0 ]]; then line_num=0; fi
                        fi
                        ;;
                    '6') # Page down (Ctrl+Page Down sends [6~)
                        read -t 0.1 -n 1 tilde || return
                        if [[ "$tilde" == "~" ]]; then
                            local total_lines=$(wc -l < "$OUTPUT_FILE" 2>/dev/null || echo 0)
                            local content_height=$((screen_height - 1))
                            local max_line=$((total_lines - content_height))
                            line_num=$((line_num + content_height))
                            if [[ $line_num -gt $max_line ]]; then line_num=$max_line; fi
                            if [[ $line_num -lt 0 ]]; then line_num=0; fi
                        fi
                        ;;
                    'H') # Home
                        line_num=0
                        col_num=0
                        ;;
                    'F') # End
                        local total_lines=$(wc -l < "$OUTPUT_FILE" 2>/dev/null || echo 0)
                        local content_height=$((screen_height - 1))
                        line_num=$((total_lines - content_height))
                        if [[ $line_num -lt 0 ]]; then line_num=0; fi
                        ;;
                esac
            fi
            ;;
    esac
}

# Main loop
echo "Starting interactive filter browser..." >&2
echo "Watching: $WATCH_FILE" >&2
echo "Press 'q' to quit, arrow keys to navigate" >&2

while true; do
    update_output
    render_screen
    handle_key
done