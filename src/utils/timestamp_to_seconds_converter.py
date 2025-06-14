"""
Class for managing converting timestamps to total number of seconds.

Leading 0s are not necessary on the leftmost field; e.g. 3:09 indicates
3 minutes and 9 seconds.
"""

import re


class TimestampFormatError(Exception):
    def __init__(self, timestamp: str) -> None:
        super().__init__(f"Improperly formatted {timestamp=}")


class TimestampToSecondsConverter:
    SUPPORTED_TIMESTAMP_FORMATS = [
        "HH:MM:SS",
        "H:MM:SS",
        "MM:SS",
        "M:SS",
        "SS",
        "S",
    ]
    _HH_MM_SS_REGEX = r"(\d{1,2}):(\d{2}):(\d{2})"
    _MM_SS_REGEX = r"(\d{1,2}):(\d{2})"
    _SS_REGEX = r"(\d{1,2})"

    @classmethod
    def convert_timestamp_to_seconds(cls, timestamp: str | int) -> int:
        timestamp = str(timestamp)
        """
        Converts a HH:MM:SS, MM:SS, or SS timestamp into number of seconds.
        Leading 0s are not necessary.
        """
        hh_mm_ss_match = re.fullmatch(cls._HH_MM_SS_REGEX, timestamp)
        mm_ss_match = re.fullmatch(cls._MM_SS_REGEX, timestamp)
        ss_match = re.fullmatch(cls._SS_REGEX, timestamp)

        if hh_mm_ss_match:
            hour, minute, second = map(int, hh_mm_ss_match.groups())
        elif mm_ss_match:
            hour = 0
            minute, second = map(int, mm_ss_match.groups())
        elif ss_match:
            hour = 0
            minute = 0
            second = int(ss_match.group(0))
        else:
            raise TimestampFormatError(timestamp)

        if not (0 <= hour <= 23 and 0 <= minute < 60 and 0 <= second < 60):
            raise TimestampFormatError(timestamp)

        total_seconds = 3600 * hour + 60 * minute + second

        return total_seconds
