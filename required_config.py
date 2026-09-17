CLIENT_NAME = "smartcv-ssbu"

REQUIRED_CONFIG = [
    {
        "section": "obs",
        "key": "source_title",
        "prompt": "Name of the OBS source showing the game (not the scene name):",
        "when": {"section": "settings", "key": "capture_mode", "equals": "obs"},
    },
    {
        "section": "settings",
        "key": "executable_title",
        "prompt": "Exact title of the game window:",
        "when": {"section": "settings", "key": "capture_mode", "equals": "game"},
    },
]
