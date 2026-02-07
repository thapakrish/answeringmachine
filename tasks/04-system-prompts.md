# Task 04: System Prompts

- **Priority**: P0
- **Deps**: Task 01 (scaffold)
- **PRD**: FR-2.1, FR-3.1

## Objective

Define all system prompts as string constants in `agents/prompts.py`. Prompts use `{placeholder}` format for runtime substitution.

## Tests First

```python
# tests/test_prompts.py
import re
from agents.prompts import (
    DEVICE_USER_GREETER_PROMPT,
    FAMILY_MEMBER_GREETER_PROMPT,
    COMPANION_PROMPT,
    GATEKEEPER_PROMPT,
)

def test_device_user_prompt_has_name_placeholder():
    assert "{member_name}" in DEVICE_USER_GREETER_PROMPT

def test_device_user_prompt_has_role_placeholder():
    assert "{member_role}" in DEVICE_USER_GREETER_PROMPT

def test_device_user_prompt_has_memory_placeholder():
    assert "{memory_context}" in DEVICE_USER_GREETER_PROMPT

def test_family_member_prompt_has_name_placeholder():
    assert "{member_name}" in FAMILY_MEMBER_GREETER_PROMPT

def test_family_member_prompt_has_device_user_placeholder():
    assert "{device_user_name}" in FAMILY_MEMBER_GREETER_PROMPT

def test_companion_prompt_has_name_placeholder():
    assert "{member_name}" in COMPANION_PROMPT

def test_gatekeeper_prompt_is_nonempty():
    assert len(GATEKEEPER_PROMPT.strip()) > 50

def test_prompts_contain_no_emoji():
    emoji_pattern = re.compile(
        "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U0001F900-\U0001F9FF]"
    )
    for prompt in [DEVICE_USER_GREETER_PROMPT, FAMILY_MEMBER_GREETER_PROMPT, COMPANION_PROMPT, GATEKEEPER_PROMPT]:
        assert not emoji_pattern.search(prompt), f"Emoji found in prompt: {prompt[:50]}..."

def test_prompts_mention_voice_context():
    """Prompts should remind the LLM this is a phone call."""
    for prompt in [DEVICE_USER_GREETER_PROMPT, FAMILY_MEMBER_GREETER_PROMPT, COMPANION_PROMPT]:
        assert "phone" in prompt.lower() or "spoken" in prompt.lower() or "voice" in prompt.lower()
```

## Implementation

```python
# agents/prompts.py

DEVICE_USER_GREETER_PROMPT = """..."""   # Warm, patient, memory-aware. Describes available tools.
FAMILY_MEMBER_GREETER_PROMPT = """...""" # Efficient, helpful. Describes leave_message, check_wellness, etc.
COMPANION_PROMPT = """..."""             # Friendly chat partner. References past conversations.
GATEKEEPER_PROMPT = """..."""            # Passphrase challenge. Clear instructions.
```

See PLAN.md "agents/prompts.py" section and DESIGN.html Section 10 for prompt content guidelines.

## Verification

```bash
pytest tests/test_prompts.py -v
```
