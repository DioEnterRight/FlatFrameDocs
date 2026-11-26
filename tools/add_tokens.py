"""Token adder: puts every FlatFrameDocs key into this repo's GitHub Actions secrets, from your own PC.

  pip install google-auth-oauthlib          (only needed for the YouTube part)
  gh auth login                             (once; GitHub CLI)
  python tools/add_tokens.py                (ask for everything; Enter skips one)
  python tools/add_tokens.py --youtube client_secret.json   (also runs the YouTube sign-in)
  python tools/add_tokens.py --list         (show which secrets are set; values are never shown)

Values are typed hidden and handed to `gh secret set` on stdin, so they never land in your shell history,
the command line or a file. Use the FlatFrameDocs channel and its own Google Cloud OAuth client for YouTube.
"""
import argparse
import getpass
import json
import subprocess
import sys

NAMES = ["FREELLMAPI_KEYS", "IG_USER_ID", "IG_PAGE_TOKEN", "YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"]
YT_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


def gh(*args, value=None):
    r = subprocess.run(["gh", *args], input=value, text=True, capture_output=True)
    if r.returncode != 0:
        sys.exit(f"gh {args[0]} {args[1]} failed: {r.stderr.strip()}")
    return r.stdout


def existing(repo):
    return {s["name"] for s in json.loads(gh("secret", "list", "--repo", repo, "--json", "name"))}


def ask_freellm_keys():
    print("\nFREELLMAPI_KEYS: free-tier provider keys. Paste the whole JSON list, or add them one by one.")
    first = input("  JSON list (or Enter to add one by one, 'skip' to skip): ").strip()
    if first.lower() == "skip":
        return None
    if first:
        keys = json.loads(first)
    else:
        keys = []
        while True:
            platform = input("  platform (google, groq, openrouter, ... ; Enter = done): ").strip().lower()
            if not platform:
                break
            key = getpass.getpass(f"  {platform} key (hidden): ").strip()
            if key:
                keys.append({"platform": platform, "key": key})
    if not keys:
        return None
    if not isinstance(keys, list) or not all(isinstance(k, dict) and k.get("platform") and k.get("key") for k in keys):
        sys.exit('FREELLMAPI_KEYS must look like [{"platform":"groq","key":"gsk_..."}]')
    if not any(k["platform"] == "google" for k in keys):
        print("  note: no Google AI Studio key; the visual judge needs a free Gemini key (see FREE_MODELS.md)")
    return json.dumps(keys)


def youtube(client_secret):
    from google_auth_oauthlib.flow import InstalledAppFlow
    print("\nYouTube: a browser opens. Pick the FlatFrameDocs channel.")
    creds = InstalledAppFlow.from_client_secrets_file(client_secret, YT_SCOPES).run_local_server(
        port=0, prompt="consent", access_type="offline")
    info = json.load(open(client_secret, encoding="utf-8"))
    info = info.get("installed") or info.get("web")
    if not creds.refresh_token:
        sys.exit("Google returned no refresh token. Remove the app at myaccount.google.com/permissions and run again.")
    return {"YT_CLIENT_ID": info["client_id"], "YT_CLIENT_SECRET": info["client_secret"], "YT_REFRESH_TOKEN": creds.refresh_token}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--youtube", metavar="client_secret.json", help="run the YouTube sign-in and store its 3 secrets")
    ap.add_argument("--list", action="store_true", help="only show which secrets are set")
    ap.add_argument("--repo", help="owner/name (default: the repo of this folder)")
    a = ap.parse_args()

    repo = a.repo or gh("repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner").strip()
    have = existing(repo)
    print(f"Repo {repo}")
    for n in NAMES:
        print(f"  {'set    ' if n in have else 'missing'}  {n}")
    if a.list:
        return

    values = {}
    if a.youtube:
        values.update(youtube(a.youtube))
    keys = ask_freellm_keys()
    if keys:
        values["FREELLMAPI_KEYS"] = keys
    print("\nInstagram (Enter skips):")
    for n in ("IG_USER_ID", "IG_PAGE_TOKEN"):
        v = (input if n == "IG_USER_ID" else getpass.getpass)(f"  {n}: ").strip()
        if v:
            values[n] = v

    for n, v in values.items():
        gh("secret", "set", n, "--repo", repo, value=v)
        print(f"  saved {n}")
    left = [n for n in NAMES if n not in have and n not in values]
    print("\nDone." + (f" Still missing: {', '.join(left)}" if left else " All secrets are set."))


if __name__ == "__main__":
    main()
