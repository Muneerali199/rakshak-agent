"""Vocal FIR intake — the Bhashini voice channel.

The product story: a Hindi-speaking complainant's statement reaches the case
graph *spoken*, not typed. The real channel is **Bhashini** — MeitY's National
Language Translation Mission — whose ASR (speech-to-text) and TTS
(text-to-speech) APIs are consumed over **API Setu**.

What actually runs on this box is a **real, on-device** speech engine (the
browser's Web Speech stack with `hi-IN`), because it works offline with no
credentials — the officer dictates in Hindi, the transcript lands in the
narrative textarea, is vetted before ingest, and nothing leaves the district
box. It is honestly labeled ``bhashini-ondevice-sim``; nothing here claims a
live Bhashini call. Production swaps the same conversation boundary for the
Bhashini ASR/TTS API over API Setu (requires a Bhashini token / agency access).
"""
from __future__ import annotations

VOICE_BRIDGE = "bhashini-ondevice-sim"
VOICE_BRIDGE_PRODUCTION = "api-setu-bhashini-asr-tts"

VOICE_DISCLOSURE = (
    "Vocal FIR intake: statement → speech-to-text → vetted narrative → case graph. "
    "This box uses the on-device Hindi speech engine (offline, no cloud, no data "
    "leaving the district box) and labels it bhashini-ondevice-sim. Production swaps "
    "in Bhashini (MeitY National Language Translation Mission) ASR/TTS over API Setu "
    "for 20+ Indic languages — needs a Bhashini token, not claimable offline. The "
    "dictated transcript is always officer-vetted before anything enters the graph.")


def voice_status() -> dict:
    return {
        "bridge": VOICE_BRIDGE,
        "production": f"{VOICE_BRIDGE_PRODUCTION} — Bhashini ASR/TTS via API Setu; "
                      "live needs a Bhashini token (offline box uses on-device speech)",
        "asr": {"engine": "on-device hi-IN", "offline": True, "audible_input": True},
        "tts": {"engine": "on-device hi-IN", "offline": True, "audible_output": True},
        "languages": {"now": ["hi-IN"], "production": "20+ Bhashini languages (BANGLA, TAMIL, …)"},
        "data_flow": "audio → device → text → officer-vetted narrative → graph; "
                     "nothing leaves the district box",
        "disclosure": VOICE_DISCLOSURE,
    }