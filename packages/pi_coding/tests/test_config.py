"""Tests for pi_coding config module."""

import os
import tempfile
from pathlib import Path

import pytest

from pi_coding.config import (
    APP_NAME,
    CONFIG_DIR_NAME,
    ENV_AGENT_DIR,
    VERSION,
    get_agent_dir,
    get_bin_dir,
    get_sessions_dir,
    get_settings_path,
)


def test_version_constant():
    assert VERSION == "0.1.0"


def test_app_name_constant():
    assert APP_NAME == "pi"


def test_config_dir_name_constant():
    assert CONFIG_DIR_NAME == ".pi"


def test_env_agent_dir_constant():
    assert ENV_AGENT_DIR == "PI_CODING_AGENT_DIR"


def test_get_agent_dir_default():
    path = get_agent_dir()
    assert str(path).endswith(".pi/agent") or str(path).endswith(".pi\\agent")


def test_get_agent_dir_env_override():
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ[ENV_AGENT_DIR] = tmpdir
        try:
            path = get_agent_dir()
            assert path == Path(tmpdir)
        finally:
            del os.environ[ENV_AGENT_DIR]


def test_get_agent_dir_tilde():
    os.environ[ENV_AGENT_DIR] = "~"
    try:
        path = get_agent_dir()
        assert path == Path.home()
    finally:
        del os.environ[ENV_AGENT_DIR]


def test_get_agent_dir_tilde_with_path():
    os.environ[ENV_AGENT_DIR] = "~/custom/path"
    try:
        path = get_agent_dir()
        assert path == Path.home() / "custom/path"
    finally:
        del os.environ[ENV_AGENT_DIR]


def test_get_sessions_dir():
    path = get_sessions_dir()
    assert path.name == "sessions"
    # Check it's under .pi/agent/sessions
    assert ".pi" in str(path) or ".pi" in str(path).replace("\\", "/")


def test_get_settings_path():
    path = get_settings_path()
    assert path.name == "settings.json"
    # Check it's under .pi/agent/settings.json
    assert ".pi" in str(path) or ".pi" in str(path).replace("\\", "/")


def test_get_bin_dir():
    path = get_bin_dir()
    assert path.name == "bin"
    # Check it's under .pi/agent/bin
    assert ".pi" in str(path) or ".pi" in str(path).replace("\\", "/")


def test_paths_are_path_objects():
    assert isinstance(get_agent_dir(), Path)
    assert isinstance(get_sessions_dir(), Path)
    assert isinstance(get_settings_path(), Path)
    assert isinstance(get_bin_dir(), Path)
