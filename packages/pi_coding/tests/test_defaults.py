"""Tests for pi_coding core defaults."""

from pi_coding.core.defaults import DEFAULT_THINKING_LEVEL


def test_default_thinking_level():
    assert DEFAULT_THINKING_LEVEL == "medium"
