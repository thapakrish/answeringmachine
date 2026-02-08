# The Answering Machine

A voice-powered AI phone agent built on [Cartesia's Line SDK](https://docs.cartesia.ai/build-with-line). It turns a phone number into an intelligent family answering machine that identifies callers, relays messages, tracks reminders, remembers past conversations, and even chats in Hindi or Spanish.

## How It Works

```
Incoming Call → Cartesia (STT/TTS) → Agent Routing → LLM (Claude Haiku 4.5)
                                          │
                    ┌─────────────────────┼──────────────────────┐
                    │                     │                      │
             Device User           Family Member           Unknown Caller
          (person who owns        (calls to leave         (passphrase
           the phone)              messages, etc.)         challenge)
```

When someone calls the phone number:

1. **Caller identification** — Firestore lookup maps the incoming phone number to a known family member
2. **Agent routing** — The right agent is selected based on who's calling:
   - **DeviceUserAgent** — The phone owner (e.g. grandma) gets a personalized greeting, can hear messages, set reminders, search the web, or just chat
   - **FamilyMemberAgent** — Family members can leave messages (including anonymous ones), add reminders, or check on the device user's wellness
   - **GatekeeperAgent** — Unknown callers must provide the family passphrase to proceed
3. **Conversation memory** — Each call is summarized and stored, so the agent remembers past interactions
4. **Multilingual** — Mid-call language switching to Hindi or Spanish (voice + LLM prompt swap)

## Features

| Feature | Description |
|---------|-------------|
| Caller ID | Identifies callers via Firestore phone number lookup |
| Message relay | Family members leave messages; device user hears them |
| Anonymous messages | Leave messages attributed to "A family member" |
| Reminders | Set, hear, and add reminders for family members |
| Conversation memory | Summarizes calls and loads context into future conversations |
| Companion chat | Handoff to a warm, conversational chat agent |
| Web search | Real-time web search via DuckDuckGo |
| Website browsing | Navigate websites via Browserbase + Stagehand |
| Wellness check | Family members can check on the device user's recent activity and mood |
| Language switching | Switch to Hindi or Spanish mid-call (voice + prompt) |
| Gatekeeper | Passphrase-based access control for unknown callers |
| Expressive TTS | Cartesia Sonic-3 SSML tags for dynamic, emotional speech |

## Architecture

```
cartesiavoice/
├── main.py                    # Entry point: VoiceAgentApp + routing
├── firebase_client.py         # Firestore async client
├── cartesia.toml              # Cartesia deployment config
├── pyproject.toml             # Dependencies
│
├── agents/
│   ├── device_user_agent.py   # AgentClass for the phone owner
│   ├── family_member_agent.py # AgentClass for family callers
│   ├── gatekeeper_agent.py    # Passphrase challenge for unknown callers
│   ├── role_config.py         # Voice IDs, personalities, language configs
│   └── prompts.py             # All system prompts
│
├── tools/
│   ├── message_tools.py       # hear_messages, leave_message, leave_anonymous
│   ├── reminder_tools.py      # set_reminder, hear_reminders, add_reminder
│   ├── wellness_tools.py      # check_wellness
│   ├── search_tools.py        # browse_website (Browserbase/Stagehand)
│   └── language_tools.py      # switch_to_hindi, switch_to_spanish
│
├── web/
│   └── dashboard.py           # FastAPI API for account management
│
├── infra/                     # Terraform GCP setup
└── tests/                     # 125 tests
```

## Setup

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager
- [Cartesia CLI](https://docs.cartesia.ai/build-with-line)
- A GCP project with Firestore enabled

### Install

```bash
uv sync --extra dev --extra web --extra search
```

### Environment Variables

Create a `.env` file:

```
CARTESIA_API_KEY=...              # Cartesia platform key
ANTHROPIC_API_KEY=...             # Claude API key
FIREBASE_SERVICE_ACCOUNT_JSON=... # GCP service account JSON (stringified)
BROWSERBASE_API_KEY=...           # Browserbase (optional, for website browsing)
BROWSERBASE_PROJECT_ID=...        # Browserbase project ID (optional)
GEMINI_API_KEY=...                # For Stagehand (optional)
```

### Run Locally

```bash
uv run python main.py
cartesia chat 8000   # Test in text mode
```

### Deploy

```bash
cartesia auth login
cartesia env set --from .env
cartesia deploy
cartesia status
```

### Test

```bash
uv run pytest tests/
```

## Tech Stack

- **Voice platform**: [Cartesia Line SDK](https://docs.cartesia.ai/build-with-line) (STT via Ink, TTS via Sonic-3)
- **LLM**: Claude Haiku 4.5 via [LiteLLM](https://docs.litellm.ai/)
- **Database**: Google Cloud Firestore (async client)
- **Web browsing**: [Browserbase](https://www.browserbase.com/) + [Stagehand](https://github.com/browserbase/stagehand)
- **Infrastructure**: Terraform (GCP)
- **API**: FastAPI (optional web dashboard)

## License

MIT
