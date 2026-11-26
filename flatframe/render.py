"""RENDER: plan.json -> storyboard stills / muted video (Remotion, engine/scripts/render.mjs) -> final.mp4 with the mix.
Flat SVG sets need no GPU; GitHub's runner Chrome is used when CHROME is set."""
import os

from PIL import Image, ImageDraw

from .common import ENGINE, log, run, write_json


def _node(args, timeout):
    env = dict(os.environ)
    env.pop("GH_TOKEN", None)          # the renderer never needs a GitHub token
    env.pop("GITHUB_TOKEN", None)
    return run(["node", ENGINE / "scripts" / "render.mjs", *args], timeout=timeout, cwd=ENGINE, env=env)


def stills(plan, project_dir, frames, timeout=900):
    write_json(project_dir / "plan.json", plan)
    out = project_dir / "stills"
    _node([project_dir / "plan.json", "--stills", ",".join(str(int(f)) for f in frames), "--outdir", out], timeout)
    return [out / f"f{int(f):05d}.png" for f in frames]


def video(cfg, plan, project_dir):
    rc = cfg["render"]
    write_json(project_dir / "plan.json", plan)
    muted = project_dir / "video.mp4"
    _node([project_dir / "plan.json", "--out", muted, "--concurrency", str(rc["concurrency"]), "--crf", str(rc["crf"])],
          int(rc["timeout_minutes"]) * 60)
    final = project_dir / "final.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-i", muted, "-i", project_dir / "mix.wav", "-map", "0:v:0", "-map", "1:a:0",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", final])
    log(f"final video: {final.stat().st_size / 1e6:.1f} MB")
    return final


def contact_sheet(images, out, cols=5, labels=None, cell=(216, 384)):
    """Grid of frames with optional captions (storyboard review and the judge's input)."""
    rows = -(-len(images) // cols)
    sheet = Image.new("RGB", (cols * cell[0], rows * (cell[1] + 26)), "white")
    d = ImageDraw.Draw(sheet)
    for i, p in enumerate(images):
        im = Image.open(p).convert("RGB").resize(cell)
        x, y = (i % cols) * cell[0], (i // cols) * (cell[1] + 26)
        sheet.paste(im, (x, y))
        if labels:
            d.text((x + 4, y + cell[1] + 4), str(labels[i])[:34], fill=(0, 0, 0))
    sheet.save(out, quality=88)
    return out


def frames_from_video(video, outdir, every=1.0, size="216:384"):
    outdir.mkdir(parents=True, exist_ok=True)
    for old in outdir.glob("q*.jpg"):
        old.unlink()
    run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vf", f"fps={1 / every},scale={size}", outdir / "q%04d.jpg"])
    return sorted(outdir.glob("q*.jpg"))
