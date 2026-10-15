#!/usr/bin/env python3
"""Apply WenWen AI branding over this Octop-derived working tree.

Idempotent: safe to re-run any time, including right after
``git fetch upstream && git merge upstream/main``. See BRANDING.md for the
sync workflow.

What it does
------------
1. Copies branding assets (logos, mascots, banners) into place.
2. Adds the monochrome ``openai`` theme palette and makes it the default.
3. Renames user-visible strings: Octop -> WenWen AI, CLI ``octop`` -> ``wenwen``.
4. Renames the Python distribution to ``wenwen-ai`` (the internal ``octop``
   Python package name is intentionally kept for clean upstream merges).

Deliberately NOT renamed (documented in BRANDING.md): the ``src/octop``
Python package, ``~/.octop`` data dir / ``OCTOP_HOME``, ``octop.db``,
localStorage keys, CSS classes, API routes and ``X-Octop-*`` headers.

Usage:
    python scripts/apply-branding.py [--check]

With ``--check`` the script reports what *would* change without writing.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRANDING = ROOT / "branding"
ASSETS = BRANDING / "assets"

DISPLAY = "WenWen AI"
DIST_NAME = "wenwen-ai"
CLI = "wenwen"

check_only = "--check" in sys.argv[1:]
changed: list[str] = []


def note(msg: str) -> None:
    changed.append(msg)
    print(("would " if check_only else "") + msg)


def write(path: Path, content: str) -> bool:
    """Write file if different. Returns True when a change was (or would be) made."""
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    note(f"write {path.relative_to(ROOT)}")
    if not check_only:
        path.write_text(content, encoding="utf-8")
    return True


def sub_file(path: Path, pattern: str, repl: str, count: int = 0) -> int:
    """Regex substitute in a file. Returns number of replacements made."""
    text = path.read_text(encoding="utf-8")
    new, n = re.subn(pattern, repl, text, count=count)
    if n:
        note(f"edit {path.relative_to(ROOT)} ({n}x)")
        if not check_only:
            path.write_text(new, encoding="utf-8")
    return n


# ---------------------------------------------------------------------------
# Prose replacement rules (user-visible text only)
# ---------------------------------------------------------------------------
URL_RE = re.compile(r"(?:https?|postgresql)://[^\s)>\]\"']+")


def prose_rules(text: str) -> str:
    """Apply branding to non-URL segments of text."""
    def apply(seg: str) -> str:
        seg = seg.replace("OctopBot", "WenWen Bot")
        # Never inside TencentCloud/Octop (upstream org/repo) or other /Octop paths
        seg = re.sub(r"(?<![\w/-])Octop(?![\w-])", DISPLAY, seg)
        seg = seg.replace("pip install octop", f"pip install {DIST_NAME}")
        seg = seg.replace("pip install -U octop", f"pip install -U {DIST_NAME}")
        # pip extras: the package is wenwen-ai (not wenwen, not octop)
        seg = seg.replace("octop[browser]", f"{DIST_NAME}[browser]")
        # Bare `octop` CLI/product mentions -> wenwen, but never inside
        # ~/.octop, octop.db, octop-memory, octop-harness, octop-gateway,
        # .octop/, or functional keys like `octop:` (skill metadata)
        seg = re.sub(r"(?<![\w./-])octop(?![\w.:-])", CLI, seg)
        # Upstream sibling projects keep their factual names
        seg = re.sub(r"WenWen AI (Harness|Memory|Gateway|Browser)", r"Octop \1", seg)
        return seg

    out, last = [], 0
    for m in URL_RE.finditer(text):
        out.append(apply(text[last:m.start()]))
        out.append(m.group(0))
        last = m.end()
    out.append(apply(text[last:]))
    return "".join(out)


def prose_file(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    new = prose_rules(text)
    if new != text:
        write(path, new)


def json_values(obj, fn):
    if isinstance(obj, dict):
        return {k: json_values(v, fn) for k, v in obj.items()}
    if isinstance(obj, list):
        return [json_values(v, fn) for v in obj]
    if isinstance(obj, str):
        return fn(obj)
    return obj


def json_file(path: Path, fn) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    new = json_values(data, fn)
    if new != data:
        note(f"edit {path.relative_to(ROOT)} (i18n values)")
        if not check_only:
            path.write_text(json.dumps(new, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Assets
# ---------------------------------------------------------------------------
def apply_assets() -> None:
    copies = [
        ("wenwen-icon-dark.svg", "dashboard/public/logo_vertical_dark.svg"),
        ("wenwen-icon-white.svg", "dashboard/public/logo_vertical_white.svg"),
        ("wenwen-icon-dark.svg", "dashboard/public/favico.svg"),
        ("wenwen-icon-dark.svg", "dashboard/src/assets/channels/wenwen.svg"),
        ("wenwen-icon-dark.svg", "docs/assets/wenwen-logo.svg"),
    ]
    for src, dst in copies:
        s, d = ASSETS / src, ROOT / dst
        if not d.exists() or d.read_bytes() != s.read_bytes():
            note(f"copy {src} -> {dst}")
            if not check_only:
                d.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(s, d)
    # Retire the octopus originals (replaced by wenwen-* files)
    for rel in [
        "dashboard/public/octop-mascot-empty.png",
        "dashboard/public/octop-mascot-tasks.png",
        "dashboard/public/octop-mascot-peek.webp",
        "dashboard/public/octop-mascot-peek.webm",
        "dashboard/public/octop-mascot-type.webp",
        "dashboard/public/octop-mascot-type.webm",
        "desktop/src/assets/octop-mascot-peek.webp",
        "desktop/src/assets/octop-mascot-type.webp",
        "dashboard/src/assets/channels/octop.svg",
        "docs/assets/octop-logo.svg",
        "docs/assets/octop-banner.png",
    ]:
        p = ROOT / rel
        if p.exists() or (p.is_symlink()):
            note(f"remove {rel}")
            if not check_only:
                p.unlink()
    # Render PNGs from SVG masters when node is available (skip in --check mode)
    if check_only:
        return
    render = BRANDING / "tools" / "render-logos.mjs"
    node = shutil.which("node")
    if node and (BRANDING / "tools" / "node_modules").exists():
        try:
            subprocess.run([node, str(render)], cwd=ROOT, check=True,
                           capture_output=True, text=True, timeout=120)
            print("rendered PNGs from SVG masters")
        except Exception as e:  # noqa: BLE001 - best effort
            print(f"warning: logo render failed ({e}); PNGs left as-is")
    else:
        print("warning: node render skipped (run node branding/tools/render-logos.mjs manually)")

    # Desktop loading-page mascots (webp) from the rendered mascot PNG
    mascot_png = ROOT / "dashboard/public/wenwen-mascot-empty.png"
    if mascot_png.exists():
        for rel in ["desktop/src/assets/wenwen-mascot-peek.webp",
                    "desktop/src/assets/wenwen-mascot-type.webp"]:
            dest = ROOT / rel
            try:
                from PIL import Image
                Image.open(mascot_png).save(dest, "WEBP")
                note(f"render {rel}")
            except ImportError:
                print(f"warning: PIL missing, cannot render {rel}")
                break
            except Exception as e:  # noqa: BLE001 - best effort
                print(f"warning: webp render failed for {rel} ({e})")
                break


# ---------------------------------------------------------------------------
# 2. Theme: add the monochrome "openai" palette, make it the default
# ---------------------------------------------------------------------------
OPENAI_TOKENS = """  openai: {
    light: {
      colorPrimary: "#111111",
      colorPrimaryHover: "#2E2E2E",
      colorPrimaryActive: "#000000",
      colorLink: "#111111",
    },
    dark: {
      colorPrimary: "#F5F5F5",
      colorPrimaryBg: "rgba(255, 255, 255, 0.12)",
      colorPrimaryBgHover: "rgba(255, 255, 255, 0.18)",
      colorPrimaryBorder: "rgba(255, 255, 255, 0.25)",
      colorPrimaryBorderHover: "rgba(255, 255, 255, 0.35)",
      colorPrimaryHover: "#FFFFFF",
      colorPrimaryActive: "#E0E0E0",
      colorPrimaryText: "#F5F5F5",
      colorPrimaryTextHover: "#FFFFFF",
      colorPrimaryTextActive: "#E0E0E0",
      colorLink: "#F5F5F5",
    },
  },
