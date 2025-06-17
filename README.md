# Loop MP3

A Python script to loop `.mp3` files.

## Setup

For the root directory of the repository, run:
```
$ python3 -m venv venv
$ source venv/bin/activate
$ pip install -r requirements.txt
$ pip install -e .
```

## Usage

### Help

To display the help message, run:
```
$ loop-mp3 --help
```

### Input

The source input must be provided in one the following ways:
- The `--youtube` argument can be a YouTube link
- The `--input-filepath` argument can be a filepath to an `.mp3` file.

### Input Splicing

The source input `.mp3` file can be spliced/altered in several ways:
- The `--start` and `--end` arguments indicate, to second precision, the section of the input `.mp3` file that is used to loop
    - See the (Timestamp Format)[#timestamp-format] section for the format for these inputs
    - The start beat is the first beat at or after the start time
    - The end beat if the last beat at or before the end time
- For finer control, the `--start-offset` and `--end-offset` arguments can be used to adjust the start and end beats respectively
- The `--input-shift` argument is the number of beats to shift the start and end of the looping section
    - See the (Beat Shift)[#beat-shift] section for details
- The `--sampling-rate` argument is to determine the sampling rate used to load the `.mp3` file

### Output

The output `.mp3` file can be adjusted:
- The `--length` argument indicates the maximum length of the output `.mp3` file as a timestamp
    - See the (Timestamp Format)[#timestamp-format] section for the format for these inputs
    - If this optional argument is not provided, only the looped segment will be downloaded (e.g. one repetition)
- The `--output-filepath` arguments allows the user to specify the filepath of the output file.

## Reference

### Timestamp Format

The accepted timestamp format are generally in the `HH:MM:SS` format. The full list of formats is below:
- `HH:MM:SS`
- `H:MM:SS`
- `MM:SS`
- `M:SS`
- `SS`
- `S`
Timestamps such as `02:00:00` (2 hours), `23:49` (23 minutes, 49 seconds), and `9` (9 seconds) are acceptable, but strings such as `400` or `3:9` are not acceptable.

With these formats, the maximum timestamp is `23:59:59`.

### Beat Shift

The beat shift is an experimental solution for audio segments that, when looped, have poor transitions between repetitions of the looped segment. This is realistically only applicable to `.mp3` files containing two or more looped segments.

When the beat shift is provided, the looped segment is now `[end, end + beat_shift) + [start + beat_shift, end)`, where `start` is time of the starting beat and `end` is the time of the ending beat.
