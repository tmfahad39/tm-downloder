# TM DOWNLODER — terminal video downloader for Termux

An interactive, colorful terminal interface for [yt-dlp](https://github.com/yt-dlp/yt-dlp).
Paste a link, see the video's name, channel, length, views and every available
resolution/size, then pick the quality you want before anything is downloaded.

Works on Termux (Android), Linux and macOS. Supports the 1800+ sites yt-dlp
supports: YouTube, TikTok, Instagram, X/Twitter, Reddit, Facebook, Vimeo,
Twitch, SoundCloud, direct `.mp4`/`.m3u8` links, and more.

## Screens

```
╭──────────────────────────────────────────────────────╮
│ ▼  TM DOWNLODER  /  downloader                       │
│ youtube · tiktok · instagram · x · reddit · more     │
╰──────────────────────────────────────────────────────╯
  ● ready   folder ~/Download/VideoDownloads

╭─ Main menu ──────────────────────────────────────────╮
│ [1]  ▼  Download video + sound                       │
│ [2]  ♪  Download audio                               │
│ [3]  ⚙  Settings                                     │
│ [4]  ▤  Downloaded files                             │
│ [5]  ↻  Update tools                                 │
│ [6]  ✂  Download a time slice                        │
│ [0]  ×  quit                                         │
╰──────────────────────────────────────────────────────╯
  ↑/↓ move   Enter select   Esc quit
```

Use **↑ / ↓** to move the highlight and **Enter** to select. `j`/`k` also work;
typing a number still works when input isn't a terminal.

After pasting a URL:

```
╭─ 1/1 · detected ─────────────────────────────────────╮
│  title    Big Buck Bunny 60fps 4K - Official Blend   │
│  channel  Blender                                    │
│  length   10:35                                      │
│  views    23,560,343                                 │
│  source   Youtube                                    │
╰──────────────────────────────────────────────────────╯

╭─ available formats ──────────────────────────────────╮
│    #  resolution  fps  ext   sound     size  id      │
│    1  3840x2160    60  mp4   no                  ?  628│
│    2  3840x2160    60  webm  no             1299MB  315│
│    5  1920x1080    60  webm  no              161MB  303│
╰──────────────────────────────────────────────────────╯

╭─ choose quality ─────────────────────────────────────╮
│  heights  2160p, 1440p, 1080p, 720p, 480p ...       │
│  0       = best available (auto)                    │
│  720     = cap at 720p                              │
│  a       = audio only                               │
│  f<id>   = exact format id from the table           │
╰──────────────────────────────────────────────────────╯
```

## Install

### Termux

```bash
pkg install -y python ffmpeg git
pip install -U yt-dlp
termux-setup-storage          # allow access to shared storage

git clone https://github.com/tmfahad39/tm-downloder.git
cd tm-downloder

cp tmdownloader.py ~/bin/
echo 'alias down="python3 ~/bin/tmdownloader.py"' >> ~/.bashrc
source ~/.bashrc

down
```

### Linux / macOS

```bash
pip install -U yt-dlp
ffmpeg installed via your package manager (apt / brew / dnf)
python3 tmdownloader.py
```

## Usage

- Paste one URL per line; press Enter on an empty line to continue.
- Pick a **height** (`720`, `1080`, …) to cap resolution, `0` for best available,
  `a` for audio only, `f303` for an exact format id (from the table), or `c` to cancel.
- Multiple URLs and playlists are supported. Playlists are previewed up to 20 entries.
- Ctrl+C is safe: yt-dlp can resume partial files when you run the same link again.

### Downloading only part of a video

**Option 1 — Download video + sound** fetches the details, asks the quality, and
downloads the whole video with its audio. No type or range questions.

**Option 2 — Download audio** shows an audio-quality table instead of the video
resolutions — bitrates like `129k` / `49k`, m4a and mp3 only (no WebM/Opus).
Pick a row to download that exact quality, or `0` for the best available.
No type or range questions. The full video title is shown in the details panel
and used in the saved filename.

Menu 6 (**Download a time slice**) is the only flow that asks for a custom range
such as `0-01:30:00`.

| Range | Meaning |
| --- | --- |
| `0-01:00:00` | first hour |
| `00:30:00-01:00:00` | from 30 min to 1 hour |
| `01:00:00-` | from 1 hour to the end |
| `-01:00:00` | shorthand for the first hour |

You can also opt into a frame-accurate cut (`--force-keyframes-at-cuts`), which
re-encodes the segment and is slower, or use the plain cut which snaps to the
nearest keyframe. Only the selected portion is transferred.

The `vdl` shell script in this repo is a lightweight non-interactive wrapper for
people who prefer one-line commands (`vdl URL`, `vdl -a URL`, `vdl -q 720 URL`).
For a one-off slice without the menu:
`vdl -- --download-sections "*0-01:00:00" URL`.

## Settings

Stored in `~/.config/vdl_ui.json`:

| Key | Meaning |
| --- | --- |
| `dest` | download folder (default: `~/storage/shared/Download/VideoDownloads`) |
| `quality` | saved resolution cap, `0` = best |
| `audio_format` | `mp3`, `m4a`, `opus`, `wav`, `flac` |
| `single` | ignore playlist context of a video URL |
| `cookies` | path to `cookies.txt` for private / age-restricted videos |
| `extra` | extra yt-dlp flags, e.g. `--sleep-requests 1` |

## Notes

- Colors are disabled automatically when output is piped or `NO_COLOR` is set.
- `yt-dlp` changes often; if extraction breaks, run **Update tools** (menu 5).
- For long downloads on Android, use `termux-wake-lock` to prevent doze.
- Only download content you own or have permission to save. Respect each site's
  terms of service and local copyright law.

## License

MIT — see [LICENSE](LICENSE).