"""

OPENAI_CSS = """
/* ---------- OPENAI (monochrome #111111) ---------- */
html[data-palette="openai"]:not([data-theme="dark"]) {
  --fn-bg-hover: rgba(0, 0, 0, 0.04);
  --fn-bg-active: rgba(0, 0, 0, 0.08);
  --fn-bg-selected: rgba(0, 0, 0, 0.06);
  --fn-text-brand: #111111;
  --fn-logo-color: #111111;
  --fn-border-focus: #111111;
  --fn-color-brand: #111111;
  --fn-color-brand-hover: #2e2e2e;
  --fn-color-brand-soft: #2e2e2e;
  --fn-color-brand-bg: rgba(0, 0, 0, 0.06);
  --fn-color-brand-light: #f5f5f5;
  --fn-color-brand-shadow: rgba(0, 0, 0, 0.15);
  --fn-color-brand-glow: rgba(0, 0, 0, 0.08);
  --fn-assistant-bubble-bg-gradient: linear-gradient(
    135deg,
    rgba(245, 245, 245, 0.7) 0%,
    rgba(255, 255, 255, 0.35) 50%,
    rgba(229, 229, 229, 0.45) 100%
  );
  --fn-assistant-bubble-border: rgba(0, 0, 0, 0.12);
  --fn-assistant-glow-color: 0, 0, 0;
  --fn-tag-channel-text: #111111;
  --fn-shadow-brand: 0 4px 14px rgba(0, 0, 0, 0.18);
  --fn-shadow-brand-lg: 0 8px 24px rgba(0, 0, 0, 0.24);
  --fn-row-selected-bg: rgba(0, 0, 0, 0.05);
  --fn-row-selected-hover: rgba(0, 0, 0, 0.09);
  --fn-row-selected-alt-bg: rgba(0, 0, 0, 0.04);
  --fn-row-selected-alt-hover: rgba(0, 0, 0, 0.08);
  --fn-row-selected-border: #111111;
  --fn-sidebar-item-active-bg: #f5f5f5;
  --fn-sidebar-item-active: rgba(0, 0, 0, 0.08);
  --fn-sidebar-item-active-text: #111111;
}

html[data-palette="openai"][data-theme="dark"] {
  --fn-bg-hover: rgba(255, 255, 255, 0.1);
  --fn-bg-active: rgba(255, 255, 255, 0.16);
  --fn-bg-selected: rgba(255, 255, 255, 0.12);
  --fn-text-brand: #f5f5f5;
  --fn-logo-color: #f5f5f5;
  --fn-border-focus: #f5f5f5;
  --fn-color-brand: #f5f5f5;
  --fn-color-brand-hover: #ffffff;
  --fn-color-brand-soft: #ffffff;
  --fn-color-brand-bg: rgba(255, 255, 255, 0.14);
  --fn-color-brand-light: rgba(255, 255, 255, 0.18);
  --fn-color-brand-shadow: rgba(255, 255, 255, 0.28);
  --fn-color-brand-glow: rgba(255, 255, 255, 0.1);
  --fn-assistant-bubble-bg-gradient: linear-gradient(
    135deg,
    rgba(245, 245, 245, 0.12) 0%,
    rgba(255, 255, 255, 0.04) 50%,
    rgba(245, 245, 245, 0.08) 100%
  );
  --fn-assistant-bubble-border: rgba(245, 245, 245, 0.16);
  --fn-assistant-glow-color: 245, 245, 245;
  --fn-tag-channel-text: #f5f5f5;
  --fn-shadow-brand: 0 4px 14px rgba(255, 255, 255, 0.24);
  --fn-shadow-brand-lg: 0 8px 24px rgba(255, 255, 255, 0.32);
  --fn-row-selected-bg: rgba(255, 255, 255, 0.12);
  --fn-row-selected-hover: rgba(255, 255, 255, 0.18);
  --fn-row-selected-alt-bg: rgba(255, 255, 255, 0.1);
  --fn-row-selected-alt-hover: rgba(255, 255, 255, 0.15);
  --fn-row-selected-border: #f5f5f5;
  --fn-sidebar-item-active-bg: rgba(255, 255, 255, 0.16);
  --fn-sidebar-item-active: rgba(255, 255, 255, 0.16);
  --fn-sidebar-item-active-text: #f5f5f5;
}

