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
    sampling_rate: int,
    maximum_length: int | None,
    start: int | None,
    end: int | None,
    start_beat_offset: int,
    end_beat_offset: int,
    beat_shift: int,
) -> None:
    loop_segment = _get_loop_segment(
        mp3_filepath,
        sampling_rate,
        start,
        end,
        start_beat_offset,
        end_beat_offset,
        beat_shift,
    )

    duration_s = librosa.get_duration(y=loop_segment, sr=sampling_rate)

    # compute number of repetitions from maximum_length
    repetitions = (
        1 if maximum_length is None else math.floor(maximum_length / duration_s)
    )

    if duration_s < _LOOP_SEGMENT_MIN_LENGTH_S:
        raise AudioLoopError(f"Loop segment is only {duration_s=}s long")

    logger.debug(f"Looping {repetitions=} times")
    looped_mp3 = np.tile(loop_segment, repetitions)

    sf.write(TEMPORARY_WAV_FILENAME, looped_mp3, sampling_rate)
    ffmpeg.input(TEMPORARY_WAV_FILENAME).output(LOOPED_MP3_FILENAME).run(quiet=True)

    _remove_xing_header(LOOPED_MP3_FILENAME, output_filepath)
    logger.debug(f"Looped {mp3_filepath}; wrote result to {output_filepath}")


def _get_loop_segment(
    mp3_filepath: pathlib.Path,
    sampling_rate: int,
    start: int | None,
    end: int | None,
    start_beat_offset: int,
    end_beat_offset: int,
    beat_shift: int,
) -> NDArray[np.float32]:
    loop_segment: NDArray[np.float32]
    base_nd_array, sr = librosa.load(mp3_filepath, sr=sampling_rate)
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

    start_beat_index += start_beat_offset
    end_beat_index += end_beat_offset

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

    if beat_shift:
        logger.debug(f"Applying {beat_shift=}")
        # this splits the audio into [start + beat_shift, end) and [end, end + beat_shift]
        # we need to reorder into [end, end + beat_shift) and [start + beat_shift, end)
        start_and_shift_s = float(
            beat_times[start_beat_index] + beat_shift * beat_length_s
        )
        end_s = float(beat_times[end_beat_index] + beat_length_s)
        end_and_shift_s = float(
            beat_times[end_beat_index] + beat_length_s + beat_shift * beat_length_s
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
                    _second_to_index(end_s, sampling_rate) : _second_to_index(
                        end_and_shift_s, sampling_rate
                    )
                ],
                base_nd_array[
                    _second_to_index(
                        start_and_shift_s, sampling_rate
                    ) : _second_to_index(end_s, sampling_rate)
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
            _second_to_index(start_s, sampling_rate) : _second_to_index(
                end_s, sampling_rate
            )
        ]
    return loop_segment.astype(np.float32)


def _second_to_index(second: float, sampling_rate: int) -> int:
    return int(sampling_rate * second)


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
