#!/usr/bin/env python3
"""
TM DOWNLODER - an interactive download interface for yt-dlp (Termux-friendly).

Run it any time with:
    python3 ~/bin/tmdownloader.py

Everything is standard-library Python. It uses the yt-dlp + ffmpeg install
already on this device, and keeps its settings in ~/.config/vdl_ui.json.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

# --------------------------------------------------------------------------- #
# theme - 256-colour UI that degrades cleanly to plain text when piped
# --------------------------------------------------------------------------- #
COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
ANSI = re.compile(r"\x1b\[[0-9;]*m")
W = 56


def paint(text: str, code: int, *, bold: bool = False) -> str:
    if not COLOR:
        return text
    return f"\033[38;5;{code}m" + ("\033[1m" if bold else "") + text + "\033[0m"


def accent(text): return paint(text, 51, bold=True)     # cyan
def pink(text):   return paint(text, 141, bold=True)    # violet
def good(text):   return paint(text, 114)               # green
def warn(text):   return paint(text, 214)               # amber
def bad(text):    return paint(text, 203)               # red
def soft(text):   return paint(text, 245)               # grey


def vlen(text: str) -> int:
    return len(ANSI.sub("", text))


def pad(text: str, width: int) -> str:
    return text + " " * max(0, width - vlen(text))


def short_path(path) -> str:
    text = str(path).replace(str(Path.home()), "~")
    parts = text.split("/")
    return "~/" + "/".join(parts[-2:]) if len(parts) > 3 else text


def top(title: str = "", width: int = W) -> str:
    if not title:
        return "╭" + "─" * (width - 2) + "╮"
    return "╭─ " + title + " " + "─" * max(0, width - vlen(title) - 5) + "╮"


def bottom(width: int = W) -> str:
    return "╰" + "─" * (width - 2) + "╯"


def row(content: str, width: int = W) -> str:
    return "│ " + content + " " * max(0, width - 3 - vlen(content)) + "│"


CONFIG_PATH = Path.home() / ".config" / "vdl_ui.json"
DEFAULT_CONFIG = {
    "dest": str(Path.home() / "storage" / "shared" / "Download" / "VideoDownloads"),
    "quality": 0,          # 0 = best available
    "audio_format": "mp3", # mp3 / m4a / opus / wav / flac
    "single": False,       # True = ignore playlist context of a video URL
    "cookies": "",         # optional path to cookies.txt
    "extra": "",           # optional extra yt-dlp flags
}


# --------------------------------------------------------------------------- #
# config
# --------------------------------------------------------------------------- #
def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    try:
        stored = json.loads(CONFIG_PATH.read_text())
        if isinstance(stored, dict):
            cfg.update({k: v for k, v in stored.items() if k in DEFAULT_CONFIG})
    except (OSError, ValueError):
        pass
    return cfg


def save_config(cfg: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2) + "\n")


# --------------------------------------------------------------------------- #
# tiny terminal helpers
# --------------------------------------------------------------------------- #
def clear() -> None:
    if sys.stdout.isatty():
        os.system("clear")


def ask(prompt: str, default: str = "") -> str:
    suffix = soft(f" [{default}]") if default else ""
    try:
        value = input(f"  {prompt}{suffix} {accent('›')} ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise SystemExit(0)
    return value or default


def menu(title: str, items: list[str], icons: list[str] | None = None) -> int | None:
    icons = icons or ["◆"] * len(items)
    print("\n" + top(pink(title)))
    for i, (icon, item) in enumerate(zip(icons, items), 1):
        print(row(f"[{accent(str(i))}]  {icon}  {item}"))
    exit_label = "quit" if title == "Main menu" else "back"
    print(row(f"[{soft('0')}]  ×  {soft(exit_label)}"))
    print(bottom())
    choice = ask("choice", "0")
    if not choice.isdigit():
        return None
    n = int(choice)
    if n == 0:
        return 0
    if 1 <= n <= len(items):
        return n
    return None


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def banner(cfg: dict) -> None:
    print(top())
    print(row(pink("▼") + "  " + accent("TM DOWNLODER") + soft("  /  downloader")))
    print(row(soft("youtube · tiktok · instagram · x · reddit · more")))
    print(bottom())
    folder = short_path(cfg["dest"])
    quality = f"{cfg['quality']}p" if cfg["quality"] else "best"
    print("  " + good("●") + " ready   " + soft("folder") + " " + folder[:34])
    print("  " + "  " * 1 + soft("quality") + " " + quality +
          "   " + soft("audio") + " " + cfg["audio_format"] + "\n")


# --------------------------------------------------------------------------- #
# core
# --------------------------------------------------------------------------- #
def preflight() -> None:
    missing = []
    if not shutil.which("yt-dlp"):
        missing.append(("yt-dlp", [sys.executable, "-m", "pip", "install", "-U", "yt-dlp"]))
    if not shutil.which("ffmpeg"):
        missing.append(("ffmpeg", ["pkg", "install", "-y", "ffmpeg"]))
    for name, command in missing:
        print("  " + warn(f"! {name} is not installed. Installing now..."))
        result = subprocess.run(command, check=False)
        if result.returncode != 0:
            print(f"  Could not install {name}. Install it manually and try again.")
    print()


def collect_urls() -> list[str]:
    print("Paste one URL per line. Press Enter on an empty line when done.")
    print("(Tip: paste a playlist URL to grab the whole playlist.)")
    urls: list[str] = []
    while True:
        try:
            line = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return urls
        if not line:
            if urls:
                return urls
            print("  (no URLs yet)")
            continue
        if "://" in line or line.startswith("ytsearch"):
            urls.append(line)
            print(f"    added [{len(urls)}]")
        else:
            print("    skipped - that doesn't look like a URL")


def destination(cfg: dict) -> str:
    path = Path(cfg["dest"]).expanduser()
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        fallback = Path.home() / "Downloads"
        fallback.mkdir(parents=True, exist_ok=True)
        cfg["dest"] = str(fallback)
        save_config(cfg)
        print(f"! Could not use {path}; switched to {fallback}")
        return str(fallback)
    return str(path)


def nice_num(value) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "?"


def nice_time(seconds) -> str:
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return "?"
    h, rest = divmod(seconds, 3600)
    m, s = divmod(rest, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def cookie_args(cfg: dict) -> list[str]:
    cookies = Path(cfg["cookies"]).expanduser() if cfg["cookies"] else None
    if cookies and cookies.is_file():
        return ["--cookies", str(cookies)]
    if cookies:
        print(f"! cookies file not found, ignoring: {cookies}")
    return []


def probe_urls(cfg: dict, urls: list[str]) -> list[dict]:
    """Ask yt-dlp for metadata only (no download) so we can show details."""
    infos: list[dict] = []
    for url in urls:
        print(f"\n  fetching details: {url[:70]}")
        cmd = ["yt-dlp", "--dump-json", "--skip-download", "--no-warnings",
               "--playlist-end", "20"] + cookie_args(cfg) + [url]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        except subprocess.TimeoutExpired:
            print("  ! timed out fetching details")
            continue
        except FileNotFoundError:
            print("  ! yt-dlp not found")
            continue

        found = 0
        for line in result.stdout.splitlines():
            try:
                info = json.loads(line)
            except ValueError:
                continue
            if isinstance(info, dict) and info.get("id"):
                info["_source"] = url
                infos.append(info)
                found += 1
        if not found:
            errs = [e.strip() for e in result.stderr.splitlines() if e.strip()]
            print("  ! no details returned" + (f": {errs[-1][:150]}" if errs else ""))
        else:
            print(f"    got {found} item(s)")
    return infos


def video_formats(info: dict) -> list[dict]:
    """One row per distinct resolution/fps/ext, best bitrate wins."""
    grouped: dict[tuple, dict] = {}
    for f in info.get("formats") or []:
        height = f.get("height")
        vcodec = f.get("vcodec")
        if not height or vcodec in (None, "none"):
            continue
        width = f.get("width") or 0
        fps = f.get("fps") or 0
        ext = f.get("ext") or "?"
        has_audio = f.get("acodec") not in (None, "none")
        tbr = f.get("tbr") or 0
        key = (height, round(fps), ext, has_audio)
        row = {
            "id": str(f.get("format_id") or f.get("id") or "?"),
            "height": height,
            "label": f"{width}x{height}" if width else f"{height}p",
            "fps": round(fps),
            "ext": ext,
            "audio": has_audio,
            "codec": vcodec,
            "size": f.get("filesize") or f.get("filesize_approx") or 0,
            "tbr": tbr,
        }
        if key not in grouped or row["tbr"] > grouped[key]["tbr"]:
            grouped[key] = row
    return sorted(grouped.values(), key=lambda r: (-r["height"], -r["fps"], r["ext"]))


def kv(label: str, value) -> None:
    print(row(soft(f" {label:<8}") + " " + str(value)[:40]))


def show_details(info: dict, index: int, total: int) -> None:
    print("\n" + top(pink(f"{index}/{total} · detected")))
    kv("title", accent((info.get("title") or "?")[:42]))
    kv("channel", info.get("uploader") or info.get("channel") or "?")
    kv("length", good(nice_time(info.get("duration"))))
    kv("views", nice_num(info.get("view_count")))
    kv("source", info.get("extractor_key") or info.get("extractor") or "?")
    about = " ".join((info.get("description") or "").split())[:42]
    if about:
        kv("about", soft(about))
    print(bottom())

    rows = video_formats(info)
    if not rows:
        print("  " + warn("no video formats reported"))
        return
    print("\n  " + top(pink("available formats")))
    head = soft(f"  {'#':>2}  {'resolution':<11} {'fps':>3}  {'ext':<5} {'sound':<5} {'size':>8}  id")
    print(row(head))
    for i, r in enumerate(rows[:14], 1):
        size = f"{r['size'] / 1048576:.0f}MB" if r["size"] else "?"
        sound = good("yes") if r["audio"] else soft("no")
        line = (f"  {accent(f'{i:>2}')}  {r['label']:<11} {r['fps']:>3}  "
                f"{r['ext']:<5} {pad(sound, 12)} {size:>8}  {soft(r['id'])}")
        print(row(line))
    if len(rows) > 14:
        print(row(soft(f"  … {len(rows) - 14} more resolutions available")))
    print(bottom())


def choose_quality(cfg: dict, infos: list[dict], prefer_audio: bool = False):
    """Return (mode, format_override, effective_config) or None if cancelled."""
    video_audio = {
        str(f.get("format_id") or f.get("id")): f.get("acodec") not in (None, "none")
        for info in infos for f in (info.get("formats") or [])
        if f.get("format_id") or f.get("id")
    }
    heights = sorted({r["height"] for info in infos for r in video_formats(info)},
                     reverse=True)
    print("\n" + top(pink("choose quality")))
    print(row(soft(" heights  ") + ", ".join(str(h) + "p" for h in heights[:10])))
    print(row(f"  {accent('0')}  = best available (auto)"))
    if heights:
        print(row(f"  {accent(str(heights[0]))}  = highest listed, or any height"))
    print(row(f"  {good('a')}  = audio only"))
    print(row(f"  {pink('f<id>')}  = exact format id from the table"))
    print(row(f"  {soft('c')}  = cancel"))
    print(bottom())
    choice = ask("quality", "a" if prefer_audio else "0").strip().lower()

    if choice in ("c", "cancel"):
        return None
    if choice in ("a", "audio"):
        return "audio", None, cfg
    if choice.startswith("f") and choice[1:] in video_audio:
        fid = choice[1:]
        return "video", (fid if video_audio[fid] else fid + "+ba"), cfg
    if choice.isdigit():
        effective = dict(cfg)
        effective["quality"] = int(choice)
        return "video", None, effective
    print("! unknown choice, using best available")
    return "video", None, cfg


def build_command(cfg: dict, mode: str, urls: list[str],
                  fmt_override: str | None = None) -> list[str]:
    args = ["yt-dlp", "--paths", destination(cfg)]

    if mode == "audio":
        args += ["-f", "ba/b", "-x", "--audio-format", cfg["audio_format"],
                 "--audio-quality", "0"]
        template = "%(uploader,channel|Unknown)s - %(title).100s.%(ext)s"
    else:
        if fmt_override:
            args += ["-f", fmt_override]
        else:
            q = str(cfg["quality"])
            if q.isdigit() and int(q) > 0:
                cap = int(q)
                args += ["-f", f"bv*[height<={cap}]+ba/b[height<={cap}]/bv*+ba/b"]
            else:
                args += ["-f", "bv*+ba/b"]
        template = "%(title).100s [%(id)s].%(ext)s"

    args += ["-o", template]
    if cfg["single"]:
        args += ["--no-playlist"]

    cookies = Path(cfg["cookies"]).expanduser() if cfg["cookies"] else None
    if cookies and cookies.is_file():
        args += ["--cookies", str(cookies)]
    elif cookies:
        print(f"! cookies file not found, ignoring: {cookies}")

    if cfg["extra"].strip():
        args += shlex.split(cfg["extra"])
    return args + urls


def do_download(cfg: dict, prefer_audio: bool = False) -> None:
    urls = collect_urls()
    if not urls:
        return

    print("\n  " + pink("◌") + " fetching metadata (nothing downloaded yet)...")
    infos = probe_urls(cfg, urls)
    if not infos:
        print("! could not read any details; downloading with defaults instead")
    else:
        for i, info in enumerate(infos, 1):
            show_details(info, i, len(infos))

    picked = choose_quality(cfg, infos, prefer_audio)
    if picked is None:
        print("cancelled")
        return
    mode, fmt_override, effective_cfg = picked

    print("\n" + top(pink("ready to download")))
    mode_text = "audio → " + effective_cfg["audio_format"] if mode == "audio" else "video + audio (mp4)"
    print(row(soft(" mode    ") + accent(mode_text)))
    if mode == "video":
        detail = fmt_override if fmt_override else (
            f"{effective_cfg['quality']}p cap" if effective_cfg["quality"] else "best available")
        print(row(soft(" quality ") + good(detail)))
    print(row(soft(" save to ") + short_path(effective_cfg["dest"])))
    print(row(soft(" items   ") + str(len(urls))))
    print(bottom())

    if ask("Start download?", "y").lower() not in ("y", "yes"):
        print("cancelled")
        return

    cmd = build_command(effective_cfg, mode, urls, fmt_override)
    try:
        result = subprocess.run(cmd, check=False)
        print("\n  " + (good("✓ finished") if result.returncode == 0
                         else bad(f"✗ yt-dlp exited with {result.returncode}")))
    except KeyboardInterrupt:
        print("\n! interrupted — partial files can be resumed by running again")
    except FileNotFoundError:
        print("! yt-dlp not found — run preflight or 'pip install -U yt-dlp'")
    ask("Press Enter to continue")


def show_files(cfg: dict) -> None:
    path = Path(destination(cfg))
    files = sorted((p for p in path.iterdir() if p.is_file()),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    print("\n" + top(pink(f"{len(files)} file(s)")))
    if not files:
        print(row(soft("nothing downloaded yet")))
    else:
        for f in files[:15]:
            print(row(good(f"{human_size(f.stat().st_size):>9}") + "  " + f.name[:38]))
        if len(files) > 15:
            print(row(soft(f"… and {len(files) - 15} more")))
    print(bottom())
    print("\n  " + accent("[1]") + " open folder   " + accent("[2]") +
          " delete a file   " + soft("[0]") + " back")
    choice = ask("choice", "0")
    if choice == "1":
        if shutil.which("termux-open"):
            subprocess.run(["termux-open", str(path)], check=False)
        else:
            print(f"  open this path in a file manager: {path}")
    elif choice == "2":
        name = ask("exact file name to delete (blank = cancel)")
        if name:
            target = path / name
            if target.is_file():
                target.unlink()
                print("deleted")
            else:
                print("file not found")
    ask("Press Enter to continue")


def settings(cfg: dict) -> None:
    while True:
        print("\n" + top(pink("settings")))
        print(row(f" {accent('1')}  folder   " + short_path(cfg["dest"])))
        q = f"{cfg['quality']}p" if cfg["quality"] else "best available"
        print(row(f" {accent('2')}  video    " + q))
        print(row(f" {accent('3')}  audio    " + cfg["audio_format"]))
        single = "yes" if cfg["single"] else "no (full playlists)"
        print(row(f" {accent('4')}  single   " + single))
        print(row(f" {accent('5')}  cookies  " + (cfg["cookies"] or soft("none"))))
        print(row(f" {accent('6')}  extra    " + (cfg["extra"] or soft("none"))))
        print(row(f" {soft('0')}  back"))
        print(bottom())
        choice = ask("choice", "0")

        if choice == "1":
            cfg["dest"] = ask("new folder", cfg["dest"])
        elif choice == "2":
            value = ask("max height in px, 0 = best", str(cfg["quality"]))
            cfg["quality"] = int(value) if value.isdigit() else 0
        elif choice == "3":
            value = ask("audio format (mp3/m4a/opus/wav/flac)", cfg["audio_format"])
            cfg["audio_format"] = value.lower() or "mp3"
        elif choice == "4":
            cfg["single"] = ask("single item even in a playlist? (y/n)",
                                "y" if cfg["single"] else "n").lower() in ("y", "yes")
        elif choice == "5":
            cfg["cookies"] = ask("path to cookies.txt (blank = none)", cfg["cookies"])
        elif choice == "6":
            cfg["extra"] = ask("extra flags e.g. --sleep-requests 1", cfg["extra"])
        elif choice == "0":
            break
        else:
            print("invalid choice")
            continue
        save_config(cfg)
        print("saved")


def update_tools() -> None:
    print("\n  " + pink("↻") + " updating yt-dlp...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"], check=False)
    print("  " + pink("↻") + " updating ffmpeg...")
    subprocess.run(["pkg", "upgrade", "-y", "ffmpeg"], check=False)
    ask("Press Enter to continue")


# --------------------------------------------------------------------------- #
# entry point
# --------------------------------------------------------------------------- #
def main() -> None:
    cfg = load_config()
    preflight()
    while True:
        clear()
        banner(cfg)
        choice = menu("Main menu", [
            "Download video",
            "Download audio",
            "Settings",
            "Downloaded files",
            "Update tools",
        ], icons=[pink("▼"), good("♪"), soft("⚙"), accent("▤"), warn("↻")])
        if choice == 0:
            if ask("Quit?", "y").lower() in ("y", "yes"):
                break
            continue
        if choice is None:
            print("invalid choice")
            ask("Press Enter to continue")
            continue
        try:
            if choice == 1:
                do_download(cfg, prefer_audio=False)
            elif choice == 2:
                do_download(cfg, prefer_audio=True)
            elif choice == 3:
                settings(cfg)
            elif choice == 4:
                show_files(cfg)
            elif choice == 5:
                update_tools()
        except SystemExit:
            raise


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nbye")