/* Keep primary controls readable with a white brand in dark mode. */
html[data-palette="openai"][data-theme="dark"] .ant-btn-primary:not(.ant-btn-dangerous),
html[data-palette="openai"][data-theme="dark"] .ant-btn-primary:not(.ant-btn-dangerous):hover,
html[data-palette="openai"][data-theme="dark"] .ant-btn-primary:not(.ant-btn-dangerous):active {
  color: #111111;
}
html[data-palette="openai"][data-theme="dark"] .ant-switch.ant-switch-checked {
  background: #f5f5f5;
}
html[data-palette="openai"][data-theme="dark"] .ant-switch.ant-switch-checked .ant-switch-handle::before {
  background-color: #111111;
}
html[data-palette="openai"][data-theme="dark"] .ant-checkbox-checked .ant-checkbox-inner {
  background-color: #f5f5f5;
  border-color: #f5f5f5;
}
html[data-palette="openai"][data-theme="dark"] .ant-checkbox-checked .ant-checkbox-inner::after {
  border-color: #111111;
}
html[data-palette="openai"][data-theme="dark"] .ant-radio-checked .ant-radio-inner {
  background-color: #f5f5f5;
  border-color: #f5f5f5;
}
html[data-palette="openai"][data-theme="dark"] .ant-radio-checked .ant-radio-inner::after {
  background-color: #111111;
}
"""


def apply_theme() -> None:
    p = ROOT / "dashboard/src/styles/themePalettes.ts"
    text = p.read_text(encoding="utf-8")
    edits = [
        ('export type ThemePalette =\n  | "rose"',
         'export type ThemePalette =\n  | "openai"\n  | "rose"'),
        ('export const VALID_PALETTES: ThemePalette[] = [\n  "rose",',
         'export const VALID_PALETTES: ThemePalette[] = [\n  "openai",\n  "rose",'),
        ('export const DEFAULT_PALETTE: ThemePalette = "rose";',
         'export const DEFAULT_PALETTE: ThemePalette = "openai";'),
        ('export const PALETTE_SWATCH: Record<ThemePalette, string> = {\n  rose: "#E85D75",',
         'export const PALETTE_SWATCH: Record<ThemePalette, string> = {\n  openai: "#111111",\n  rose: "#E85D75",'),
    ]
    for old, new in edits:
        if old in text and new not in text:
            text = text.replace(old, new, 1)
            note("edit dashboard/src/styles/themePalettes.ts (palette registration)")
    if '"openai": {' not in text and "openai: {" not in text:
        anchor = "> = {\n  rose: {"
        if anchor in text:
            text = text.replace(anchor, "> = {\n" + OPENAI_TOKENS + "  rose: {", 1)
            note("edit dashboard/src/styles/themePalettes.ts (openai tokens)")
    write(p, text)

    css = ROOT / "dashboard/src/styles/theme-vars.css"
    ctext = css.read_text(encoding="utf-8")
    if 'data-palette="openai"' not in ctext:
        ctext = ctext.replace(
            'Palettes via html[data-palette="rose|tech|indigo|teal|violet|emerald|amber|slate"]',
            'Palettes via html[data-palette="openai|rose|tech|indigo|teal|violet|emerald|amber|slate"]',
            1,
        )
        if not ctext.endswith("\n"):
            ctext += "\n"
        ctext += OPENAI_CSS
        write(css, ctext)

# ---------------------------------------------------------------------------
# 2b. Fork-owned test updates (upstream tests hardcode the palette set)
# ---------------------------------------------------------------------------
def apply_test_updates() -> None:
    p = ROOT / "dashboard/src/styles/themePalettes.test.ts"
    if p.exists():
        text = p.read_text(encoding="utf-8")
        orig = text
        text = text.replace(
            '    expect(VALID_PALETTES).toEqual([\n      "rose",',
            '    expect(VALID_PALETTES).toEqual([\n      "openai",\n      "rose",',
            1)
        # openai/dark intentionally uses near-white primaries (OpenAI-style);
        # primary controls there render dark text via theme-vars.css overrides.
        old_block = '''  it.each(VALID_PALETTES.filter((palette) => palette !== "rose"))(
    "keeps %s solid Ant Design states readable with white text",
    (palette) => {
      for (const mode of ["light", "dark"] as const) {
        const tokens = ANTD_BRAND_TOKENS[palette][mode];
        for (const color of [
          tokens.colorPrimary,
          tokens.colorPrimaryHover,
          tokens.colorPrimaryActive,
        ]) {
          expect(contrastRatio(color, "#FFFFFF")).toBeGreaterThanOrEqual(4.5);
        }
      }
    },
  );'''
        new_block = '''  it.each(VALID_PALETTES.filter((palette) => palette !== "rose"))(
    "keeps %s solid Ant Design states readable",
    (palette) => {
      for (const mode of ["light", "dark"] as const) {
        const tokens = ANTD_BRAND_TOKENS[palette][mode];
        const foreground =
          palette === "openai" && mode === "dark" ? "#111111" : "#FFFFFF";
        for (const color of [
          tokens.colorPrimary,
          tokens.colorPrimaryHover,
          tokens.colorPrimaryActive,
        ]) {
          expect(contrastRatio(color, foreground)).toBeGreaterThanOrEqual(4.5);
        }
      }
    },
  );'''
        if old_block in text:
            text = text.replace(old_block, new_block, 1)
        if text != orig:
            write(p, text)

    p = ROOT / "dashboard/src/utils/expertColor.test.ts"
    if p.exists():
        text = p.read_text(encoding="utf-8")
        orig = text
        text = text.replace(
            'import { PALETTE_SWATCH } from "../styles/themePalettes";',
            'import {\n  DEFAULT_PALETTE,\n  PALETTE_SWATCH,\n} from "../styles/themePalettes";',
            1)
        text = text.replace(
            '''  it("falls back to rose when color is missing", () => {
    expect(resolveExpertPalette(null)).toBe("rose");
    expect(resolveExpertPalette(undefined)).toBe("rose");
  });''',
            '''  it("falls back to the default palette when color is missing", () => {
    expect(resolveExpertPalette(null)).toBe(DEFAULT_PALETTE);
    expect(resolveExpertPalette(undefined)).toBe(DEFAULT_PALETTE);
  });''',
            1)
        if text != orig:
            write(p, text)

    # Backend: skill display names follow the brand; slugs stay `octop-*`
    p = ROOT / "tests/unit/i18n/test_skills.py"
    if p.exists():
        text = p.read_text(encoding="utf-8")
        orig = text
        text = text.replace('"Octop 助手"', '"WenWen AI 助手"')
        text = text.replace('"Octop Assistant"', '"WenWen AI Assistant"')
        if text != orig:
            write(p, text)

    # CLI tests: command is now `wenwen`, errors say "WenWen AI"
    p = ROOT / "tests/unit/cli/test_version_cmd.py"
    if p.exists():
        text = p.read_text(encoding="utf-8")
        orig = text
        text = text.replace('assert "octop" in result.output.lower()',
                            'assert "wenwen" in result.output.lower()')
        if text != orig:
            write(p, text)
    p = ROOT / "tests/unit/cli/test_stub.py"
    if p.exists():
        text = p.read_text(encoding="utf-8")
        orig = text
        text = text.replace('"Not applicable for Octop"', '"Not applicable for WenWen AI"')
        if text != orig:
            write(p, text)
    p = ROOT / "tests/unit/mobile/test_docker_install.py"
    if p.exists():
        text = p.read_text(encoding="utf-8")
        orig = text
        text = text.replace('"missing from the Octop package"',
                            '"missing from the WenWen AI package"')
        if text != orig:
            write(p, text)

    # Dashboard: display-text assertion follows the brand
    p = ROOT / "dashboard/src/pages/Agent/Memory/ProfileOverview.test.tsx"
    if p.exists():
        text = p.read_text(encoding="utf-8")
        orig = text
        text = text.replace("/Octop 还在了解你/", "/WenWen AI 还在了解你/")
        if text != orig:
            write(p, text)

    # Updater tests follow the fork (GitHub releases, never upstream PyPI).
    # If upstream rewrites these files, --check flags the missing markers.
    fork_test_markers = {
        ROOT / "tests/unit/cli/test_update_cmd.py": [
            "fetch_fork_release",
            "get_wenwen_version",
            "is_source_install",
        ],
        ROOT / "tests/unit/api/test_update_router.py": [
            "fetch_fork_release",
            "release_unreachable",
            "is_source_install",
        ],
        ROOT / "tests/unit/infra/setup/test_self_update.py": [
            "def test_is_newer_wenwen(",
            "def test_run_upgrade_refuses_source_install(",
            "wenwen-ai @ git+https://github.com/",
        ],
    }
    for path, markers in fork_test_markers.items():
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                note(f"{path.relative_to(ROOT)}: missing fork marker {marker!r} — re-apply manually!")


# ---------------------------------------------------------------------------
# 3. Locales (dashboard + backend): palette label + brand strings in values
# ---------------------------------------------------------------------------
def apply_locales() -> None:
    for rel, label in [
        ("dashboard/src/locales/zh.json", "墨黑"),
        ("dashboard/src/locales/en.json", "Mono"),
    ]:
        p = ROOT / rel
        original = json.loads(p.read_text(encoding="utf-8"))
        data = json.loads(p.read_text(encoding="utf-8"))
        palette = data.get("header", {}).get("palette", {})
        if "openai" not in palette:
            new_palette = {"openai": label}
            new_palette.update(palette)
            data["header"]["palette"] = new_palette
        new = json_values(data, prose_rules)
        if new != original:
            note(f"edit {rel} (palette label + brand strings)")
            if not check_only:
                p.write_text(json.dumps(new, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")

    for rel in ["src/octop/i18n/zh.json", "src/octop/i18n/en.json"]:
        json_file(ROOT / rel, prose_rules)


# ---------------------------------------------------------------------------
# 4. Distribution metadata
# ---------------------------------------------------------------------------
def apply_metadata() -> None:
    p = ROOT / "pyproject.toml"
    text = p.read_text(encoding="utf-8")
    orig = text
    text = re.sub(r'^name = "octop"$', f'name = "{DIST_NAME}"', text,
                  count=1, flags=re.M)
    text = re.sub(
        r'^description = ".*"$',
        f'description = "{DISPLAY}: smarter self-hosted AI assistant for multiple users and agents"',
        text, count=1, flags=re.M)
    text = text.replace(
        '[project.scripts]\noctop = "octop.cli.main:cli"',
        f'[project.scripts]\n{CLI} = "octop.cli.main:cli"\noctop = "octop.cli.main:cli"  # legacy alias',
        1)
    if text != orig:
        write(p, text)

    p = ROOT / "dashboard/package.json"
    sub_file(p, r'"name": "octop-dashboard"', f'"name": "{DIST_NAME}-dashboard"')

    p = ROOT / "dashboard/index.html"
    sub_file(p, r"<title>Octop</title>", f"<title>{DISPLAY}</title>")
    sub_file(p, r'content="Octop" />', f'content="{DISPLAY}" />')

    # PWA manifest (install name shown on home screen)
    p = ROOT / "dashboard/public/manifest.json"
    sub_file(p, r'"name": "Octop"', f'"name": "{DISPLAY}"')
    sub_file(p, r'"short_name": "Octop"', f'"short_name": "{DISPLAY}"')

    # PWA offline fallback page
    p = ROOT / "dashboard/public/offline.html"
    if p.exists():
        text = p.read_text(encoding="utf-8")
        orig = text
        text = prose_rules(text)
        if text != orig:
            write(p, text)

    # FastAPI / OpenAPI title
    p = ROOT / "src/octop/api/app.py"
    sub_file(p, r'title="Octop API"', f'title="{DISPLAY} API"')


# ---------------------------------------------------------------------------
# 4b. WenWen AI fork identity: version file + updater package lock
# ---------------------------------------------------------------------------
def _wenwen_repo_slug() -> str:
    """Derive ``owner/repo`` from git origin, fallback to the known fork."""
    try:
        out = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        m = re.search(r"github\.com[/:]([^/]+)/([^/]+?)(?:\.git)?$", out)
        if m:
            return f"{m.group(1)}/{m.group(2)}"
    except Exception:
        pass
    return "tongwei0715/WenWen-AI"


def apply_wenwen_version() -> None:
    """Sync ``src/octop/wenwen_version.py`` from the latest CHANGELOG entry.

    The self-updater compares this full fork version (``<upstream>-wenwen.<N>``)
    against the fork's GitHub releases. Without it the updater cannot tell
    fork releases apart, so this must run on every branding pass.
    """
    m = re.search(
        r"^## \[([0-9][^\]\s]*-wenwen\.\d+)\]",
        (ROOT / "CHANGELOG-WENWEN.md").read_text(encoding="utf-8"),
        flags=re.M,
    )
    if not m:
        note("CHANGELOG-WENWEN.md has no wenwen version header; skipping wenwen_version.py")
        return
    ver, repo = m.group(1), _wenwen_repo_slug()
    content = (
        '"""WenWen AI fork identity.\n'
        '\n'
        'Managed by ``scripts/apply-branding.py`` — do not edit by hand.\n'
        '``WENWEN_VERSION`` is the full fork version (``<upstream>-wenwen.<N>``),\n'
        '``WENWEN_REPO`` is the GitHub repo whose releases the self-updater tracks\n'
        '(override at runtime with the ``WENWEN_REPO`` environment variable).\n'
        '"""\n'
        f'\nWENWEN_VERSION = "{ver}"\nWENWEN_REPO = "{repo}"\n'
    )
    write(ROOT / "src/octop/wenwen_version.py", content)

    # Lock: the self-updater must never reference the upstream PyPI package.
    # If upstream renames/restructures this module, --check will flag it.
    p = ROOT / "src/octop/infra/setup/self_update.py"
    text = p.read_text(encoding="utf-8")
    if '_PACKAGE_NAME = "wenwen-ai"' not in text:
        if check_only:
            note("self_update.py: _PACKAGE_NAME is not wenwen-ai")
        else:
            text = re.sub(
                r'^_PACKAGE_NAME = "[^"]*"$',
                '_PACKAGE_NAME = "wenwen-ai"',
                text, count=1, flags=re.M,
            )
            write(p, text)
            note('self_update.py: _PACKAGE_NAME restored to "wenwen-ai"')
    # The fork-guard helpers must survive upstream merges of this file.
    for marker in (
        "def get_wenwen_version(",
        "def fetch_fork_release(",
        "def is_source_install(",
        "def get_source_dir(",
    ):
        if marker not in text:
            note(f"self_update.py: missing fork guard {marker} — re-apply manually!")


