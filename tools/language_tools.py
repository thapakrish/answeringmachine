"""Language switching tools — switch the agent's voice and response language.

Instead of handing off to a separate agent (slow, breaks STT),
these tools switch the voice AND update the system prompt so the
LLM responds in the target language. The same agent stays in
control with all its tools and memory.
"""

from typing import Annotated

from line.events import AgentSendText, AgentUpdateCall
from line.llm_agent import LlmConfig, passthrough_tool, ToolEnv

from agents.role_config import LANGUAGE_CONFIGS


def make_language_switch_tools(greeter_agent=None):
    """Build language switch tools from LANGUAGE_CONFIGS.

    Args:
        greeter_agent: The LlmAgent whose system prompt should be updated
            on language switch. If None, only the voice changes (no prompt update).

    Returns a list of passthrough tools that switch voice + update system prompt.
    """
    tools = []

    for code, cfg in LANGUAGE_CONFIGS.items():
        lang_name = cfg["name"]
        voice_id = cfg["voice_id"]
        confirmation = cfg["handoff_message"]
        description = cfg["handoff_description"]
        system_prompt = cfg["system_prompt"]

        # Use closure to capture per-language values
        def _make_tool(vid, conf, lname, desc, prompt):
            async def _switch(ctx: ToolEnv):
                # Update the LLM system prompt so it responds in the new language
                if greeter_agent is not None:
                    new_config = LlmConfig(system_prompt=prompt)
                    greeter_agent._config = new_config
                    greeter_agent._llm._config = new_config

                # Switch the Cartesia TTS voice
                yield AgentUpdateCall(voice_id=vid)
                # Speak confirmation in the target language
                yield AgentSendText(text=conf)

            # Set name and docstring BEFORE decorating so _ToolDescriptor captures them
            _switch.__name__ = f"switch_to_{lname.lower()}"
            _switch.__doc__ = desc

            tool = passthrough_tool(_switch)
            tool.name = f"switch_to_{lname.lower()}"
            return tool

        tools.append(_make_tool(voice_id, confirmation, lang_name, description, system_prompt))

    return tools
