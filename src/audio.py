import librosa
import math
import logging
import pathlib
import ffmpeg
import numpy as np
import soundfile as sf
from numpy.typing import NDArray

from filename_constants import (
    LOOPED_MP3_FILENAME,
    TEMPORARY_WAV_FILENAME,
)


_LOOP_SEGMENT_MIN_LENGTH_S = 0.1


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class AudioLoopError(Exception):
    pass


def loop_audio(
    mp3_filepath: pathlib.Path,
    output_filepath: pathlib.Path,
    sampling_rate_hz: int,
    length_s: int | None,
    start_s: int | None,
    end_s: int | None,
    start_offset_beats: int,
    end_offset_beats: int,
    input_shift_beats: int,
    end_truncate_ms: int,
    output_fade_ms: int,
) -> None:
    loop_segment = _get_loop_segment(
        mp3_filepath,
        sampling_rate_hz,
        start_s,
        end_s,
        start_offset_beats,
        end_offset_beats,
        input_shift_beats,
    )

    duration_s = librosa.get_duration(y=loop_segment, sr=sampling_rate_hz)

    # compute number of repetitions from length
    repetitions = 1 if length_s is None else math.floor(length_s / duration_s)

    if duration_s < _LOOP_SEGMENT_MIN_LENGTH_S:
        raise AudioLoopError(f"Loop segment is only {duration_s=}s long")

    end_truncate_s = end_truncate_ms / 1000
    if end_truncate_s >= duration_s:
        raise AudioLoopError(
            "End truncation length {end_truncate_s} exceeds loop segment length {duration_s=}"
        )

    logger.debug(f"Looping {repetitions=} times")
    looped_mp3 = np.tile(loop_segment, repetitions)
    looped_mp3 = looped_mp3[: -_second_to_index(end_truncate_s, sampling_rate_hz)]
    if output_fade_ms:
        fade_samples = _second_to_index(output_fade_ms / 1000, sampling_rate_hz)
        fade_curve = np.linspace(1, 0, fade_samples)
        looped_mp3[-fade_samples:] *= fade_curve

    sf.write(TEMPORARY_WAV_FILENAME, looped_mp3, sampling_rate_hz)
    ffmpeg.input(TEMPORARY_WAV_FILENAME).output(LOOPED_MP3_FILENAME).run(quiet=True)

    _remove_xing_header(LOOPED_MP3_FILENAME, output_filepath)
    logger.debug(f"Looped {mp3_filepath}; wrote result to {output_filepath}")


def _get_loop_segment(
    mp3_filepath: pathlib.Path,
    sampling_rate_hz: int,
    start: int | None,
    end: int | None,
    start_offset_beats: int,
    end_offset_beats: int,
    input_shift_beats: int,
) -> NDArray[np.float32]:
    loop_segment: NDArray[np.float32]
    base_nd_array, sr = librosa.load(mp3_filepath, sr=sampling_rate_hz)
    tempo, beat_frames = librosa.beat.beat_track(y=base_nd_array, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    if len(beat_times) < 2:
        raise AudioLoopError("Fewer than two beats detected")

    duration_s = librosa.get_duration(y=base_nd_array, sr=sr)
    start_time = start if start else 0
    end_time = end if end else duration_s

    beat_length_s = 60 / tempo

    # NOTE: the comparisons do not use a threshold (like for other float comparisons
    # The user has the option to use beat offsets

    start_beat_index = None  # the beat index for the start beat
    end_beat_index = (
        None  # the beat index for the last beat; the entire end beat will be used
    )

    # find the beat right at or after the start
    for i, beat_time in enumerate(beat_times):
        if float(beat_time) >= start_time:
            start_beat_index = i
            break

    # find the beat right at or before the end
    for j, beat_time in enumerate(reversed(beat_times)):
        if float(beat_time) <= end_time:
            end_beat_index = len(beat_times) - j - 1
            break

    if start_beat_index is None:
        raise AudioLoopError(f"Could not find beat at or after {start_time=}")
    if end_beat_index is None:
        raise AudioLoopError(f"Could not find beat at or before {end_time=}")

    start_beat_index += start_offset_beats
    end_beat_index += end_offset_beats

    if end_beat_index < start_beat_index:
        # NOTE: it is acceptable for these to be the same beat as the entire end beat will be used
        raise AudioLoopError("Start beat is after end beat")

    if start_beat_index < 0:
        logger.warning(
            "Start beat is before first beat of original audio, defaulting to first beat"
        )
        start_beat_index = 0

    if len(beat_times) <= start_beat_index:
        raise AudioLoopError("Start beat is after last beat of original audio")

    if end_beat_index < 0:
        raise AudioLoopError("End beat is before first beat of original audio")

    if len(beat_times) <= end_beat_index:
        logger.warning(
            "End beat is after last beat of original audio, defaulting to last beat"
        )
        end_beat_index = len(beat_times) - 1

    logger.debug(
        f"Start beat info: {start_beat_index=}, {beat_times[start_beat_index]=}"
    )
    logger.debug(f"End beat info: {end_beat_index=}, {beat_times[end_beat_index]=}")

    logger.debug(f"Loading {mp3_filepath=}")

    if input_shift_beats:
        logger.debug(f"Applying {input_shift_beats=}")
        # this splits the audio into [start + input_shift_beats, end) and [end, end + input_shift_beats]
        # we need to reorder into [end, end + input_shift_beats) and [start + input_shift_beats, end)
        start_and_shift_s = float(
            beat_times[start_beat_index] + input_shift_beats * beat_length_s
        )
        end_s = float(beat_times[end_beat_index] + beat_length_s)
        end_and_shift_s = float(
            beat_times[end_beat_index]
            + beat_length_s
            + input_shift_beats * beat_length_s
        )  # add extra beat to include entire beat

        if start_and_shift_s < 0:
            raise AudioLoopError(
                f"Out of bounds beat shift: {start_and_shift_s=} is before start of audio"
            )
        if end_s >= duration_s:
            raise AudioLoopError(
                f"Out of bounds beat shift: {end_and_shift_s=} exceeds length of audio {duration_s=}"
            )

        logger.debug(
            f"Stitching together two segments, in s: [{end_s}, {end_and_shift_s}) and [{start_and_shift_s}, {end_s})"
        )
        loop_segment = np.concatenate(
            [
                base_nd_array[
                    _second_to_index(end_s, sampling_rate_hz) : _second_to_index(
                        end_and_shift_s, sampling_rate_hz
                    )
                ],
                base_nd_array[
                    _second_to_index(
                        start_and_shift_s, sampling_rate_hz
                    ) : _second_to_index(end_s, sampling_rate_hz)
                ],
            ]
        )
    else:
        logger.debug("No beat shift applied")
        start_s = float(beat_times[start_beat_index])
        end_s = float(
            beat_times[end_beat_index] + beat_length_s
        )  # add extra beat to include entire beat

        logger.debug(
            f"Detected start and end s for {mp3_filepath}: {start_s=}; {end_s=}"
        )
        loop_segment = base_nd_array[
            _second_to_index(start_s, sampling_rate_hz) : _second_to_index(
                end_s, sampling_rate_hz
            )
        ]
    return loop_segment.astype(np.float32)


def _second_to_index(second: float, sampling_rate_hz: int) -> int:
    return int(sampling_rate_hz * second)


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
    logger.debug(
        f"Removed Xing header from {mp3_filepath}; wrote result to {output_filepath}"
    )