# ---------------------------------------------------------------------------
# 5. Hardcoded UI literals + mascot/component renames (dashboard)
# ---------------------------------------------------------------------------
def _replace_in_ts_strings(text: str) -> str:
    """Replace standalone Octop/octop inside TS string literals only.

    Skips comments, identifiers, import paths, URLs and /Octop paths so
    code semantics never change; only user-visible strings are rebranded.
    """
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            j = n if j == -1 else j
            out.append(text[i:j])
            i = j
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            j = n if j == -1 else j + 2
            out.append(text[i:j])
            i = j
            continue
        if c in "\"'`":
            j = i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == c:
                    break
                j += 1
            j = min(j + 1, n)
            s = text[i:j]
            s = s.replace("cd Octop", "cd WenWen-AI")
            s = s.replace("octop[browser]", "wenwen-ai[browser]")
            s = re.sub(r"(?<![\w/-])Octop(?![\w-])", DISPLAY, s)
            # NOTE: bare `octop` is intentionally NOT replaced here. It is the
            # Ant Design prefixCls, CLI compat alias and module name in code
            # strings; prose_rules() handles the prose cases elsewhere.
            # Upstream sibling projects keep their factual names
            s = re.sub(r"WenWen AI (Harness|Memory|Gateway|Browser)", r"Octop \1", s)
            out.append(s)
            i = j
            continue
        out.append(c)
        i += 1
    return "".join(out)


