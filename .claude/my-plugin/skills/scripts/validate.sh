#!/usr/bin/env bash
# validate.sh — Checks source files against the code-formatting skill standards.
# Usage: bash validate.sh [file_or_directory]
#        Defaults to the current working directory when no argument is given.

set -euo pipefail

TARGET="${1:-.}"
PASS=0
FAIL=0
WARNINGS=()

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
warn() {
    local file="$1" rule="$2" detail="$3"
    WARNINGS+=("  [FAIL] $file — $rule: $detail")
    (( FAIL++ )) || true
}

ok() {
    (( PASS++ )) || true
}

# ──────────────────────────────────────────────
# Collect files to check
# ──────────────────────────────────────────────
if [[ -f "$TARGET" ]]; then
    FILES=("$TARGET")
else
    mapfile -t FILES < <(find "$TARGET" \
        \( -name "*.js" -o -name "*.ts" -o -name "*.jsx" -o -name "*.tsx" \
           -o -name "*.py" -o -name "*.sh" \) \
        ! -path "*/node_modules/*" ! -path "*/.git/*" \
        | sort)
fi

if [[ ${#FILES[@]} -eq 0 ]]; then
    echo "No source files found in: $TARGET"
    exit 0
fi

# ──────────────────────────────────────────────
# Rules
# ──────────────────────────────────────────────

check_file_header() {
    local file="$1"
    # Accepts: /** @file ... */, # @file ..., or // @file ...
    if head -5 "$file" | grep -qE '(@file|@author|@date)'; then
        ok
    else
        warn "$file" "File Header" "Missing @file / @author / @date header in first 5 lines"
    fi
}

check_no_magic_numbers() {
    local file="$1"
    # Flag bare numeric literals that are not 0 or 1 and not inside a named constant assignment
    if grep -Pn '(?<![A-Z_=\s])\b[2-9][0-9]{2,}\b' "$file" | grep -qv '^\s*//'; then
        warn "$file" "Magic Numbers" \
            "Found large numeric literals — consider extracting to named constants (UPPER_CASE)"
    else
        ok
    fi
}

check_function_docs() {
    local file="$1"
    local ext="${file##*.}"
    local missing=0

    if [[ "$ext" == "js" || "$ext" == "ts" || "$ext" == "jsx" || "$ext" == "tsx" ]]; then
        # Find lines with 'function ' or ') =>' that are NOT immediately preceded by a JSDoc block
        while IFS= read -r lineno; do
            local prev_line
            prev_line=$(sed -n "$((lineno - 1))p" "$file" 2>/dev/null || true)
            if ! echo "$prev_line" | grep -qE '(\*/|#|//)'; then
                (( missing++ )) || true
            fi
        done < <(grep -n 'function \|=>' "$file" | cut -d: -f1)
    elif [[ "$ext" == "py" ]]; then
        # Python: check def without a following docstring
        while IFS= read -r lineno; do
            local next_line
            next_line=$(sed -n "$((lineno + 1))p" "$file" 2>/dev/null || true)
            if ! echo "$next_line" | grep -qE '"""|\x27\x27\x27'; then
                (( missing++ )) || true
            fi
        done < <(grep -n '^\s*def ' "$file" | cut -d: -f1)
    fi

    if [[ $missing -gt 0 ]]; then
        warn "$file" "Function Docs" \
            "$missing function(s) appear to lack doc-comments (JSDoc / docstring)"
    else
        ok
    fi
}

check_indentation() {
    local file="$1"
    local ext="${file##*.}"

    if [[ "$ext" == "py" ]]; then
        # Python: tabs are non-standard (PEP 8 uses 4 spaces)
        if grep -Pq '^\t' "$file"; then
            warn "$file" "Indentation" "Tab indentation found — Python (PEP 8) expects 4 spaces"
        else
            ok
        fi
    else
        # JS/TS: flag mixed tabs and spaces
        local has_tabs has_spaces
        has_tabs=$(grep -Pc '^\t' "$file" || true)
        has_spaces=$(grep -Pc '^ {2,}' "$file" || true)
        if [[ $has_tabs -gt 0 && $has_spaces -gt 0 ]]; then
            warn "$file" "Indentation" "Mixed tabs and spaces detected — pick one and apply consistently"
        else
            ok
        fi
    fi
}

check_line_length() {
    local file="$1"
    local limit=120
    local long_lines
    long_lines=$(awk "length > $limit" "$file" | wc -l)
    if [[ $long_lines -gt 0 ]]; then
        warn "$file" "Line Length" "$long_lines line(s) exceed $limit characters"
    else
        ok
    fi
}

check_no_console_log() {
    local file="$1"
    local ext="${file##*.}"
    if [[ "$ext" == "js" || "$ext" == "ts" || "$ext" == "jsx" || "$ext" == "tsx" ]]; then
        local count
        count=$(grep -c 'console\.log' "$file" || true)
        if [[ $count -gt 0 ]]; then
            warn "$file" "Debug Statements" \
                "$count console.log() call(s) found — remove or replace with a proper logger"
        else
            ok
        fi
    fi
}

# ──────────────────────────────────────────────
# Run checks on every collected file
# ──────────────────────────────────────────────
echo "Validating ${#FILES[@]} file(s) in: $TARGET"
echo "────────────────────────────────────────"

for file in "${FILES[@]}"; do
    check_file_header      "$file"
    check_no_magic_numbers "$file"
    check_function_docs    "$file"
    check_indentation      "$file"
    check_line_length      "$file"
    check_no_console_log   "$file"
done

# ──────────────────────────────────────────────
# Report
# ──────────────────────────────────────────────
echo ""
if [[ ${#WARNINGS[@]} -gt 0 ]]; then
    for w in "${WARNINGS[@]}"; do echo "$w"; done
    echo ""
fi

echo "────────────────────────────────────────"
echo "Result: $PASS check(s) passed, $FAIL check(s) failed"

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
