"""QUEUE (the Make job's last step, the only one with a write token): every out/<id>/ready.json becomes a GitHub
Release (final.mp4 + meta + research + QA) and a `queued` history entry. Idempotent: an existing release or history
entry with the same id is never duplicated.

  python -m flatframe.queue
"""
import json

from .common import OUT, load_history, log, read_json, run, save_history

ASSETS = ("final.mp4", "meta.json", "research.json", "qa.json", "sheet.jpg", "storyboard.jpg")


def main():
    history = load_history()
    known = {v["id"] for v in history["videos"]}
    for ready in sorted(OUT.glob("*/ready.json")):
        entry = read_json(ready, None)
        P = ready.parent
        if not entry or entry["id"] in known:
            continue
        meta = json.loads((P / "meta.json").read_text(encoding="utf-8"))
        exists = run(["gh", "release", "view", entry["tag"]], check=False, capture=True).returncode == 0
        if not exists:
            run(["gh", "release", "create", entry["tag"], *[P / a for a in ASSETS if (P / a).exists()],
                 "--title", meta["title"][:100], "--notes", f"{entry['question']}\n\nQA {entry['qa']['score']}; "
                 f"verified claims: {entry['verified_claims']}. Queued for posting."])
        history["videos"].append(entry)
        save_history(history)
        log(f"queued {entry['id']}: {meta['title']}")


if __name__ == "__main__":
    main()
