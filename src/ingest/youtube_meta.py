from dataclasses import dataclass
from typing import Optional
import subprocess
import json

@dataclass
class VideoMeta:
    url: str
    title: Optional[str]
    license: Optional[str]


def get_youtube_meta(url: str) -> Optional[VideoMeta]:
    try:
        out = subprocess.check_output([
            "yt-dlp", url, "--dump-json", "--skip-download"
        ], text=True)
        data = json.loads(out)
        return VideoMeta(
            url=url,
            title=data.get("title"),
            license=data.get("license"),
        )
    except Exception:
        return None
