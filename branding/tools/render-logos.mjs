#!/usr/bin/env node
/**
 * Render WenWen AI SVG masters to PNGs via @resvg/resvg-js.
 * Usage: node branding/tools/render-logos.mjs
 * Idempotent: overwrites the same output files every run.
 */
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { Resvg } from "@resvg/resvg-js";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const assets = join(root, "branding", "assets");
const pub = join(root, "dashboard", "public");

/** [srcSvg, destPng, width] */
const jobs = [
  ["wenwen-horizontal-dark.svg", join(pub, "logo_horizontal_dark.png"), 753],
  ["wenwen-horizontal-white.svg", join(pub, "logo_horizontal_white.png"), 753],
  ["wenwen-mascot.svg", join(pub, "wenwen-mascot-empty.png"), 1024],
  ["wenwen-mascot.svg", join(pub, "wenwen-mascot-tasks.png"), 1024],
  ["wenwen-icon-dark.svg", join(root, "docs", "assets", "wenwen-icon-dark.png"), 512],
  ["wenwen-icon-white.svg", join(root, "docs", "assets", "wenwen-icon-white.png"), 512],
  ["wenwen-banner.svg", join(root, "docs", "assets", "readme-banner.png"), 1080],
  ["wenwen-banner-zh.svg", join(root, "docs", "assets", "readme-banner-zh.png"), 1676],
];

mkdirSync(pub, { recursive: true });
for (const [src, dest, width] of jobs) {
  const svg = readFileSync(join(assets, src), "utf8");
  const resvg = new Resvg(svg, {
    fitTo: { mode: "width", value: width },
    font: { loadSystemFonts: true },
  });
  const png = resvg.render().asPng();
  mkdirSync(dirname(dest), { recursive: true });
  writeFileSync(dest, png);
  console.log(`rendered ${dest} (${png.length} bytes)`);
}
