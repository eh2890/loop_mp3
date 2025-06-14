import pytest
from unittest.mock import patch, MagicMock

from youtube_downloader import download_youtube


@pytest.mark.parametrize(
    "input_filename, expected_outtmpl",
    [
        ("song.mp3", "song"),
        ("video_audio", "video_audio"),
    ],
)
@patch("youtube_downloader.yt_dlp.YoutubeDL")
def test_download_youtube(
    mock_yt_dl_class: MagicMock, input_filename: str, expected_outtmpl: str
) -> None:
    mock_ydl_instance = MagicMock()
    mock_yt_dl_class.return_value.__enter__.return_value = mock_ydl_instance

    test_url = "https://youtube.com/fakevideo"

    download_youtube(test_url, input_filename)

    # Check that YoutubeDL was instantiated with correct outtmpl
    called_opts = mock_yt_dl_class.call_args[0][0]
    assert called_opts["outtmpl"] == expected_outtmpl

    # Check that download() was called with correct URL
    mock_ydl_instance.download.assert_called_once_with(test_url)
