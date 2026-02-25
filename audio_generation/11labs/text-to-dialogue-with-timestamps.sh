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
  echo "Error: dialogue.json not found at ${DIALOGUE_FILE}" >&2
  exit 1
fi

command -v jq >/dev/null 2>&1 || { echo "Error: jq is required but not installed." >&2; exit 1; }

ELEVENLABS_API_KEY="$(cat "$TOKEN_FILE")"
MODEL_ID="$(cat "$MODEL_FILE")"

mkdir -p "$OUTPUT_DIR"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUTPUT_MP3="${OUTPUT_DIR}/dialogue_ts_${TIMESTAMP}.mp3"
OUTPUT_JSON="${OUTPUT_DIR}/dialogue_ts_${TIMESTAMP}.json"
RESPONSE_FILE="${OUTPUT_DIR}/.response_ts_${TIMESTAMP}.json"

jq --arg model "$MODEL_ID" '. + {model_id: $model}' "$DIALOGUE_FILE" | \
curl -X POST "https://api.elevenlabs.io/v1/text-to-dialogue/with-timestamps?output_format=mp3_44100_128" \
  -H "Content-Type: application/json" \
  -H "xi-api-key: ${ELEVENLABS_API_KEY}" \
  -d @- \
  -o "$RESPONSE_FILE"

# Decode base64 audio and save as mp3
jq -r '.audio_base64' "$RESPONSE_FILE" | base64 -d > "$OUTPUT_MP3"

# Save full response without audio_base64
jq 'del(.audio_base64)' "$RESPONSE_FILE" > "$OUTPUT_JSON"

rm -f "$RESPONSE_FILE"

echo "Saved to ${OUTPUT_MP3}"
echo "Saved to ${OUTPUT_JSON}"