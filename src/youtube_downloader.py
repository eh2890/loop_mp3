import yt_dlp
import logging
from filename_constants import MP3_FILE_EXTENSION


logger = logging.getLogger(__name__)


def download_youtube(url: str, filename: str) -> None:
    """
    Downloads YouTube URL as .mp3 file
    Returns path to downloaded file
    """

    if filename.endswith(MP3_FILE_EXTENSION):
        filename = filename[: -len(MP3_FILE_EXTENSION)]

    yt_opts = {
        "format": "bestaudio/best",
        "outtmpl": filename,
        "audio_format": "mp3",
        "logger": logger,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    with yt_dlp.YoutubeDL(yt_opts) as ydl:
        ydl.download(url)
