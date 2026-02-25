#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT_DIR="${SCRIPT_DIR}/input"
OUTPUT_DIR="${SCRIPT_DIR}/output"
TOKEN_FILE="${INPUT_DIR}/.token"
MODEL_FILE="${INPUT_DIR}/.model"
DIALOGUE_FILE="${INPUT_DIR}/dialogue.json"

if [[ ! -f "$TOKEN_FILE" ]]; then
  echo "Error: API token not found at ${TOKEN_FILE}" >&2
  exit 1
fi

if [[ ! -f "$MODEL_FILE" ]]; then
  echo "Error: .model not found at ${MODEL_FILE}" >&2
  exit 1
fi

if [[ ! -f "$DIALOGUE_FILE" ]]; then
  echo "Error: DIALOGUE.JSON not found at ${DIALOGUE_FILE}" >&2
  exit 1
fi

command -v jq >/dev/null 2>&1 || { echo "Error: jq is required but not installed." >&2; exit 1; }

ELEVENLABS_API_KEY="$(cat "$TOKEN_FILE")"
MODEL_ID="$(cat "$MODEL_FILE")"

mkdir -p "$OUTPUT_DIR"

OUTPUT_MP3="${OUTPUT_DIR}/dialogue_$(date +%Y%m%d_%H%M%S).mp3"

jq --arg model "$MODEL_ID" '. + {model_id: $model}' "$DIALOGUE_FILE" | \
curl -X POST "https://api.elevenlabs.io/v1/text-to-dialogue?output_format=mp3_44100_128" \
  -H "Content-Type: application/json" \
  -H "xi-api-key: ${ELEVENLABS_API_KEY}" \
  -d @- \
  -o "$OUTPUT_MP3"

echo "Saved to ${OUTPUT_MP3}"