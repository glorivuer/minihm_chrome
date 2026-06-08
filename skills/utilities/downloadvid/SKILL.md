---
name: downloadvid
description: "Download videos from social media platforms (X/Twitter, YouTube, Threads, etc.) using yt-dlp"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [download, video, social-media, x, youtube, threads, yt-dlp]
    triggers: ["@downloadvid", "download video", "下载视频"]
---

# Download Video Skill

Download videos from social media platforms using `yt-dlp`.

## Supported Platforms

- **X/Twitter**: `https://x.com/i/status/...` or `https://twitter.com/i/status/...`
- **YouTube**: `https://youtube.com/watch?v=...` or `https://youtu.be/...`
- **Threads**: `https://www.threads.net/@username/post/...`
- Plus 1000+ other sites supported by yt-dlp

## Usage

When user says `@downloadvid [URL]`, execute the download workflow.

## Workflow

### Step 1: Parse the URL

Extract the video URL from user's message. URL patterns:
- X/Twitter: `https://x.com/i/status/2062652523945836770`
- YouTube: `https://youtube.com/watch?v=VIDEO_ID`
- Threads: `https://www.threads.net/...`
- Any other yt-dlp supported site

### Step 2: Determine Output Directory

Default output directory: `~/Downloads/videos/`

Create if not exists:
```bash
mkdir -p ~/Downloads/videos/
```

### Step 3: Run yt-dlp

Use the following command template:
```bash
cd ~/Downloads/videos/ && yt-dlp -o "%(title)s_%(id)s.%(ext)s" --no-playlist [URL]
```

**Key options:**
- `--no-playlist` — Don't download playlists, single video only
- `-o "%(title)s_%(id)s.%(ext)s"` — Output filename pattern
- `-f "bestvideo+bestaudio/best"` — Best quality (optional, default is good)
- `--cookies-from-browser BROWSER` — Use browser cookies if needed for private videos

### Step 4: Verify & Report

After download:
1. List the downloaded file
2. Report success with file path and any relevant info (title, duration, etc.)

## Error Handling

| Error | Solution |
|-------|----------|
| "yt-dlp not found" | Install: `pip install yt-dlp` or `brew install yt-dlp` |
| "Video unavailable" | Check URL is correct and video is public |
| "Cookie auth required" | Try: `yt-dlp --cookies-from-browser chrome [URL]` |
| "Rate limited" | Add wait or use `--sleep-requests 3` |

## Example

**User input:**
```
@downloadvid https://x.com/i/status/2062652523945836770
```

**Action:**
```bash
mkdir -p ~/Downloads/videos/
cd ~/Downloads/videos/ && yt-dlp -o "%(title)s_%(id)s.%(ext)s" --no-playlist "https://x.com/i/status/2062652523945836770"
```

**Expected output:**
```
Downloaded: twitter_video_2062652523945836770.mp4
Path: /home/remora/Downloads/videos/twitter_video_2062652523945836770.mp4
```

## Install yt-dlp (if needed)

```bash
# via pip
pip install -U yt-dlp

# via brew (macOS)
brew install yt-dlp

# via npm
npm install -g ytdl-core
```

## Quick Reference

```bash
# Basic download
yt-dlp "URL"

# With custom filename
yt-dlp -o "%(title)s.%(ext)s" "URL"

# Best quality
yt-dlp -f "bestvideo+bestaudio/best" "URL"

# Use browser cookies (for private content)
yt-dlp --cookies-from-browser chrome "URL"

# Download subtitle/captions too
yt-dlp --write-subs --write-auto-subs "URL"
```