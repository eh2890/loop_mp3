import pytest


from utils.timestamp_to_seconds_converter import (
    TimestampFormatError,
    TimestampToSecondsConverter,
)


class TestTimestampToSecondsConverter:
    @pytest.mark.parametrize(
        "timestamp, seconds",
        [
            ("23:59:59", 86399),
            ("01:23:45", 5025),
            ("1:23:45", 5025),
            ("1:00:00", 3600),
            ("0:59:59", 3599),
            ("12:34", 754),
            ("1:23", 83),
            ("12", 12),
            ("1", 1),
            ("00:00:00", 0),
            ("0:00:00", 0),
            ("00:00", 0),
            ("0:00", 0),
            ("00", 0),
            ("0", 0),
        ],
    )
    def test_convert_timestamp_to_seconds_success(
        self, timestamp: str, seconds: int
    ) -> None:
        assert seconds == TimestampToSecondsConverter.convert_timestamp_to_seconds(
            timestamp
        )

    @pytest.mark.parametrize(
        "timestamp",
        [
            "abc",
            "123",
            "123:456",
            ":23",
            "-12:34",
            "-1:23",
        ],
    )
    def test_convert_timestamp_to_seconds_timestamp_format_error(
        self, timestamp: str
    ) -> None:
        with pytest.raises(
            TimestampFormatError, match=f"Improperly formatted {timestamp=}"
        ):
            TimestampToSecondsConverter.convert_timestamp_to_seconds(timestamp)
