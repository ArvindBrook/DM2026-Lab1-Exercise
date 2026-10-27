import os
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path("config/.env"))

key_names = ["GOOGLE_API_KEY"] + [f"GOOGLE_API_KEY_{i}" for i in range(1, 11)]

keys = []

for name in key_names:
    value = os.getenv(name)
    if not value:
        continue

    value = value.strip().strip('"').strip("'")

    if not value:
        continue

    lowered = value.lower()
    if "your-" in lowered or "placeholder" in lowered or "example" in lowered:
        print(f"Skipping placeholder key: {name}")
        continue

    keys.append((name, value))

if not keys:
    print("No usable Google API keys found in config/.env")
    raise SystemExit

for name, key in keys:
    print("\n" + "=" * 60)
    print(name)
    print("=" * 60)
    print("Prefix:", key[:4])
    print("Length:", len(key))

    headers = {"x-goog-api-key": key}

    list_url = "https://generativelanguage.googleapis.com/v1beta/models"

    try:
        resp = requests.get(list_url, headers=headers, timeout=30)
        print("ListModels HTTP status:", resp.status_code)

        if resp.status_code != 200:
            print("Error response:")
            print(resp.text[:700])
            continue

        data = resp.json()
        models = data.get("models", [])

        usable = []

        for model in models:
            methods = model.get("supportedGenerationMethods", [])
            if "generateContent" in methods:
                model_name = model.get("name", "")
                if model_name.startswith("models/"):
                    model_name = model_name.split("/", 1)[1]
                usable.append(model_name)

        if not usable:
            print("No models support generateContent.")
            continue

        print("Models supporting generateContent:")
        for m in usable[:20]:
            print(" -", m)

        preferred = [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
        ]

        chosen = None
        for p in preferred:
            if p in usable:
                chosen = p
                break

        if chosen is None:
            chosen = usable[0]

        print("\nTrying generateContent with model:", chosen)

        generate_url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{chosen}:generateContent"
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": "Reply with exactly: OK"
                        }
                    ]
                }
            ]
        }

        gen_resp = requests.post(
            generate_url,
            headers=headers,
            json=payload,
            timeout=60,
        )

        print("Generate HTTP status:", gen_resp.status_code)
        print(gen_resp.text[:700])

        if gen_resp.status_code == 200:
            print("\nSUCCESS: This Google key works.")
        else:
            print("\nFAILED: This Google key could not generate content.")

    except Exception as exc:
        print("Request failed:", exc)