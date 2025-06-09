import argparse
import pathlib
import logging
import tempfile
import os
import shutil

from youtube_downloader import download_youtube
from constants import BASE_MP3_FILENAME
from audio import loop_audio
from utils.directory_utils import PushDir


log = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="game_music_mp3",
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
    # output length group
    output_length_group = parser.add_argument_group(
        "Output length", "Parameters for determining the time length of the output file"
    )
    mutually_exclusive_length_output_group = (
        output_length_group.add_mutually_exclusive_group()
    )
    mutually_exclusive_length_output_group.add_argument(
        "--length",
        "-l",
        type=int,
        help="Maximum length of the output file, in seconds",
    )
    mutually_exclusive_length_output_group.add_argument(
        "--repetitions",
        "-r",
        type=int,
        help="Number of times the input .mp3 is repeated",
        default=1,
    )
    # output name
    parser.add_argument(
        "--output-filepath",
        "-o",
        type=str,
        help="Name of output file",
        default="output.mp3",
    )
    # beat offset
    parser.add_argument(
        "--beat-offset",
        "-b",
        type=int,
        help="Number of beats to offset when finding loop segment",
        default=0,
    )

    args = parser.parse_args()
    output_filepath = pathlib.Path(args.output_filepath).resolve()

    with tempfile.TemporaryDirectory() as temp_dir:
        base_mp3_filepath = pathlib.Path(temp_dir, BASE_MP3_FILENAME)
        if args.input_filepath:
            # copy input .mp3 file to temp dir
            log.info(f"Using {args.input_filepath} as input filepath")
            shutil.copy(args.input_filepath, base_mp3_filepath)
        else:
            # download youtube .mp3 file
            log.info(f"Downloading {args.youtube}")
            with PushDir(temp_dir):
                download_youtube(args.youtube, BASE_MP3_FILENAME)

        # temp_dir now holds the BASE_MP3_FILENAME
        log.info(f"temp_dir contents: {os.listdir(temp_dir)}")

        # loop audio
        with PushDir(temp_dir):
            if args.length:
                loop_audio(
                    BASE_MP3_FILENAME,
                    output_filepath,
                    length=args.length,
                    beat_offset=args.beat_offset,
                )
            else:
                loop_audio(
                    BASE_MP3_FILENAME,
                    output_filepath,
                    repetitions=args.repetition,
                    beat_offset=args.beat_offset,
                )


if __name__ == "__main__":
    main()
