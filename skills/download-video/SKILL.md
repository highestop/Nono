---
name: download-video
description: Download video or audio with yt-dlp, including URL resolution, quality selection, and automatic audio/video merging. Use for YouTube, Bilibili, Twitter/X, and other major platforms.
---

## Dependencies

- `yt-dlp`: resolve video URLs and download media
- `ffmpeg`: merge video and audio (required for DASH formats)

Before taking any action, check whether the dependencies are installed (`which yt-dlp && which ffmpeg`). Install any missing dependency with `brew install` without asking the user.

## Workflow

### 1. List video formats

```bash
yt-dlp --list-formats <url>
```

- For HTTP 412 or authentication errors (common on Bilibili), add `--cookies-from-browser chrome`.
- For a short URL (such as b23.tv), first resolve the full URL with `curl -sI -o /dev/null -w "%{redirect_url}" <url>`.

### 2. Show available quality options

Show the results in a table with resolution, frame rate, codec, and estimated size. Indicate which options require a paid membership.

### 3. Download

Download at the quality selected by the user. Use the current working directory by default:

```bash
yt-dlp --cookies-from-browser chrome -f "<video>+<audio>" -o "<output_dir>/%(title)s.%(ext)s" <url>
```

- Prefer a `video+audio` format combination so yt-dlp merges the streams automatically.
- If the video and audio are already combined (as on Twitter), download using a single format ID.
- Use `run_in_background` for large downloads to avoid blocking.

### 4. Merge (only when needed)

Normally, yt-dlp merges the streams automatically when ffmpeg is installed. If an error leaves separate video and audio files, merge them and delete the temporary files without asking the user:

```bash
ffmpeg -i <video_file> -i <audio_file> -c copy <output_file>
rm <video_file> <audio_file>
```

## Notes

- Use the user's current working directory as the default download directory. Follow a different path if the user specifies one.
- If the user only wants a direct video URL, use `yt-dlp -g <url>` without downloading.
- If the user only wants audio, use `yt-dlp -x --audio-format mp3 <url>`.
- High-quality formats on some sites (such as Bilibili) require a logged-in account with a paid membership. If high-quality options are missing from the format list, remind the user to log in.
