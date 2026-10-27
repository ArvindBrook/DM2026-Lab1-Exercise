import os
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

fatal = []
warning_list = []


def hr(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


hr("1. Python version")
print(sys.version)

if sys.version_info[:2] != (3, 11):
    fatal.append("Python is not 3.11.x. Run: uv python install 3.11 then uv sync")
else:
    print("PASS: Python 3.11 detected")


hr("2. Required packages")
modules = [
    "pandas",
    "numpy",
    "scipy",
    "sklearn",
    "nltk",
    "matplotlib",
    "seaborn",
    "plotly",
    "kaleido",
    "ipywidgets",
    "dotenv",
    "requests",
    "umap",
]

for mod in modules:
    try:
        __import__(mod)
        print(f"OK   {mod}")
    except Exception as exc:
        fatal.append(f"Missing/broken package: {mod} -> {exc}")
        print(f"FAIL {mod}: {exc}")

pami_ok = False
for mod in ["PAMI", "pami"]:
    try:
        __import__(mod)
        pami_ok = True
        print(f"OK   {mod}")
        break
    except Exception:
        pass

if not pami_ok:
    warning_list.append("Could not import PAMI. If Master notebook fails on PAMI, rerun uv sync.")


hr("3. API key file")
env_path = Path("config/.env")

if not env_path.exists():
    fatal.append("config/.env does not exist. Copy config/.env.example to config/.env and put real keys there.")
else:
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
        print(f"Loaded {env_path}")
    except Exception as exc:
        fatal.append(f"Could not load config/.env: {exc}")

    def inspect_key(name):
        value = os.getenv(name)
        if value is None or value.strip() == "":
            return "NOT SET", None

        value = value.strip().strip('"').strip("'")
        lowered = value.lower()

        placeholder = any(
            token in lowered
            for token in ["your-", "placeholder", "example", "changeme", "xxxx"]
        )

        if placeholder:
            return "PLACEHOLDER", None

        return "SET", len(value)

    key_names = ["GROQ_API_KEY", "GOOGLE_API_KEY"] + [
        f"GOOGLE_API_KEY_{i}" for i in range(1, 10)
    ]

    detected_providers = []

    for name in key_names:
        status, length = inspect_key(name)

        if status == "NOT SET":
            print(f"NOT SET      {name}")
        elif status == "PLACEHOLDER":
            fatal.append(f"{name} still looks like placeholder text. Replace it with a real key.")
            print(f"PLACEHOLDER  {name}")
        else:
            print(f"SET          {name} (length={length})")

            if name == "GROQ_API_KEY":
                detected_providers.append("Groq")
            else:
                detected_providers.append("Google")

    detected_providers = sorted(set(detected_providers))

    if not detected_providers:
        fatal.append("No real Groq or Google API key was detected in config/.env.")
    else:
        print("Detected providers:", ", ".join(detected_providers))


hr("4. NLTK smoke test")
try:
    import nltk

    download_packages = [
        "punkt",
        "punkt_tab",
        "stopwords",
        "averaged_perceptron_tagger",
        "averaged_perceptron_tagger_eng",
        "maxent_ne_chunker",
        "words",
    ]

    for pkg in download_packages:
        try:
            nltk.download(pkg, quiet=True)
        except Exception as exc:
            warning_list.append(f"NLTK download failed for {pkg}: {exc}")

    from nltk.tokenize import word_tokenize

    tokens = word_tokenize("Hello, lab! This is a tokenization test.")
    print("Tokenization sample:", tokens)

except Exception as exc:
    fatal.append(f"NLTK smoke test failed: {exc}")


hr("5. 20 Newsgroups subset download/load")
data = None

try:
    from sklearn.datasets import fetch_20newsgroups

    categories = [
        "alt.atheism",
        "comp.graphics",
        "sci.med",
        "soc.religion.christian",
    ]

    data = fetch_20newsgroups(
        subset="all",
        categories=categories,
        shuffle=True,
        random_state=42,
    )

    print("Loaded documents:", len(data.data))

    if len(data.data) == 0:
        fatal.append("20 Newsgroups loader returned zero documents.")

except Exception as exc:
    fatal.append(f"20 Newsgroups download/load failed: {exc}")


hr("6. CountVectorizer smoke test")
if data is not None and len(data.data) > 0:
    try:
        from sklearn.feature_extraction.text import CountVectorizer

        vectorizer = CountVectorizer(stop_words="english", max_features=1000)
        X = vectorizer.fit_transform(data.data[:50])

        print("Small document-term matrix shape:", X.shape)
        print("Non-zero entries:", X.nnz)

    except Exception as exc:
        warning_list.append(f"CountVectorizer smoke test failed: {exc}")
else:
    warning_list.append("Skipped CountVectorizer smoke test because dataset was not loaded.")


hr("7. Optional live API tests")
if os.getenv("RUN_API_TESTS", "").strip() != "1":
    print("Skipped live API tests.")
    print("To run them, use:")
    print("    $env:RUN_API_TESTS='1'")
    print("    uv run python test_env.py")
else:
    import requests

    groq_key = os.getenv("GROQ_API_KEY")

    if groq_key:
        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {groq_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
                    "max_tokens": 5,
                },
                timeout=30,
            )

            print("Groq HTTP status:", resp.status_code)

            if resp.status_code != 200:
                warning_list.append(f"Groq API test failed: {resp.text[:300]}")
            else:
                print("Groq API test passed.")

        except Exception as exc:
            warning_list.append(f"Groq API request error: {exc}")

    google_key = os.getenv("GOOGLE_API_KEY")

    if not google_key:
        for i in range(1, 10):
            google_key = os.getenv(f"GOOGLE_API_KEY_{i}")
            if google_key:
                break

    if google_key:
        models_to_try = [
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b",
        ]

        google_ok = False
        last_error = ""

        for model in models_to_try:
            try:
                url = (
                    "https://generativelanguage.googleapis.com/"
                    f"v1beta/models/{model}:generateContent"
                )

                resp = requests.post(
                    url,
                    headers={
                        "x-goog-api-key": google_key,
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
                    timeout=30,
                )

                print(f"Google {model} HTTP status:", resp.status_code)

                if resp.status_code == 200:
                    google_ok = True
                    print("Google API test passed.")
                    break
                else:
                    last_error = f"{model}: {resp.text[:300]}"

            except Exception as exc:
                last_error = f"{model}: {exc}"

        if not google_ok:
            warning_list.append(f"Google API test failed. Last error: {last_error}")


hr("SUMMARY")

if fatal:
    print("ENVIRONMENT CHECK FAILED")
    for item in fatal:
        print("- FAIL:", item)
    sys.exit(1)
else:
    print("ENVIRONMENT CHECK PASSED")

    if warning_list:
        print("\nWarnings, not necessarily blocking:")
        for item in warning_list:
            print("- WARN:", item)