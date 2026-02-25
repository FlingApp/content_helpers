#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT_DIR="${SCRIPT_DIR}/input"
TOKEN_FILE="${INPUT_DIR}/.token"

if [[ ! -f "$TOKEN_FILE" ]]; then
  echo "Error: API token not found at ${TOKEN_FILE}" >&2
  exit 1
fi

ELEVENLABS_API_KEY="$(cat "$TOKEN_FILE")"

curl -s "https://api.elevenlabs.io/v1/models" \
  -H "xi-api-key: ${ELEVENLABS_API_KEY}" \
  | jq .
