"""Extract and print utterances from call transcript."""
import json

with open("call_transcript.json", "r", encoding="utf-8") as f:
    data = json.load(f)

utterances = data["results"].get("utterances", [])
meta = data["metadata"]
print(f"Total utterances: {len(utterances)}")
print(f"Call duration: {meta['duration']}s")
print()

for u in utterances:
    spk = u.get("speaker", "?")
    label = "ADITI" if spk == 0 else "USER"
    text = u["transcript"]
    start = round(u["start"], 1)
    end_t = round(u["end"], 1)
    dur = round(end_t - start, 1)
    print(f"[{start}s - {end_t}s] ({dur}s) {label}: {text}")
    print()
