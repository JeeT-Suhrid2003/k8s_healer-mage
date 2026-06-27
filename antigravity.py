
import os
import sys
from google import genai


def main():
    api_key = "AIzaSyBSedAgAZCmRK257BKfiXvQBWbkznS9nes"
    if not api_key:
        print(
            "Error: API key not found. Set the GENAI_API_KEY or GOOGLE_API_KEY environment variable.",
            file=sys.stderr,
        )
        return 1

    client = genai.Client(api_key=api_key)

    print("🚀 Activating Antigravity SRE Agent... Please wait while the remote sandbox provisions.")

    # Using a streaming interaction to print real-time logs
    # Provide the agent with clear context about your infrastructure layout
    try:
        interaction = client.interactions.create(
            agent="antigravity-preview-05-2026",
            input=(
                "Authenticate using the provided project details. "
                "Target GCP Project ID: 'qwiklabs-gcp-01-96311a8ba97a'. "
                "Cluster Name: 'my-cluster'. "
                "Region/Zone: 'europe-west1'. "
                "Check the 'broken-nginx' deployment in the default namespace. "
                "If it is failing, analyze the logs and fix it."
            ),
            environment="remote",
            stream=True,
        )
    except Exception as e:
        print("Failed to start interaction:", e, file=sys.stderr)
        return 1

    print("\n--- Agent Live Stream ---")

    # interaction may be a callable that returns an iterator, or an iterable/stream object.
    if callable(interaction):
        iterator = interaction()
    elif hasattr(interaction, "__iter__"):
        iterator = interaction
    elif hasattr(interaction, "stream") and callable(getattr(interaction, "stream")):
        iterator = interaction.stream()
    else:
        print("Interaction object is not iterable or callable:", type(interaction), file=sys.stderr)
        return 1

    try:
        for chunk in iterator:
            try:
                # Handle several possible chunk formats
                if isinstance(chunk, str):
                    print(chunk, flush=True)
                    continue

                if hasattr(chunk, "text") and getattr(chunk, "text"):
                    print(getattr(chunk, "text"), flush=True)
                    continue

                # dict-like payloads
                if isinstance(chunk, dict):
                    text = chunk.get("text")
                    if not text:
                        delta = chunk.get("delta") or {}
                        text = delta.get("text") if isinstance(delta, dict) else None
                    if text:
                        print(text, flush=True)
                        continue

                # nested object with delta
                if hasattr(chunk, "delta") and getattr(chunk.delta, "text", None):
                    print(chunk.delta.text, flush=True)
                    continue

                # fallback: show representation for debugging
                print(repr(chunk), flush=True)
            except Exception as e:
                print("Stream chunk parse error:", e, file=sys.stderr)
    except Exception as e:
        print("Streaming failed:", e, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())