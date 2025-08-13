import os
import re
import subprocess
from dataclasses import dataclass
from typing import Optional

# Note: This helper only supports downloads for Creative Commons licensed videos.
# It validates license via yt-dlp metadata first and refuses non-CC.

@dataclass
class YouTubeItem:
    url: str
    title: str
    license: str
    view_count: int


def get_latest_cc_viral_video(query: str = "trending") -> Optional[YouTubeItem]:
    """
    Use yt-dlp JSON search to find a Creative Commons video with high views.
    Requires yt-dlp in PATH. Returns None if not found.
    """
    try:
        # Search limited to first 20 items
        cmd = [
            "yt-dlp",
            f"ytsearch20:{query}",
            "--print", "id,title,license,view_count",
            "--skip-download",
        ]
        out = subprocess.check_output(cmd, text=True)
    except Exception:
        return None

    best: Optional[YouTubeItem] = None
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) != 4:
            # yt-dlp sometimes prints one field per line; fallback parse
            parts = re.split(r"[\s\|]", line)
        if len(parts) < 4:
            continue
        vid, title, license_str, views_str = parts[0], parts[1], parts[2], parts[3]
        if not license_str or "creative" not in license_str.lower():
            continue
        try:
            views = int(views_str)
        except Exception:
            views = 0
        url = f"https://www.youtube.com/watch?v={vid}"
        item = YouTubeItem(url=url, title=title, license=license_str, view_count=views)
        if (best is None) or (item.view_count > best.view_count):
            best = item
    return best


def download_cc_video(url: str, out_dir: str) -> Optional[str]:
    """
    Downloads the given YouTube video if and only if yt-dlp reports a CC license.
    Returns path to mp4 or None if refused.
    """
    os.makedirs(out_dir, exist_ok=True)
    # Verify metadata first
    try:
        meta = subprocess.check_output([
            "yt-dlp", url, "--print", "license", "--skip-download"
        ], text=True).strip()
    except Exception:
        return None

    if "creative" not in (meta or "").lower():
        # Not Creative Commons; refuse to download
        return None

    try:
        out = subprocess.check_output([
            "yt-dlp", url, "-f", "mp4", "-o", os.path.join(out_dir, "%(title)s.%(ext)s")
        ], text=True)
    except Exception:
        return None

    # Find the last created mp4 in out_dir
    mp4s = [os.path.join(out_dir, f) for f in os.listdir(out_dir) if f.lower().endswith(".mp4")]
    if not mp4s:
        return None
    mp4s.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return mp4s[0]
