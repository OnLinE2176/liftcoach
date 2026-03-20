"""
LiftCoach AI — Live Recorder Component
Browser-based webcam recorder using HTML5 MediaRecorder API.
Returns base64-encoded video data to Python.
"""

import streamlit.components.v1 as components
import os

_COMPONENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "live_recorder", "frontend")
_component_func = components.declare_component("live_recorder", path=_COMPONENT_DIR)


def live_recorder(key=None):
    """
    Render the live webcam recorder component.

    Returns:
        str | None: Base64-encoded video data (webm) when recording is
                    complete, or None while idle / recording.
    """
    result = _component_func(key=key, default=None)
    return result
