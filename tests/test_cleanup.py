from __future__ import annotations

import click
import pytest

from sandbox.cleanup import parse_duration


class TestParseDuration:
    def test_days(self) -> None:
        assert parse_duration("7d") == 604800

    def test_hours(self) -> None:
        assert parse_duration("24h") == 86400

    def test_minutes(self) -> None:
        assert parse_duration("30m") == 1800

    def test_seconds(self) -> None:
        assert parse_duration("60s") == 60

    def test_invalid_unit_raises(self) -> None:
        with pytest.raises(click.BadParameter):
            parse_duration("7x")
