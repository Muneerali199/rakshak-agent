"""Bhashini voice channel contract: on-device, honestly labeled, in the posture."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

import api.main as apimod  # noqa: E402
from voice import VOICE_BRIDGE, voice_status  # noqa: E402


def _client() -> TestClient:
    return TestClient(apimod.app)


def test_voice_status_endpoint():
    with _client() as c:
        r = c.get("/api/voice/status")
        assert r.status_code == 200
        d = r.json()
        assert d["bridge"] == VOICE_BRIDGE == "bhashini-ondevice-sim"
        assert d["production"].endswith("Bhashini token (offline box uses on-device speech)")
        assert d["asr"]["offline"] is True and d["tts"]["offline"] is True
        assert d["asr"]["engine"].startswith("on-device")
        assert "Bhashini" in d["disclosure"]
        assert "disclosure" in second_call(c)


def second_call(c) -> dict:
    return c.get("/api/voice/status").json()


def test_voice_present_in_posture_and_graded_map():
    with _client() as c:
        p = c.get("/api/security/posture").json()
        assert p["levels"]["GET /api/voice/status"]["level"] == 1
        assert p["voice"]["bridge"] == VOICE_BRIDGE