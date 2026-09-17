CLIENT_NAME = "smartcv-ssbu"

REQUIRED_CONFIG = [
    {
        "section": "settings",
        "key": "capture_mode",
        "kind": "choice",
        "ask": "once",
        "prompt": "Capture the game from OBS, or from a game window on this PC?",
        "choices": [
            {"value": "obs", "label": "OBS"},
            {"value": "game", "label": "Game window"},
        ],
    },
    {
        "section": "obs",
        "key": "source_title",
        "ask": "if_empty",
        "prompt": "Name of the OBS source showing the game (not the scene name):",
        "when": {"section": "settings", "key": "capture_mode", "equals": "obs"},
    },
    {
        "section": "settings",
        "key": "executable_title",
        "ask": "confirm_default",
        "prompt": "Game window title",
        "when": {"section": "settings", "key": "capture_mode", "equals": "game"},
    },
]
