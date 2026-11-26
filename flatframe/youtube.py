"""YouTube Data API calls (the decisions live in yt_guard.py). Adapted from roblox-stories-bot/pipeline/youtube.py.

Secrets: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN (tools/youtube_auth.py prints them once).
Quota use per post run: channels.list (1) + playlistItems.list (1) for reconciliation; videos.insert only when the
guard clears an upload. An insert is attempted ONCE per run; only the resumable transfer of that same upload retries
on 5xx. Errors are classified by yt_guard.classify().
"""
import os
import time

from .common import env, log, run


def _creds():
    if not (env("YT_CLIENT_ID") and env("YT_CLIENT_SECRET") and env("YT_REFRESH_TOKEN")):
        return None
    from google.oauth2.credentials import Credentials
    return Credentials(None, refresh_token=env("YT_REFRESH_TOKEN"), token_uri="https://oauth2.googleapis.com/token",
                       client_id=env("YT_CLIENT_ID"), client_secret=env("YT_CLIENT_SECRET"))


def client():
    from googleapiclient.discovery import build
    creds = _creds()
    if not creds:
        raise RuntimeError("YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN secrets are missing")
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def shorts_title(title):
    title = title[:90]
    return title if "#shorts" in title.lower() else f"{title} #shorts"[:100]


def channel_state(yt, n=25):
    """-> (channel id, [{video_id, title, published_at}]) for the authenticated channel's latest uploads."""
    ch = yt.channels().list(part="id,contentDetails", mine=True).execute()["items"][0]
    pl = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    items = yt.playlistItems().list(part="snippet", playlistId=pl, maxResults=n).execute().get("items", [])
    recent = [{"video_id": it["snippet"]["resourceId"]["videoId"], "title": it["snippet"]["title"],
               "published_at": it["snippet"]["publishedAt"].replace("Z", "+00:00")} for it in items]
    return ch["id"], recent


def upload(yt, video_path, meta, privacy="public"):
    """ONE videos.insert. Returns (video_id, privacyStatus). Raises googleapiclient HttpError on refusal."""
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload
    body = {
        "snippet": {"title": shorts_title(meta["title"]),
                    "description": f"{meta['description']}\n\n{' '.join(meta['hashtags'])}",
                    "tags": [h.lstrip("#") for h in meta["hashtags"]], "categoryId": "27",
                    "defaultLanguage": meta.get("language", "en"), "defaultAudioLanguage": meta.get("language", "en")},
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False,
                   "containsSyntheticMedia": bool(meta.get("synthetic_youtube", False))},
    }
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True))
    resp, errors = None, 0
    while resp is None:
        try:
            _, resp = req.next_chunk()
        except HttpError as e:
            if e.resp.status not in (500, 502, 503, 504) or errors >= 3:
                raise
            errors += 1
            time.sleep(2 ** errors)
            log(f"YouTube transfer hiccup ({e.resp.status}); resuming the same upload", "WARN")
    return resp["id"], resp.get("status", {}).get("privacyStatus", "unknown")


def notify_manual(meta, tag):
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    body = f"""Today's YouTube Short is ready (youtube_mode: manual).

1. Download **final.mp4** from https://github.com/{repo}/releases/tag/{tag}
2. YouTube app -> + -> Upload a video
3. Title and description below; "Altered or synthetic content": **{'Yes' if meta.get('synthetic_youtube') else 'No'}** (stylised animation)

**Title**
```
{shorts_title(meta['title'])}
```
**Description**
```
{meta['description']}

{' '.join(meta['hashtags'])}
```
"""
    run(["gh", "issue", "create", "--title", f"📱 Upload to YouTube: {meta['title'][:60]}", "--body", body], check=False)
