// Studio settings only (npx remotion studio src/index.ts). Production renders go through scripts/render.mjs.
import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
Config.setConcurrency(4);
Config.setPublicDir("public");
