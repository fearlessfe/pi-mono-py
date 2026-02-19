"""Configuration paths for pi_coding agent."""

import os
from pathlib import Path

# Version from package (can be updated)
VERSION = "0.1.0"

# App configuration
APP_NAME = "pi"
CONFIG_DIR_NAME = ".pi"

# Environment variable for custom agent directory
ENV_AGENT_DIR = f"{APP_NAME.upper()}_CODING_AGENT_DIR"


def get_agent_dir() -> Path:
    """Get the agent config directory (e.g., ~/.pi/agent/).
    
    Checks ENV_AGENT_DIR first, then uses default ~/.pi/agent/
    
    Returns:
        Path to agent directory
    """
    env_dir = os.environ.get(ENV_AGENT_DIR)
    if env_dir:
        if env_dir == "~":
            return Path.home()
        if env_dir.startswith("~/"):
            return Path.home() / env_dir[2:]
        return Path(env_dir)
    return Path.home() / CONFIG_DIR_NAME / "agent"


def get_sessions_dir() -> Path:
    """Get the sessions directory (e.g., ~/.pi/agent/sessions/).
    
    Returns:
        Path to sessions directory
    """
    return get_agent_dir() / "sessions"


def get_settings_path() -> Path:
    """Get path to settings.json (e.g., ~/.pi/agent/settings.json).
    
    Returns:
        Path to settings.json file
    """
    return get_agent_dir() / "settings.json"


def get_bin_dir() -> Path:
    """Get path to managed binaries directory (fd, rg).
    
    Returns:
        Path to bin directory
    """
    return get_agent_dir() / "bin"
