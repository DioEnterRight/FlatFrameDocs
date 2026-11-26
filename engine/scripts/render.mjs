#!/usr/bin/env node
/**
 * Render a FlatFrameDocs plan with the Remotion Node API (flat SVG sets: no GPU needed).
 *
 *   node scripts/render.mjs <plan.json> --out video.mp4 [--concurrency 4] [--crf 18]   muted H.264 1080x1920 30 fps
 *   node scripts/render.mjs <plan.json> --stills 0,45,90 --outdir stills/                PNG storyboard stills
 *
 * Audio is mixed and muxed afterwards by flatframe/render.py (the skill: render muted, add the voice at the end).
 * CHROME=/path/to/chrome uses an installed browser instead of downloading Remotion's headless shell.
 */
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { bundle } from "@remotion/bundler";
import { renderMedia, renderStill, selectComposition } from "@remotion/renderer";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const args = process.argv.slice(2);
const opt = (name, def) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 ? args[i + 1] : def;
};
const planPath = args[0];
if (!planPath || !fs.existsSync(planPath)) {
  console.error("usage: render.mjs <plan.json> --out file.mp4 | --stills 0,30 --outdir dir");
  process.exit(2);
}
const plan = JSON.parse(fs.readFileSync(planPath, "utf8"));
const browserExecutable = process.env.CHROME || null;
const t0 = Date.now();
const serveUrl = await bundle({ entryPoint: path.join(ROOT, "src", "index.ts"), webpackOverride: (c) => c });
const inputProps = { plan };
const composition = await selectComposition({ serveUrl, id: "Doc", inputProps, browserExecutable });
console.log(`bundled in ${((Date.now() - t0) / 1000).toFixed(1)}s; ${composition.durationInFrames} frames`);

const stills = opt("stills", null);
if (stills) {
  const outdir = opt("outdir", "stills");
  fs.mkdirSync(outdir, { recursive: true });
  for (const fr of stills.split(",").map(Number)) {
    const output = path.join(outdir, `f${String(fr).padStart(5, "0")}.png`);
    await renderStill({ composition, serveUrl, inputProps, frame: fr, output, browserExecutable, timeoutInMilliseconds: 120000 });
  }
  console.log(`stills done in ${((Date.now() - t0) / 1000).toFixed(1)}s`);
} else {
  const out = opt("out", "video.mp4");
  let last = -1;
  await renderMedia({
    composition, serveUrl, inputProps, codec: "h264", outputLocation: out, muted: true,
    crf: Number(opt("crf", "18")), concurrency: Math.min(Number(opt("concurrency", "4")), os.cpus().length), imageFormat: "jpeg", jpegQuality: 92,
    pixelFormat: "yuv420p", browserExecutable, timeoutInMilliseconds: 180000,
    onProgress: ({ progress }) => {
      const p = Math.floor(progress * 10);
      if (p !== last) { last = p; console.log(`render ${p * 10}% (${((Date.now() - t0) / 1000).toFixed(0)}s)`); }
    },
  });
  console.log(`video done in ${((Date.now() - t0) / 1000).toFixed(1)}s -> ${out}`);
}
