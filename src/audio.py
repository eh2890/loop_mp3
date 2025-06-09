import librosa
import math
from pydub import AudioSegment
import logging
import pathlib
import ffmpeg

from constants import LOOPED_MP3_FILENAME


log = logging.getLogger(__name__)


def loop_audio(
    mp3_filepath: pathlib.Path,
    output_filepath: pathlib.Path,
    *,
    length: int | None = None,
    repetitions: int | None = None,
    beat_offset: int = 0,
) -> None:
    if length and repetitions:
        raise RuntimeError(
            f"Cannot pass non-None values for both arguments {length=} and {repetitions=}"
        )

    if not length and not repetitions:
        raise RuntimeError(
            "Must provide value for one of length and repetitions arguments"
        )

    start_ms, end_ms = _get_start_end_ms(mp3_filepath, beat_offset)

    # compute number of repetitions from length
    if length:
        repetitions = math.floor(length * 1000 / (end_ms - start_ms))

    # Load audio with pydub
    log.info(f"Loading {mp3_filepath}")
    base = AudioSegment.from_mp3(mp3_filepath)

    loop_segment = base[start_ms:end_ms]

    log.info(f"Looping {repetitions=} times")
    looped = loop_segment * repetitions

    looped.export(LOOPED_MP3_FILENAME, format="mp3")

    _remove_xing_header(LOOPED_MP3_FILENAME, output_filepath)
    log.info(f"Looped {mp3_filepath}; wrote reuslt to {output_filepath}")


def _get_start_end_ms(
    mp3_filepath: pathlib.Path, beat_offset: int = 0
) -> tuple[int, int]:
    y, sr = librosa.load(mp3_filepath, sr=None)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    if len(beat_times) < 2:
        raise RuntimeError("Fewer than two beats detected")

    beat_length_ms = 60 / tempo
    start_time = float(beat_times[0])
    end_time = float(beat_times[-1]) + beat_length_ms + (beat_offset * beat_length_ms)

    # convert to milliseconds
    # this is for pydub and indexing
    start_ms = int(start_time * 1000)
    end_ms = int(end_time * 1000)

    log.info(f"Detected start and end ms for {mp3_filepath}: {start_ms=}; {end_ms=}")

    return start_ms, end_ms


def _remove_xing_header(
    mp3_filepath: pathlib.Path, output_filepath: pathlib.Path
) -> None:
    """
    Removes the Xing header
    Without this, the duration of the .mp3 file and other metadata may appear incorrectly
    """
    ffmpeg.input(LOOPED_MP3_FILENAME).output(
        str(output_filepath), c="copy", write_xing=0
    ).global_args("-loglevel", "error").run()
    log.info(
        f"Removed Xing header from {mp3_filepath}; wrote result to {output_filepath}"
    )
