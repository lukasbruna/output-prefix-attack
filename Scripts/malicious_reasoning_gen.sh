#!/bin/bash

# Default values
PROMPT_START=""
PROMPT_END=""
LIMIT=5
VERBOSE=false
OUTPUT_FILE="prefixes.json"
MODEL="QuixiAI/Wizard-Vicuna-30B-Uncensored"
URL="http://localhost:8000/v1/completions"
DATASET="walledai/AdvBench"
SPLIT="train"
PROMPT_COL="prompt"

usage() {
    echo "Usage: $0 --prompt_start <string> --prompt_end <string> [options]"
    echo "Options:"
    echo "  --prompt_start <string>  Prefix string before the dataset prompt (alias: --string1)"
    echo "  --prompt_end <string>    Suffix string after the dataset prompt (alias: --string2)"
    echo "  --model <model>          Model name (default: $MODEL)"
    echo "  --endpoint <url>         API endpoint URL (alias: --url, default: $URL)"
    echo "  --dataset <name>         Dataset repository/path (default: $DATASET)"
    echo "  --split <split>          Dataset split (default: $SPLIT)"
<<<<<<< HEAD
=======
    echo "  --prompt_col <name>      Column name for prompt (default: $PROMPT_COL)"
>>>>>>> 1f2671ff718d8b2fb3349a5a5648817c19637c8c
    echo "  --limit <int>            Limit number of prompts (default: $LIMIT)"
    echo "  --output_file <path>     JSON output file (default: $OUTPUT_FILE)"
    echo "  --verbose                Print exact curl command and raw response"
    exit 1
}

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --prompt_start|--string1) PROMPT_START="$2"; shift ;;
        --prompt_end|--string2) PROMPT_END="$2"; shift ;;
        --model) MODEL="$2"; shift ;;
        --endpoint|--url) URL="$2"; shift ;;
        --dataset) DATASET="$2"; shift ;;
        --split) SPLIT="$2"; shift ;;
<<<<<<< HEAD
=======
        --prompt_col) PROMPT_COL="$2"; shift ;;
>>>>>>> 1f2671ff718d8b2fb3349a5a5648817c19637c8c
        --limit) LIMIT="$2"; shift ;;
        --output_file) OUTPUT_FILE="$2"; shift ;;
        --verbose) VERBOSE=true ;;
        *) echo "Unknown parameter: $1"; usage ;;
    esac
    shift
done

if ! command -v jq &> /dev/null; then
    echo "Error: jq is not installed. This script requires jq."
    exit 1
fi

echo "Fetching dataset $DATASET..."
DATA=$(python3 -c "from datasets import load_dataset; import json; ds = load_dataset('$DATASET'); [print(json.dumps(x)) for x in ds['$SPLIT'].select(range(min($LIMIT, len(ds['$SPLIT']))))]")

# Initialize output JSON object
echo "{}" > "$OUTPUT_FILE"

IDX=0
while read -r line; do
    if [[ -z "$line" ]]; then continue; fi

    PROMPT=$(echo "$line" | jq -r ".[\"$PROMPT_COL\"] // .[$PROMPT_COL] // \"\"")

    # Construct full prompt by placing dataset prompt between PROMPT_START and PROMPT_END
    FULL_PROMPT="${PROMPT_START}\"${PROMPT}\"${PROMPT_END}"

    echo "Processing prompt $((IDX+1))/$LIMIT..."

    # Construct payload
    PAYLOAD=$(jq -n \
        --arg model "$MODEL" \
        --arg prompt "$FULL_PROMPT" \
        --argjson max_tokens 1500 \
        --argjson temp 0.7 \
        '{model: $model, prompt: $prompt, max_tokens: $max_tokens, temperature: $temp}')

    # Call local API
    if [ "$VERBOSE" = true ]; then
        echo -e "\nExecuting command:"
        echo "curl -X POST \"$URL\" \\"
        echo "  -H \"Content-Type: application/json\" \\"
        echo "  -d '$(echo "$PAYLOAD" | jq -c .)'"
        echo ""
    fi

    RESPONSE=$(curl -s -X POST "$URL" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD")

    if [ "$VERBOSE" = true ]; then
        echo "Raw Response: $RESPONSE"
    fi

    # Extract completion text and wrap in tags
    GENERATED_TEXT=$(echo "$RESPONSE" | jq -r '.choices[0].text // ""')
    WRAPPED_TEXT="<think>${GENERATED_TEXT}</think>"

    # Add to JSON output file
    # We use a temporary file to safely update the JSON
    TMP_FILE=$(mktemp)
    jq --arg idx "$IDX" --arg text "$WRAPPED_TEXT" '.[$idx] = $text' "$OUTPUT_FILE" > "$TMP_FILE" && mv "$TMP_FILE" "$OUTPUT_FILE"

    IDX=$((IDX+1))
done <<< "$DATA"

echo "Generated prefixes saved to $OUTPUT_FILE"