def apply_dashboard_string_literals() -> None:
    """Sweep every dashboard .ts/.tsx string literal for leftover branding."""
    src = ROOT / "dashboard/src"
    if not src.exists():
        return
    for p in sorted(src.rglob("*.tsx")) + sorted(src.rglob("*.ts")):
        if ".test." in p.name:
            continue
        text = p.read_text(encoding="utf-8")
        new = _replace_in_ts_strings(text)
        if new != text:
            write(p, new)

    # Connector catalog: 4 user-visible description strings (surgical, no reformat)
    p = ROOT / "src/octop/infra/connectors/catalog.json"
    if p.exists():
        text = p.read_text(encoding="utf-8")
        orig = text
        text = text.replace(
            "Use one-click OAuth when Octop has public HTTPS or localhost;",
            "Use one-click OAuth when WenWen AI has public HTTPS or localhost;")
        text = text.replace(
            "Octop and Obsidian must run on the same host,",
            "WenWen AI and Obsidian must run on the same host,")
        text = text.replace(
            "Octop 与 Obsidian 需在同一台主机，",
            "WenWen AI 与 Obsidian 需在同一台主机，")
        text = text.replace(
            "Octop appends /api/v1 when the URL does not already include it",
            "WenWen AI appends /api/v1 when the URL does not already include it")
        if text != orig:
            write(p, text)


def apply_dashboard_literals() -> None:
    repls = [
        ('alt="Octop"', f'alt="{DISPLAY}"'),
        ('aria-label="Octop mascot"', f'aria-label="{DISPLAY} mascot"'),
        ("Octop 的建议", f"{DISPLAY} 的建议"),
        ("将 Octop 安装为 App，随时一键打开。", f"将 {DISPLAY} 安装为 App，随时一键打开。"),
        ("或在 Octop 主机终端手动执行下方命令。", f"或在 {DISPLAY} 主机终端手动执行下方命令。"),
        ("这些草稿由 Octop 从对话中自动提取，正在等待系统规则判断。",
         f"这些草稿由 {DISPLAY} 从对话中自动提取，正在等待系统规则判断。"),
        ("{/* 3. Octop agent install */}", "{/* 3. WenWen AI agent install */}"),
    ]
    for rel in [
        "dashboard/src/layouts/Sidebar.tsx",
        "dashboard/src/pages/Login/index.tsx",
        "dashboard/src/pages/Setup/index.tsx",
        "dashboard/src/pages/Chat/components/WelcomeScreen.tsx",
        "dashboard/src/pages/Agent/Memory/CandidatesReview.tsx",
        "dashboard/src/components/PwaInstallPrompt/index.tsx",
        "dashboard/src/pages/Agent/Connectors/index.tsx",
        "dashboard/src/pages/Admin/Storage/DockerEnvFooter.tsx",
    ]:
        p = ROOT / rel
        if not p.exists():
            continue
        for old, new in repls:
            sub_file(p, re.escape(old), new)

    # Prose-y literals containing "Octop " in tsx (not identifiers)
    for rel in [
        "dashboard/src/pages/Agent/Memory/ProactiveConfig.tsx",
        "dashboard/src/pages/Agent/Memory/ProfileOverview.tsx",
        "dashboard/src/pages/Control/RemoteBrowser/index.tsx",
    ]:
        p = ROOT / rel
        if p.exists():
            text = p.read_text(encoding="utf-8")
            new = re.sub(r"(?<![\w-])Octop(?![\w-])", DISPLAY, text)
            if new != text:
                write(p, new)

    # Mascot asset + constant + component rename
    p = ROOT / "dashboard/src/assets/mascot.ts"
    if p.exists():
        text = p.read_text(encoding="utf-8")
        text = text.replace("OCTOP_EMPTY_MASCOT_SRC", "WENWEN_EMPTY_MASCOT_SRC")
        text = text.replace("/octop-mascot-empty.png", "/wenwen-mascot-empty.png")
        text = text.replace("OctopEmptyMascot", "WenWenEmptyMascot")
        write(p, text)

    old_comp = ROOT / "dashboard/src/components/EmptyState/OctopEmptyMascot.tsx"
    new_comp = ROOT / "dashboard/src/components/EmptyState/WenWenEmptyMascot.tsx"
    if old_comp.exists() and not new_comp.exists():
        note("rename dashboard/src/components/EmptyState/OctopEmptyMascot.tsx -> WenWenEmptyMascot.tsx")
        if not check_only:
            old_comp.rename(new_comp)
    if new_comp.exists():
        text = new_comp.read_text(encoding="utf-8")
        new = text.replace("OctopEmptyMascot", "WenWenEmptyMascot")
        new = new.replace("OCTOP_EMPTY_MASCOT_SRC", "WENWEN_EMPTY_MASCOT_SRC")
        if new != text:
            write(new_comp, new)

    # Update all references across dashboard/src
    for rel in sorted((ROOT / "dashboard/src").rglob("*.tsx")) + \
               sorted((ROOT / "dashboard/src").rglob("*.ts")):
        if rel.name.endswith(".test.tsx") or rel.name.endswith(".test.ts"):
            continue
        text = rel.read_text(encoding="utf-8")
        new = text.replace("OctopEmptyMascot", "WenWenEmptyMascot")
        new = new.replace("OCTOP_EMPTY_MASCOT_SRC", "WENWEN_EMPTY_MASCOT_SRC")
        new = new.replace("../../../../assets/channels/octop.svg",
                          "../../../../assets/channels/wenwen.svg")
        new = re.sub(r"(?<![\w-])octopIcon(?![\w-])", "wenwenIcon", new)
        if new != text:
            write(rel, new)

    # Check for remaining direct references to the retired tasks mascot
    for rel in (ROOT / "dashboard/src").rglob("*"):
        if rel.is_file() and rel.suffix in {".tsx", ".ts"}:
            text = rel.read_text(encoding="utf-8")
            if "octop-mascot-tasks.png" in text:
                new = text.replace("octop-mascot-tasks.png", "wenwen-mascot-tasks.png")
                write(rel, new)

    # Animated typing mascots -> static WenWen mark (used as <img>, no video)
    p = ROOT / "dashboard/src/components/StreamConnectingIndicator/index.tsx"
    if p.exists():
        sub_file(p, r"`\$\{import\.meta\.env\.BASE_URL\}octop-mascot-type\.webp`",
                 "`${import.meta.env.BASE_URL}wenwen-mascot-empty.png`")
    p = ROOT / "dashboard/src/pages/Chat/components/ThinkingBubble.tsx"
    if p.exists():
        sub_file(p, r"`\$\{import\.meta\.env\.BASE_URL\}octop-mascot-type\.webp`",
                 "`${import.meta.env.BASE_URL}wenwen-mascot-empty.png`")
    p = ROOT / "dashboard/src/pages/Chat/components/WelcomeScreen.tsx"
    if p.exists():
        text = p.read_text(encoding="utf-8")
        orig = text
        old_block = '''// Animated WebP keeps alpha on Safari; VP9 WebM alpha is unreliable there.
const MASCOT_PEEK = "/octop-mascot-peek.webp";
const MASCOT_TYPE = "/octop-mascot-type.webp";
const MASCOT_IMAGES = [MASCOT_PEEK, MASCOT_TYPE];

function getRandomMascot(current?: string): string {
  if (MASCOT_IMAGES.length <= 1) return MASCOT_IMAGES[0];
  let next = current;
  // Avoid picking the same image twice in a row.
  while (next === current) {
    next = MASCOT_IMAGES[Math.floor(Math.random() * MASCOT_IMAGES.length)];
  }
  return next as string;
}'''
        if old_block in text:
            text = text.replace(old_block, 'const MASCOT = "/wenwen-mascot-empty.png";', 1)
        text = text.replace("  const [mascotSrc, setMascotSrc] = useState(MASCOT_PEEK);\n", "")
        text = text.replace('''  const handleMascotClick = () => {
    setMascotSrc((prev) => getRandomMascot(prev));
  };

''', "")
        text = text.replace('''              onClick={handleMascotClick}
              role="button"''', '''              role="presentation"''')
        text = text.replace("src={mascotSrc}", "src={MASCOT}")
        text = text.replace('import { useState } from "react";\n', "")
        # leftover keyboard toggle from the peek/type switcher
        text = text.replace('''              role="presentation"
              tabIndex={0}
              title={t("chatWelcome.mascotSwitchHint")}
              aria-label="WenWen AI mascot"
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  handleMascotClick();
                }
              }}
''', '''              role="presentation"
''')
        if text != orig:
            write(p, text)


