"""Language handoff tools — switch the agent to speak in another language."""

import os

from line.events import AgentUpdateCall
from line.llm_agent import LlmAgent, LlmConfig, agent_as_handoff, end_call, handoff_tool, ToolEnv
from line.llm_agent.tools.utils import construct_function_tool

from agents.role_config import get_language_configs


def make_language_handoffs(role: str, api_key: str = None):
    """Build language handoff tools for a given role.

    Returns a list of (handoff_tool, llm_agent) tuples.
    The llm_agent is returned so the caller can clean it up on CallEnded.
    """
    api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    lang_configs = get_language_configs(role)
    results = []

    for lang_cfg in lang_configs:
        lang_name = lang_cfg["name"]
        voice_id = lang_cfg["voice_id"]

        lang_agent = LlmAgent(
            model="anthropic/claude-haiku-4-5-20251001",
            api_key=api_key,
            tools=[end_call],
            config=LlmConfig(
                system_prompt=lang_cfg["system_prompt"],
                introduction=lang_cfg["handoff_message"],
            ),
        )

        # Wrap agent_as_handoff but prepend AgentUpdateCall for voice switch
        inner_handoff = agent_as_handoff(
            lang_agent,
            name=f"switch_to_{lang_name.lower()}",
            description=lang_cfg["handoff_description"],
        )

        # Wrap handoff to emit AgentUpdateCall for voice switch before delegating
        original_func = inner_handoff.func

        def _make_handoff(vid, orig):
            async def _voice_switching_handoff(ctx: ToolEnv, event):
                yield AgentUpdateCall(voice_id=vid)
                async for output in orig(ctx, event=event):
                    yield output
            return _voice_switching_handoff

        tool = construct_function_tool(
            _make_handoff(voice_id, original_func),
            name=inner_handoff.name,
            description=inner_handoff.description,
            tool_type=inner_handoff.tool_type,
        )

        results.append((tool, lang_agent))

    return results
