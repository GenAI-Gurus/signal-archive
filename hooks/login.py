#!/usr/bin/env python3
"""
Signal Archive CLI login.
Opens a browser to sign in via magic link. Polls until auth completes,
then prints the export command to configure SIGNAL_ARCHIVE_API_KEY.
"""
import os
import sys
import time
import subprocess
import urllib.request
import urllib.error
import json

API_URL = os.environ.get("SIGNAL_ARCHIVE_API_URL", "https://signal-archive-api.fly.dev")
POLL_INTERVAL_SECS = 2
TIMEOUT_SECS = 600  # 10 minutes


def api_post(path: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{API_URL}{path}", data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def api_get(path: str) -> dict:
    with urllib.request.urlopen(f"{API_URL}{path}", timeout=10) as resp:
        return json.loads(resp.read())


def open_browser(url: str) -> None:
    for cmd in (["open", url], ["xdg-open", url]):
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except FileNotFoundError:
            continue
    print(f"  Open this URL in your browser:\n  {url}")


def main():
    print("\nSignal Archive — Login\n")

    if os.environ.get("SIGNAL_ARCHIVE_API_KEY"):
        print("✓ Already logged in (SIGNAL_ARCHIVE_API_KEY is set).")
        print("  To log in again: unset SIGNAL_ARCHIVE_API_KEY")
        sys.exit(0)

    print("→ Creating login session…")
    try:
        session = api_post("/auth/cli-session", {})
    except Exception as e:
        print(f"Error connecting to Signal Archive API: {e}")
        sys.exit(1)

    login_url = session["login_url"]
    session_id = session["session_id"]

    print(f"→ Opening browser to complete sign-in…")
    open_browser(login_url)
    print("\nWaiting for browser sign-in…  (Ctrl+C to cancel)\n")

    deadline = time.time() + TIMEOUT_SECS
    while time.time() < deadline:
        time.sleep(POLL_INTERVAL_SECS)
        try:
            result = api_get(f"/auth/cli-session/{session_id}/poll")
        except urllib.error.HTTPError as e:
            if e.code == 410:
                print("\nSession expired. Run /signal-archive:login again.")
                sys.exit(1)
            continue
        except Exception:
            continue

        if result.get("ready") and result.get("api_key"):
            api_key = result["api_key"]
            print("\n✓ Logged in!\n")
            print("Add your API key to your shell profile:\n")
            print(f"  echo 'export SIGNAL_ARCHIVE_API_KEY=\"{api_key}\"' >> ~/.zshrc")
            print("  source ~/.zshrc\n")
            print("Or for this session only:\n")
            print(f"  export SIGNAL_ARCHIVE_API_KEY=\"{api_key}\"\n")
            sys.exit(0)

        print(".", end="", flush=True)

    print("\nTimed out. Run /signal-archive:login again.")
    sys.exit(1)


if __name__ == "__main__":
    main()
