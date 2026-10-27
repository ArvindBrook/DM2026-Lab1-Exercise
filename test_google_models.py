import os
import json
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
        continue

    keys.append((name, value))

if not keys:
    print("No usable Google API keys found in config/.env")
    raise SystemExit

candidate_models = [
    "gemini-3.8-flash",
    "gemini-flash-latest",
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite",
    "gemini-3.1-flash-lite-preview",
    "gemini-2.5-flash-lite",
    "gemini-pro-latest",
]

generate_url_template = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)

interactions_url = "https://generativelanguage.googleapis.com/v1beta/interactions"


def try_generate_content(key, model):
    url = generate_url_template.format(model=model)

    try:
        resp = requests.post(
            url,
            headers={
                "x-goog-api-key": key,
                "Content-Type": "application/json",
            },
            json={
                "contents": [
                    {
                        "parts": [
                            {
                                "text": "Reply with exactly: OK"
                            }
                        ]
                    }
                ]
            },
            timeout=60,
        )

        return resp.status_code, resp.text[:700]

    except Exception as exc:
        return None, str(exc)


def try_interactions_api(key, model):
    try:
        resp = requests.post(
            interactions_url,
            headers={
                "x-goog-api-key": key,
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "input": "Reply with exactly: OK",
            },
            timeout=60,
        )

        return resp.status_code, resp.text[:700]

    except Exception as exc:
        return None, str(exc)


print("=" * 70)
print("Testing first available Google key across candidate models")
print("=" * 70)

first_name, first_key = keys[0]

print(f"Using key: {first_name}")
print(f"Prefix: {first_key[:4]}")
print(f"Length: {len(first_key)}")

working_generate = []
working_interactions = []

for model in candidate_models:
    print("\n" + "-" * 70)
    print(f"Model: {model}")
    print("-" * 70)

    gen_status, gen_body = try_generate_content(first_key, model)
    int_status, int_body = try_interactions_api(first_key, model)

    print(f"generateContent status: {gen_status}")
    if gen_status != 200:
        print("generateContent response:")
        print(gen_body)
    else:
        print("generateContent SUCCESS")
        working_generate.append(model)

    print(f"Interactions API status: {int_status}")
    if int_status != 200:
        print("Interactions API response:")
        print(int_body)
    else:
        print("Interactions API SUCCESS")
        working_interactions.append(model)

print("\n" + "=" * 70)
print("RESULTS FOR FIRST KEY")
print("=" * 70)

if working_generate:
    print("Working generateContent models:")
    for m in working_generate:
        print(" -", m)
else:
    print("No working generateContent model found for first key.")

if working_interactions:
    print("Working Interactions API models:")
    for m in working_interactions:
        print(" -", m)
else:
    print("No working Interactions API model found for first key.")

if not working_generate and not working_interactions:
    print("\n" + "=" * 70)
    print("Testing all keys with likely models")
    print("=" * 70)

    likely_models = [
        "gemini-3.8-flash",
        "gemini-flash-latest",
        "gemini-3-flash-preview",
    ]

    all_working = []

    for name, key in keys:
        print("\n" + "-" * 70)
        print(f"Key: {name}")
        print("-" * 70)

        for model in likely_models:
            gen_status, _ = try_generate_content(key, model)
            int_status, _ = try_interactions_api(key, model)

            print(f"{model}: generateContent={gen_status}, Interactions={int_status}")

            if gen_status == 200:
                all_working.append((name, "generateContent", model))
            if int_status == 200:
                all_working.append((name, "Interactions", model))

    if all_working:
        print("\n" + "=" * 70)
        print("WORKING COMBINATIONS FOUND")
        print("=" * 70)
        for name, api, model in all_working:
            print(f"{name} | {api} | {model}")
    else:
        print("\n" + "=" * 70)
        print("NO WORKING GOOGLE MODEL FOUND")
        print("=" * 70)
        print("Use Groq instead, or ask the TA whether the lab backend needs a newer Gemini model/API.")