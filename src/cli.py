import argparse
import pathlib
import logging
import tempfile
import os
import shutil

from youtube_downloader import download_youtube
from filename_constants import (
    BASE_MP3_FILENAME,
    DEFAULT_OUTPUT_MP3_FILENAME,
)
from audio import loop_audio
from utils.directory_utils import PushDir
from utils.timestamp_to_seconds_converter import TimestampToSecondsConverter


logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="loop_mp3",
        description="CLI for downloading and looping .mp3 files",
    )
    # input group
    input_group = parser.add_argument_group("Input", "Source of input .mp3 file")
    mutually_exclusive_input_group = input_group.add_mutually_exclusive_group(
        required=True
    )
    mutually_exclusive_input_group.add_argument(
        "--youtube", "-y", type=str, help="YouTube link"
    )
    mutually_exclusive_input_group.add_argument(
        "--input-filepath", "-i", type=str, help="Filepath to .mp3 file"
    )
    # input splicing options
    input_splicing_group = parser.add_argument_group(
        "Input splicing", "Adjust the start/end of input .mp3 file"
    )
    input_splicing_group.add_argument(
        "--start",
        type=TimestampToSecondsConverter.convert_timestamp_to_seconds,
        help=f"Start timestamp; formats: {TimestampToSecondsConverter.SUPPORTED_TIMESTAMP_FORMATS}",
    )
    input_splicing_group.add_argument(
        "--end",
        type=TimestampToSecondsConverter.convert_timestamp_to_seconds,
        help=f"End timestamp; formats: {TimestampToSecondsConverter.SUPPORTED_TIMESTAMP_FORMATS}",
    )
    input_splicing_group.add_argument(
        "--start-offset",
        type=int,
        help="Offset, in beats, from the start time",
        default=0,
    )
    input_splicing_group.add_argument(
        "--end-offset",
        type=int,
        help="Offset, in beats, from the end time",
        default=0,
    )
    input_splicing_group.add_argument(
        "--input-shift",
        type=int,
        help="Beat shift, must be non-negative",
        default=0,
    )
    input_splicing_group.add_argument(
        "--sampling-rate",
        type=int,
        help="Sampling rate; defaults to librosa's default of 22050hz",
        default=22050,
    )
    # output length group
    output_group = parser.add_argument_group("Output", "Parameters for output file")
    output_group.add_argument(
        "--length",
        "-l",
        type=TimestampToSecondsConverter.convert_timestamp_to_seconds,
        help=f"Maximum length of output as a timestamp; formats: {TimestampToSecondsConverter.SUPPORTED_TIMESTAMP_FORMATS}",
    )
    output_group.add_argument(
        "--output-filepath",
        "-o",
        type=str,
        help=f"Name of output file; defaults to {DEFAULT_OUTPUT_MP3_FILENAME}",
        default=DEFAULT_OUTPUT_MP3_FILENAME,
    )
    output_group.add_argument(
        "--end-truncate",
        type=int,
        help="Length to truncate the end of the output file, in milliseconds",
        default=0,
    )
    output_group.add_argument(
        "--output-fade",
        type=int,
        help="Length of output fade, in milliseconds; applied after truncation",
        default=0,
    )

    args = parser.parse_args()
    output_filepath = pathlib.Path(args.output_filepath).resolve()
    if args.input_shift < 0:
        raise argparse.ArgumentTypeError(
            f"Input shift {args.input_shift=} is an invalid negative value"
        )
    if args.end_truncate < 0:
        raise argparse.ArgumentTypeError(
            f"End truncation length {args.end_truncate=} is an invalid negative value"
        )
    if args.output_fade < 0:
        raise argparse.ArgumentTypeError(
            f"Output fade {args.output_fade=} is an invalid negative value"
        )

    with tempfile.TemporaryDirectory() as temp_dir:
        base_mp3_filepath = pathlib.Path(temp_dir, BASE_MP3_FILENAME)
        if args.input_filepath:
            # copy input .mp3 file to temp dir
            logger.debug(f"Using {args.input_filepath} as input filepath")
            shutil.copy(args.input_filepath, base_mp3_filepath)
        else:
            # download youtube .mp3 file
            logger.debug(f"Downloading {args.youtube}")
            with PushDir(temp_dir):
                download_youtube(args.youtube, BASE_MP3_FILENAME)

        # temp_dir now holds the BASE_MP3_FILENAME
        logger.debug(f"temp_dir contents: {os.listdir(temp_dir)}")

        # loop audio
        with PushDir(temp_dir):
            loop_audio(
                mp3_filepath=BASE_MP3_FILENAME,
                output_filepath=output_filepath,
                sampling_rate_hz=args.sampling_rate,
                length_s=args.length,
                start_s=args.start,
                end_s=args.end,
                start_offset_beats=args.start_offset,
                end_offset_beats=args.end_offset,
                input_shift_beats=args.input_shift,
                end_truncate_ms=args.end_truncate,
                output_fade_ms=args.output_fade,
            )


if __name__ == "__main__":
    main()