# ---------------------------------------------------------------------------
# 5b. Desktop app (Wails Go): product name, copy strings, artifact names
# ---------------------------------------------------------------------------
def apply_desktop() -> None:
    p = ROOT / "desktop/src/Taskfile.yml"
    if p.exists():
        sub_file(p, r'APP_NAME: "Octop"', 'APP_NAME: "WenWenAI"')

    p = ROOT / "desktop/src/build/config.yml"
    if p.exists():
        text = p.read_text(encoding="utf-8")
        orig = text
        text = text.replace('companyName: "Octop"', 'companyName: "WenWen AI"')
        text = text.replace('productName: "Octop"', 'productName: "WenWen AI"')
        text = text.replace('productIdentifier: "com.tencent.octop"',
                            'productIdentifier: "com.wenwenai.desktop"')
        text = text.replace('description: "Octop desktop shell"',
                            'description: "WenWen AI desktop shell"')
        text = text.replace('copyright: "(c) 2026, Octop"', 'copyright: "(c) 2026, WenWen AI"')
        if text != orig:
            write(p, text)

    # Go source: user-visible copy (identifiers like startOctop are untouched
    # by the word-boundary rules)
    for rel in sorted((ROOT / "desktop/src").glob("*.go")):
        if rel.name.endswith("_test.go"):
            continue
        prose_file(rel)
        # portable artifact names follow the binary name (no space)
        text = rel.read_text(encoding="utf-8")
        new = text.replace('"Octop-%s.zip"', '"WenWenAI-%s.zip"')
        new = new.replace('"Octop-portable-"', '"WenWenAI-portable-"')
        new = new.replace("Zip root is Octop-<plat>/", "Zip root is WenWenAI-<plat>/")
        if new != text:
            write(rel, new)

    # Portable packaging pipeline (producer side)
    p = ROOT / "desktop/portable/_common.sh"
    if p.exists():
        text = p.read_text(encoding="utf-8")
        orig = text
        text = text.replace("Octop-portable-", "WenWenAI-portable-")
        text = text.replace("Octop-desktop-", "WenWenAI-desktop-")
        text = text.replace("Octop-<plat>/", "WenWenAI-<plat>/")
        text = text.replace("Octop-<kind>-", "WenWenAI-<kind>-")
        if text != orig:
            write(p, text)
    p = ROOT / "desktop/package-release.sh"
    if p.exists():
        text = p.read_text(encoding="utf-8")
        orig = text
        text = text.replace("Octop-portable-", "WenWenAI-portable-")
        text = text.replace("release/Octop-", "release/WenWenAI-")
        if text != orig:
            write(p, text)

    # Desktop tests: expected strings follow the brand
    p = ROOT / "desktop/src/desktop_copy_test.go"
    if p.exists():
        text = p.read_text(encoding="utf-8")
        orig = text
        text = re.sub(r"(?<![\w/-])Octop(?![\w-])", DISPLAY, text)
        if text != orig:
            write(p, text)
    p = ROOT / "desktop/src/download_test.go"
    if p.exists():
        text = p.read_text(encoding="utf-8")
        orig = text
        text = text.replace('"Octop-"+greenPlat()+".zip"', '"WenWenAI-"+greenPlat()+".zip"')
        text = re.sub(r"(?<![\w/-])Octop(?![\w-])", DISPLAY, text)
        if text != orig:
            write(p, text)
    p = ROOT / "desktop/src/process_test.go"
    if p.exists():
        text = p.read_text(encoding="utf-8")
        orig = text
        text = re.sub(r"(?<![\w/-])Octop(?![\w-])", DISPLAY, text)
        if text != orig:
            write(p, text)

    # Desktop CI workflow: artifact names must match what the (rebranded)
    # packaging scripts actually produce, or the workflow fails on
    # if-no-files-found. Upstream uses Octop-*; the fork uses WenWenAI-*.
    p = ROOT / ".github/workflows/octop-desktop.yml"
    if p.exists():
        text = p.read_text(encoding="utf-8")
        orig = text
        text = text.replace("Octop-portable-", "WenWenAI-portable-")
        text = text.replace("Octop-desktop-", "WenWenAI-desktop-")
        text = text.replace("release/Octop-", "release/WenWenAI-")
        text = text.replace("pattern: Octop-*", "pattern: WenWenAI-*")
        text = text.replace("its Octop-* artifacts", "its WenWenAI-* artifacts")
        # Workflow display name on the Actions tab must read WenWen AI.
        # The file name stays octop-desktop.yml (upstream merge compatibility).
        text = text.replace(
            "name: Octop Desktop Package", "name: WenWen AI Desktop Package"
        )
        text = text.replace(
            "name: Build frontend \u2192 src/octop/dashboard",
            "name: Build frontend dashboard",
        )
        if text != orig:
            write(p, text)

    # Portable packaging: the wheel is now wenwen_ai-*.whl (distribution
    # renamed), but the script looked for octop-*.whl and aborted.
    p = ROOT / "desktop/portable/package.sh"
    if p.exists():
        text = p.read_text(encoding="utf-8")
        orig = text
        text = text.replace(
            'whl="$(ls -1 "${wheel_dir}"/octop-*.whl 2>/dev/null | sort | tail -1 || true)"',
            'whl="$(ls -1 "${wheel_dir}"/wenwen_ai-*.whl 2>/dev/null | sort | tail -1 || true)"',
        )
        text = text.replace(
            'echo "[package] failed to build octop-*.whl" >&2',
            'echo "[package] failed to build wenwen_ai-*.whl" >&2',
        )
        text = text.replace(
            'echo "[package] building octop wheel → ${wheel_dir}" >&2',
            'echo "[package] building wenwen-ai wheel → ${wheel_dir}" >&2',
        )
        # Staging dir inside the portable zip follows the brand too.
        text = text.replace('"${GREEN_RELEASE}/Octop-${plat}"', '"${GREEN_RELEASE}/WenWenAI-${plat}"')
        text = text.replace('"Octop-${plat}"', '"WenWenAI-${plat}"')
        text = text.replace("'Octop-${plat}'", "'WenWenAI-${plat}'")
        text = text.replace("#   Octop-<plat>/", "#   WenWenAI-<plat>/")
        text = text.replace(
            "# Public filename is Octop-portable-<plat>-<version>.zip",
            "# Public filename is WenWenAI-portable-<plat>-<version>.zip",
        )
        if text != orig:
            write(p, text)

    # _common.sh: octop_version() must prefer the fork version from
    # wenwen_version.py over pyproject.toml, or portable/desktop artifact
    # filenames lose the -wenwen.N suffix and CI's PORTABLE_ZIP check fails.
    p = ROOT / "desktop/portable/_common.sh"
    if p.exists():
        text = p.read_text(encoding="utf-8")
        orig = text
        upstream_fn = (
            'octop_version() {\n'
            '  sed -nE \'s/^version[[:space:]]*=[[:space:]]*"([^"]+)".*/\\1/p\' \\\n'
            '    "${REPO_ROOT}/pyproject.toml" | head -1\n'
            '}'
        )
        fork_fn = (
            '# WenWen AI fork: prefer the fork version (WENWEN_VERSION in\n'
            '# src/octop/wenwen_version.py, synced from CHANGELOG-WENWEN.md) over the\n'
            '# upstream base version in pyproject.toml, so artifact filenames carry the\n'
            '# full fork version (e.g. 1.0.2b7-wenwen.10).\n'
            'octop_version() {\n'
            '  local fw\n'
            '  fw="$(sed -nE \'s/^WENWEN_VERSION[[:space:]]*=[[:space:]]*"([^"]+)".*/\\1/p\' \\\n'
            '    "${REPO_ROOT}/src/octop/wenwen_version.py" 2>/dev/null | head -1)"\n'
            '  if [[ -n "$fw" ]]; then\n'
            '    echo "$fw"\n'
            '    return 0\n'
            '  fi\n'
            '  sed -nE \'s/^version[[:space:]]*=[[:space:]]*"([^"]+)".*/\\1/p\' \\\n'
            '    "${REPO_ROOT}/pyproject.toml" | head -1\n'
            '}'
        )
        if upstream_fn in text:
            text = text.replace(upstream_fn, fork_fn)
        if text != orig:
            write(p, text)

    # stamp_version.py: four_part_version() must strip the -wenwen.N fork
    # suffix before mapping to Windows X.X.X.X, or Windows packaging fails.
    p = ROOT / "desktop/src/build/stamp_version.py"
    if p.exists():
        text = p.read_text(encoding="utf-8")
        orig = text
        anchor = "def four_part_version(version: str) -> str | None:"
        fork_block = (
            '# WenWen AI fork versions look like 1.0.2b7-wenwen.10: strip the -wenwen.N\n'
            '# local suffix before mapping to Windows X.X.X.X (display strings keep it).\n'
            '_FORK_VERSION_SUFFIX = re.compile(r"-wenwen\\.\\d+$", re.IGNORECASE)\n'
            '\n\n'
        )
        if anchor in text and "_FORK_VERSION_SUFFIX" not in text:
            text = text.replace(anchor, fork_block + anchor, 1)
            text = text.replace(
                '    raw = version.strip()\n    if not raw or raw == "dev":\n        return None\n',
                '    raw = version.strip()\n    if not raw or raw == "dev":\n        return None\n'
                '    raw = _FORK_VERSION_SUFFIX.sub("", raw)\n',
                1,
            )
        if text != orig:
            write(p, text)


