#!/usr/bin/env python3
import json
import urllib.request
import os

def campaign_ideas(brand, concept, max_ideas=3):
    try:
        prompt = (
            f"You are a marketing expert. "
            f"Given this brand: {brand} "
            f"and this concept note: {concept} "
            f"generate exactly {max_ideas} campaign ideas. "
            f"Format your response as:\n"
            f"1. [Title]: [Description]\n"
            f"2. [Title]: [Description]\n"
            f"3. [Title]: [Description]"
        )

        payload = json.dumps({
            "model": "qwen2.5:14b",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }).encode("utf-8")

        req = urllib.request.Request(
            "http://localhost:11434/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=60) as r:
            body = json.loads(r.read().decode("utf-8"))

        result = body["message"]["content"]

        output_path = f"/home/jovyan/PeTTa/repos/mettaclaw/channels/campaign-{brand.replace(' ', '_')}.txt"
        with open(output_path, "a", encoding="utf-8") as f:
            f.write(f"\n=== Campaign Ideas for: {brand} ===\n")
            f.write(f"Concept: {concept}\n")
            f.write(result)
            f.write("\n")

        ret = "("
        for line in result.strip().split("\n"):
            if line.strip():
                ret += "(IDEA: " + line.strip() + ") "
        ret += ")"
        return ret

    except Exception as e:
        output_path = f"/home/jovyan/PeTTa/repos/mettaclaw/channels/campaign-{brand.replace(' ', '_')}.txt"
        with open(output_path, "a", encoding="utf-8") as f:
            f.write(f"\n=== ERROR for: {brand} ===\n{str(e)}\n")
        return "(ERROR: " + str(e) + ")"