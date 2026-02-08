"""Role-based voice, personality, and language configuration.

Each role maps to a Cartesia voice ID, a personality description
injected into the system prompt, and optional language handoffs.
The agent adapts its tone, voice, and language depending on who is calling.
"""

# Voice IDs from Cartesia's voice library
# Browse: https://play.cartesia.ai/voices

# Language handoff configurations
# Each language has a Cartesia voice and system prompt for that language
LANGUAGE_CONFIGS = {
    "hi": {
        "name": "Hindi",
        "voice_id": "393dd459-f8d8-4c3e-a86b-ec43a1113d0b",  # Rahul - Calm Office Guy
        "system_prompt": (
            "आप एक सहायक वॉइस असिस्टेंट हैं। हिंदी में बात करें। "
            "जवाब संक्षिप्त और स्पष्ट रखें। यह एक फोन कॉल है।"
        ),
        "handoff_description": (
            "Switch to Hindi-speaking mode. "
            "Use when the caller asks to speak in Hindi or starts speaking Hindi."
        ),
        "handoff_message": "हिंदी में बात करते हैं।",
    },
    "es": {
        "name": "Spanish",
        "voice_id": "846d6cb0-2301-48b6-9571-13571f3bd45e",  # Spanish voice
        "system_prompt": (
            "Eres un asistente de voz servicial. Habla solo en español. "
            "Mantén las respuestas breves y claras. Esta es una llamada telefónica."
        ),
        "handoff_description": (
            "Switch to Spanish-speaking mode. "
            "Use when the caller asks to speak in Spanish or starts speaking Spanish."
        ),
        "handoff_message": "Cambiando a español.",
    },
}

ROLE_DEFAULTS = {
    "grandparent": {
        "voice_id": "d7e54830-4754-4b17-952c-bcdb7e80a2fb",  # Mabel - Grandma
        "personality": (
            "Speak slowly and clearly. Be extra warm, patient, and gentle. "
            "Use simple words and short sentences. If the caller seems confused, "
            "calmly repeat or rephrase. React with genuine delight to good news."
        ),
    },
    "parent": {
        "voice_id": "79f8b5fb-2cc8-479a-80df-29f7a7cf1a04",  # Adelaide - Authoritative
        "personality": (
            "Be friendly but efficient. This caller is busy — get to the point quickly. "
            "Offer proactive suggestions. Be organized and clear."
        ),
    },
    "son": {
        "voice_id": "79f8b5fb-2cc8-479a-80df-29f7a7cf1a04",  # Adelaide - Calm & professional
        "personality": (
            "Be calm and professional. Keep responses concise and to the point. "
            "Polite but not overly friendly — like a helpful receptionist."
        ),
        "languages": ["hi"],
    },
    "daughter": {
        "voice_id": "cbaf8084-f009-4838-a096-07ee2e6612b1",  # Maya - Easygoing Ally
        "personality": (
            "Be casual and relaxed. Use a conversational, easygoing tone. "
            "Keep it natural — like chatting with a friend."
        ),
    },
    "grandchild": {
        "voice_id": "6ccbfb76-1fc6-48f7-b71d-91ac6298247b",  # Tessa - Kind Companion
        "personality": (
            "Be upbeat and enthusiastic! Use simple language and a playful tone. "
            "React with excitement. Keep things fun and lighthearted."
        ),
    },
    "granddaughter": {
        "voice_id": "6ccbfb76-1fc6-48f7-b71d-91ac6298247b",  # Tessa - Kind Companion
        "personality": (
            "Be upbeat and enthusiastic! Use simple language and a playful tone. "
            "React with excitement. Keep things fun and lighthearted."
        ),
    },
    "great-granddaughter": {
        "voice_id": "6ccbfb76-1fc6-48f7-b71d-91ac6298247b",  # Tessa - Kind Companion
        "personality": (
            "Be super friendly and playful! Use very simple words. "
            "Be encouraging and patient. Make the conversation fun."
        ),
    },
    "spouse": {
        "voice_id": "79f8b5fb-2cc8-479a-80df-29f7a7cf1a04",  # Adelaide - Authoritative
        "personality": (
            "Be warm and familiar. This is a close relationship — be natural and comfortable. "
            "Be helpful and attentive."
        ),
    },
    "caregiver": {
        "voice_id": "79f8b5fb-2cc8-479a-80df-29f7a7cf1a04",  # Adelaide - Authoritative
        "personality": (
            "Be professional, clear, and supportive. Provide detailed information when asked. "
            "Be respectful and organized."
        ),
    },
    "guest": {
        "voice_id": "cbaf8084-f009-4838-a096-07ee2e6612b1",  # Maya - Easygoing Ally
        "personality": (
            "Be polite and professional. This is someone you don't know well — "
            "be helpful but keep appropriate boundaries."
        ),
    },
}

# Fallback for unknown roles
_DEFAULT = {
    "voice_id": "cbaf8084-f009-4838-a096-07ee2e6612b1",  # Maya - Easygoing Ally
    "personality": "Be friendly, clear, and helpful.",
}


def get_role_config(role: str) -> dict:
    """Get voice_id and personality for a given role."""
    return ROLE_DEFAULTS.get(role, _DEFAULT)


def get_language_configs(role: str) -> list[dict]:
    """Get language handoff configs for a role. Returns list of LANGUAGE_CONFIGS entries."""
    role_cfg = ROLE_DEFAULTS.get(role, _DEFAULT)
    lang_codes = role_cfg.get("languages", [])
    return [LANGUAGE_CONFIGS[code] for code in lang_codes if code in LANGUAGE_CONFIGS]