# ---------------------------------------------------------------------------
# 6. CLI help texts + docs + install scripts + packaging
# ---------------------------------------------------------------------------
def apply_cli_texts() -> None:
    for rel in sorted((ROOT / "src/octop/cli").rglob("*.py")):
        p = rel
        text = p.read_text(encoding="utf-8")
        new = re.sub(r"(?<![\w./-])octop(?![\w.:-])", CLI, text)
        new = re.sub(r"(?<![\w-])Octop(?![\w-])", DISPLAY, new)
        # importlib.metadata needs the *distribution* name (wenwen-ai), not the CLI name
        new = new.replace('pkg_version("wenwen")', 'pkg_version("wenwen-ai")')
        new = new.replace('_v("wenwen")', '_v("wenwen-ai")')
        if new != text:
            write(p, new)


def restore_upstream_product_names(text: str) -> str:
    """Octop Harness/Memory/Gateway/Browser are separate TencentCloud projects;
    keep their names factual wherever they name the dependency."""
    text = re.sub(r"WenWen AI (Harness|Memory|Gateway|Browser)", r"Octop \1", text)
    # Badge / repo references that still point at the upstream org
    text = text.replace("TencentCloud/WenWen AI", "TencentCloud/Octop")
    return text


def apply_desktop_build_metadata() -> None:
    """Desktop packaging metadata (icons aside): user-visible names/IDs.

    Upstream stamps Octop branding into the installer/exe/.app metadata;
    the fork must read WenWen AI everywhere. Binary assets (appicon.png,
    appicon-macos.png, dmg-background.jpeg) are generated from
    branding/make-desktop-assets.py and are not touched here.
    """
    # Windows exe version resource (stamp_version.py only sets versions).
    p = ROOT / "desktop/src/build/windows/info.json"
    if p.exists():
        text = p.read_text(encoding="utf-8")
        orig = text
        text = text.replace('"CompanyName": "Octop"', '"CompanyName": "WenWen AI"')
        text = text.replace('"FileDescription": "Octop desktop"', '"FileDescription": "WenWen AI desktop"')
        text = text.replace('"ProductName": "Octop"', '"ProductName": "WenWen AI"')
        text = text.replace('"Comments": "Octop desktop shell"', '"Comments": "WenWen AI desktop shell"')
        if text != orig:
            write(p, text)

    # NSIS installer defines.
    p = ROOT / "desktop/src/build/windows/nsis/wails_tools.nsh"
    if p.exists():
        text = p.read_text(encoding="utf-8")
        orig = text
        text = text.replace("for the Octop desktop installer.", "for the WenWen AI desktop installer.")
        text = text.replace('!define INFO_PROJECTNAME "Octop"', '!define INFO_PROJECTNAME "WenWen AI"')
        text = text.replace('!define INFO_COMPANYNAME "Octop"', '!define INFO_COMPANYNAME "WenWen AI"')
        text = text.replace('!define INFO_PRODUCTNAME "Octop"', '!define INFO_PRODUCTNAME "WenWen AI"')
        text = text.replace('"(c) 2026, Octop"', '"(c) 2026, WenWen AI"')
        if text != orig:
            write(p, text)

    p = ROOT / "desktop/src/build/windows/nsis/project.nsi"
    if p.exists():
        text = p.read_text(encoding="utf-8")
        orig = text
        text = text.replace("# Octop desktop NSIS installer.", "# WenWen AI desktop NSIS installer.")
        text = text.replace("Octop.exe project.nsi", "WenWenAI.exe project.nsi")
        if text != orig:
            write(p, text)

    # Windows app manifest identity.
    p = ROOT / "desktop/src/build/windows/wails.exe.manifest"
    if p.exists():
        text = p.read_text(encoding="utf-8")
        orig = text
        text = text.replace('name="com.tencent.octop"', 'name="com.wenwenai.desktop"')
        if text != orig:
            write(p, text)

    # macOS Info.plist (CFBundleExecutable must match the WenWenAI binary or
    # Finder cannot launch the app; the zip name must match what download.go
    # looks for, or the bundled runtime is not found).
    for rel in ["desktop/src/build/darwin/Info.plist", "desktop/src/build/darwin/Info.dev.plist"]:
        p = ROOT / rel
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        orig = text
        text = text.replace("<string>Octop</string>", "<string>WenWen AI</string>", 1)
        text = text.replace("<string>Octop</string>", "<string>WenWenAI</string>", 1)
        text = text.replace("<string>com.tencent.octop</string>", "<string>com.wenwenai.desktop</string>")
        text = text.replace("Octop desktop shell", "WenWen AI desktop shell")
        if text != orig:
            write(p, text)

    # stamp_version.py: manifest regex must match the fork identity.
    p = ROOT / "desktop/src/build/stamp_version.py"
    if p.exists():
        text = p.read_text(encoding="utf-8")
        orig = text
        text = text.replace(r"com\.tencent\.octop", r"com\.wenwenai\.desktop")
        text = text.replace('"""Stamp the Octop version', '"""Stamp the WenWen AI version')
        text = text.replace("octop assemblyIdentity not found", "assemblyIdentity not found")
        if text != orig:
            write(p, text)

    # Portable-zip default names + task summaries across platform Taskfiles.
    for rel, olds in [
        ("desktop/src/build/darwin/Taskfile.yml", ["Octop-portable-darwin-", "Octop-darwin-{{.ARCH}}.zip", "octop-dmg.XXXXXX"]),
        ("desktop/src/build/windows/Taskfile.yml", ["Octop-portable-windows-", "Wraps Octop.exe in an NSIS installer"]),
        ("desktop/src/build/linux/Taskfile.yml", ["Octop-portable-linux-"]),
        ("desktop/src/build/Taskfile.yml", ["octop-iconset.XXXXXX"]),
    ]:
        p = ROOT / rel
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        orig = text
        for o in olds:
            n = (o.replace("Octop-", "WenWenAI-").replace("Octop.exe", "WenWenAI.exe")
                   .replace("octop-", "wenwenai-"))
            text = text.replace(o, n)
        if text != orig:
            write(p, text)


