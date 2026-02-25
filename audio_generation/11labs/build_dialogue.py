#!/usr/bin/env python3
"""Build dialogue.json from tagged text and cast list."""
import json
import re

CAST_PATH = "true_luna_miltivoice_cast_list.json"
TAGGED_PATH = "true_luna_miltivoice_tagged.txt"
OUTPUT_PATH = "input/dialogue.json"

def main():
    with open(CAST_PATH, encoding="utf-8") as f:
        cast = json.load(f)
    id_to_voice = {c["id"]: c["voice_id"] for c in cast["characters"]}

    with open(TAGGED_PATH, encoding="utf-8") as f:
        lines = f.readlines()

    inputs = []
    pattern = re.compile(r"^\[([^\]]+)\]:\s*(.*)$")
    for line in lines:
        line = line.rstrip("\n")
        if not line.strip():
            continue
        m = pattern.match(line)
        if not m:
            continue
        speaker_id, text = m.group(1).strip(), m.group(2).strip()
        voice_id = id_to_voice.get(speaker_id)
        if voice_id is None:
            raise SystemExit(f"Unknown speaker: {speaker_id!r}")
        inputs.append({"text": text, "voice_id": voice_id})

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump({"inputs": inputs}, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(inputs)} entries to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