def apply_docs() -> None:
    roots = [ROOT / "README.md", ROOT / "README_CN.md", ROOT / "CONTRIBUTING.md",
             ROOT / "SECURITY.md", ROOT / "docs", ROOT / "desktop",
             ROOT / "docker", ROOT / "fnos", ROOT / "plugins"]
    for base in roots:
        if not base.exists():
            continue
        files = [base] if base.is_file() else [
            f for f in base.rglob("*")
            if f.is_file() and f.suffix in {".md", ".mdx", ".txt", ".rst"}
        ]
        for f in files:
            if "CHANGELOG" in f.name:
                continue  # historical record; leave untouched
            prose_file(f)
    # Standalone intro page: rename once, then rebrand content
    old_intro = ROOT / "docs/octop-introduction.html"
    new_intro = ROOT / "docs/wenwen-introduction.html"
    if old_intro.exists() and not new_intro.exists():
        note("rename docs/octop-introduction.html -> docs/wenwen-introduction.html")
        if not check_only:
            old_intro.rename(new_intro)
    if new_intro.exists():
        text = new_intro.read_text(encoding="utf-8")
        orig = text
        wenwen_svg = (
            '<svg viewBox="0 0 1506 578" fill="none" '
            'xmlns="http://www.w3.org/2000/svg" aria-hidden="true">\n'
            '            <g transform="translate(60,89) scale(0.78125)">\n'
            '              <circle cx="256" cy="82" r="32" fill="#111111"/>\n'
            '              <path d="M104 150 L184 362 L256 206 L328 362 L408 150" '
            'stroke="#111111" stroke-width="62" stroke-linecap="round" '
            'stroke-linejoin="round"/>\n'
            '            </g>\n'
            '            <text x="560" y="345" font-family="Noto Sans, DejaVu Sans, '
            'sans-serif" font-size="150" font-weight="700" letter-spacing="2" '
            'fill="#111111">WenWen AI</text>\n'
            '          </svg>'
        )
        text, n = re.subn(r'<svg viewBox="0 0 1493 440".*?</svg>', wenwen_svg,
                          text, flags=re.DOTALL)
        text = prose_rules(text)
        if text != orig:
            write(new_intro, text)

    # Standalone user guide page: rebrand prose in place
    guide = ROOT / "docs/user-guide.html"
    if guide.exists():
        text = guide.read_text(encoding="utf-8")
        orig = text
        text = prose_rules(text)
        if text != orig:
            write(guide, text)

    # Desktop app loading page: mascot refs + brand prose
    desk = ROOT / "desktop/src/assets/index.html"
    if desk.exists():
        text = desk.read_text(encoding="utf-8")
        orig = text
        text = text.replace("/octop-mascot-peek.webp", "/wenwen-mascot-peek.webp")
        text = text.replace("/octop-mascot-type.webp", "/wenwen-mascot-type.webp")
        text = prose_rules(text)
        if text != orig:
            write(desk, text)

    # Docker image tags (anchored; never inside URLs like postgresql://…)
    for rel in ["docker/docker-compose.yml", "docker/docker_build.sh"]:
        p = ROOT / rel
        if p.exists():
            text = p.read_text(encoding="utf-8")
            orig = text
            text = text.replace("image: octop:", f"image: {DIST_NAME}:")
            text = re.sub(r"(?<![/:])/octop:([a-z0-9._-]+)", f"/{DIST_NAME}:\\1", text)
            text = text.replace("container_name: octop", f"container_name: {DIST_NAME}")
            text = re.sub(r"(?<![\w./:-])octop:(?=[a-z0-9._-])", f"{DIST_NAME}:", text)
            text = prose_rules(text)
            if text != orig:
                write(p, text)


def apply_install_scripts() -> None:
    p = ROOT / "scripts/install.sh"
    if p.exists():
        text = p.read_text(encoding="utf-8")
        # user-visible prose (URL-aware: repo URLs stay intact)
        new = prose_rules(text)
        # add a `wenwen` wrapper next to the `octop` wrapper (idempotent)
        marker = 'WRAPPER_WENWEN_INSTALLED'
        if marker not in new:
            anchor = 'chmod +x "$OCTOP_BIN/octop"'
            addition = (
                'chmod +x "$OCTOP_BIN/octop"\n'
                f'# {marker}: WenWen AI primary CLI name (same entry point)\n'
                'if [ -x "$OCTOP_HOME/venv/bin/wenwen" ]; then\n'
                '  cp "$OCTOP_BIN/octop" "$OCTOP_BIN/wenwen"\n'
                '  sed -i \'s|/venv/bin/octop"|/venv/bin/wenwen"|\' "$OCTOP_BIN/wenwen"\n'
                '  chmod +x "$OCTOP_BIN/wenwen"\n'
                '  info "Wrapper script created: $OCTOP_BIN/wenwen"\n'
                'fi'
            )
            if anchor in new:
                new = new.replace(anchor, addition, 1)
        if new != text:
            write(p, new)
    for rel in ["scripts/install.ps1", "scripts/install.bat", "scripts/install-octop.sh"]:
        p = ROOT / rel
        if p.exists():
            prose_file(p)  # URL-aware: never rewrites repo URLs


def main() -> int:
    os.chdir(ROOT)
    apply_assets()
    apply_theme()
    apply_test_updates()
    apply_locales()
    apply_metadata()
    apply_wenwen_version()
    apply_dashboard_literals()
    apply_dashboard_string_literals()
    apply_desktop()
    apply_desktop_build_metadata()
    apply_cli_texts()
    apply_docs()
    apply_install_scripts()
    print("done." if not check_only else "check done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
