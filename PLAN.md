# AnsweringMachine - Implementation Plan

## Architecture

```
INCOMING CALL → VoiceAgentApp(get_agent, pre_call_handler)
    │
    ├── pre_call_handler(call_request)
    │     │
    │     ├── Lookup call_request.from_ (caller phone) in Firestore
    │     ├── Lookup call_request.to (device phone) in Firestore
    │     │
    │     ├── Unknown caller → metadata: {is_authorized: false, needs_passphrase: true}
    │     ├── Device user picking up → metadata: {is_device_user: true, member_id, name, ...}
    │     └── Known family member → metadata: {is_device_user: false, member_id, name, ...}
    │
    └── get_agent(env, call_request)
          │
          ├── is_authorized=false → GatekeeperAgent
          │     ├── Family found via call_request.to (device phone)
          │     ├── Asks for family passphrase (stored as field on families/{id} document)
          │     ├── Correct → one-off session as guest (no number registration)
          │     │     └── Proceeds to FamilyMemberAgent with member_id="guest", name="Guest"
          │     │         Tools use from_member_id="guest", from_name="Guest" in Firestore
          │     │         RESTRICTED: no check_wellness, no add_reminder (guests can only leave messages)
          │     └── Wrong/no answer → "This number is not registered." → end_call, logged
          │
          ├── is_device_user=true → DeviceUserAgent (AgentClass)
          │     │
          │     ├── On CallStarted:
          │     │     └── Dynamic intro: time greeting + unread count + memory callback
          │     │
          │     ├── _greeter: LlmAgent (Claude Haiku 4.5)
          │     │     ├── hear_messages    @loopback_tool     → fetch from Firestore
          │     │     ├── hear_reminders   @loopback_tool     → fetch from Firestore
          │     │     ├── set_reminder     @loopback_tool     → save to Firestore
          │     │     ├── quick_search     web_search         → DuckDuckGo (weather, facts)
          │     │     ├── browse_website   @loopback_tool(bg) → Browserbase/Stagehand (site nav)
          │     │     ├── companion_chat   agent_as_handoff   → Companion LlmAgent
          │     │     └── end_call         built-in
          │     │
          │     ├── _companion: LlmAgent (Claude Haiku 4.5)
          │     │     └── Warm, patient chat partner with memory context
          │     │
          │     └── On CallEnded:
          │           └── Save conversation summary to memory collection
          │
          └── is_device_user=false → FamilyMemberAgent (AgentClass)
                │
                └── _greeter: LlmAgent (Claude Haiku 4.5)
                      ├── leave_message    @loopback_tool → save to Firestore
                      ├── leave_anonymous  @loopback_tool → save with from="A family member"
                      ├── check_wellness   @loopback_tool → fetch recent activity
                      ├── add_reminder     @loopback_tool → save to Firestore
                      └── end_call         built-in
```

## File Structure

```
cartesiavoice/
├── main.py                       # Entry point: VoiceAgentApp + pre_call_handler + get_agent
├── firebase_client.py            # Firestore client: all DB operations
├── seed_data.py                  # Seed demo family (The Smiths)
├── pyproject.toml                # Dependencies
├── .env                          # API keys (exists, DO NOT READ)
├── cartesia.toml                 # Cartesia config (exists)
│
├── agents/
│   ├── __init__.py
│   ├── device_user_agent.py      # AgentClass: grandma/kid picks up device
│   ├── family_member_agent.py    # AgentClass: family member calls in
│   └── prompts.py                # All system prompts (centralized)
│
├── tools/
│   ├── __init__.py
│   ├── message_tools.py          # hear_messages, leave_message
│   ├── reminder_tools.py         # set_reminder, hear_reminders, add_reminder
│   ├── search_tools.py           # quick_search (web_search/DuckDuckGo) + browse_website (Browserbase/Stagehand)
│   └── memory_tools.py           # load_memory, save_memory (conversation summaries)
│
└── web/
    ├── __init__.py
    └── dashboard.py              # FastAPI: account management API (stretch goal)
```

## Firestore Data Model

```
families/{family_id}
  ├── name: "The Smiths"
  ├── device_phones: ["+15551234567"]
  ├── passphrase: "sunflower garden"
  ├── created_at: timestamp
  │
  ├── members/{member_id}
  │     ├── name: "Rose"
  │     ├── role: "grandparent"           # grandparent, parent, child, grandchild
  │     ├── phone_numbers: ["+15559876543"]
  │     ├── is_device_user: true
  │     └── preferences: {interests: ["mystery novels", "gardening"]}
  │
  │     (passphrase is a field on the family document itself, not a subcollection)
  │
  ├── messages/{message_id}
  │     ├── from_member_id: "member_abc"  # or "anonymous"
  │     ├── from_name: "Sarah"            # or "A family member"
  │     ├── to_member_id: "member_xyz"
  │     ├── content: "Hi Grandma! Coming for dinner Sunday at 5."
  │     ├── read: false
  │     └── created_at: timestamp
  │
  ├── reminders/{reminder_id}
  │     ├── for_member_id: "member_xyz"
  │     ├── created_by_member_id: "member_abc"
  │     ├── content: "Take blood pressure medicine"
  │     ├── time: "2:00 PM"
  │     ├── recurring: "daily"            # daily, weekly, once, null
  │     └── active: true
  │
  ├── call_logs/{log_id}
  │     ├── caller_phone, caller_member_id, caller_name
  │     ├── timestamp, summary, is_anonymous
  │     └── direction: "inbound"
  │
  └── memory/{member_id}
        ├── recent_conversations: [{date, summary, topics, mood}]
        ├── preferences: {favorite_topics, health_notes, family_context}
        └── last_interaction: timestamp

unknown_call_attempts/{attempt_id}
  ├── phone_number, target_device_phone, family_id
  ├── timestamp, blocked: true
```

## Demo Seed Data (The Smiths)

| Member | Role | Phone | Device User |
|--------|------|-------|-------------|
| Rose | Grandparent | +15551234567 | Yes (primary) |
| Sarah | Granddaughter | +15559876543 | No |
| Mike | Son | +15551111111 | No |
| Emma | Great-granddaughter | +15552222222 | No |

Pre-loaded:
- 2 messages from Sarah and Mike
- 2 reminders (medicine at 2 PM, doctor appointment Thursday)
- Memory: Rose likes mystery novels, recently talked about gardening, mood: cheerful

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Caller routing | `get_agent` factory, not handoffs | Device vs family split is known before conversation starts |
| Agent pattern | AgentClass wrappers (like chat_supervisor) | Need per-call state (metadata, DB, memory) |
| LLM model | Haiku 4.5 for ALL real-time agents | Latency is critical for voice; no Opus in real-time path |
| Unknown callers | GatekeeperAgent with per-family passphrase | Fallback for new phones; one-off session only (no number registration to avoid scope creep) |
| Web search | Built-in `web_search` for quick queries | DuckDuckGo fallback, no ToS risk, low latency |
| Browserbase | `@loopback_tool(is_background=True)` for site navigation | Reserve for impressive demos (library catalog, event pages) |
| Tools as methods | Instance methods on AgentClass | Access to self._db, self._metadata without globals |
| Anonymous messages | In-call tool on FamilyMemberAgent | Reliable (no PSTN *67 dependency); user chooses during call |

## Reference Code (from Line SDK)

| Pattern | Reference File |
|---------|---------------|
| AgentClass wrapper with nested LlmAgent | `line/examples/chat_supervisor/main.py` |
| agent_as_handoff for multi-agent | `line/examples/transfer_agent/main.py` |
| Stateful data extraction | `line/examples/sales_with_leads/main.py` |
| Browserbase + Stagehand | `line/example_integrations/browserbase/main.py` |
| Tool decorators | `line/line/llm_agent/tools/decorators.py` |
| Event types | `line/line/events.py` |

## Implementation Phases

### Phase 1: Core Skeleton (1-2 hours)
**Goal**: A working call where the agent identifies the caller and greets them by name.

Files to create:
- `pyproject.toml` — dependencies: `cartesia-line>=0.2.2`, `firebase-admin>=6.0.0`, `loguru>=0.7.0`, `python-dotenv>=1.0.0`
- `firebase_client.py` — init Firestore, `find_family_by_device_phone()`, `find_member_by_phone()`, `get_primary_device_user()`
- `seed_data.py` — populate The Smiths family
- `agents/prompts.py` — all system prompts
- `main.py` — VoiceAgentApp with pre_call_handler + get_agent
- `agents/device_user_agent.py` — minimal: personalized greeting + end_call
- `agents/family_member_agent.py` — minimal: greeting + end_call

**Verify**:
```bash
python seed_data.py                                    # seed Firestore
ANTHROPIC_API_KEY=... PORT=8000 uv run python main.py  # start agent
cartesia chat 8000                                     # test text mode
```

### Phase 2: Message Relay (1-2 hours)
**Goal**: Family member leaves a message → device user hears it. This is THE killer demo feature.

Add to `firebase_client.py`:
- `save_message()`, `get_unread_messages()`, `mark_messages_read()`

Add tools:
- `leave_message` on FamilyMemberAgent — asks for content, confirms, saves to Firestore
- `hear_messages` on DeviceUserAgent — fetches unread, formats for natural reading, marks read

**Verify**: Call as Sarah → leave message → call as Rose → hear the message.

### Phase 3: Memory + Companion Chat (1 hour)
**Goal**: Personalized greetings that reference past conversations. Companion chat handoff.

Add to `firebase_client.py`:
- `get_memory()`, `save_memory()`

Changes:
- DeviceUserAgent `CallStarted` handler: time-of-day greeting + unread count + memory callback
- `_companion` LlmAgent with `agent_as_handoff` — warm, patient chat partner
- On `CallEnded`: save conversation summary to memory collection

**Verify**: Call as Rose → personalized greeting → "I want to chat" → companion agent takes over.

### Phase 4: Reminders + Wellness (1 hour)
**Goal**: Set and hear reminders. Family can check on device user's activity.

Add to `firebase_client.py`:
- `save_reminder()`, `get_reminders()`, `get_recent_activity()`

Add tools:
- `set_reminder`, `hear_reminders` on DeviceUserAgent
- `add_reminder`, `check_wellness` on FamilyMemberAgent

**Verify**: Sarah sets reminder for Rose → Rose hears her reminders. Sarah checks Rose's wellness.

### Phase 5: Web Search + Browserbase (30-60 min)
**Goal**: "What's the weather?" → quick web search. "What's at the library?" → Browserbase navigates the site.

Add two search tools on DeviceUserAgent:
- `quick_search` using built-in `web_search` tool (DuckDuckGo) — for weather, facts, simple queries
- `browse_website` as `@loopback_tool(is_background=True)` — uses Stagehand + Browserbase to navigate a specific website (e.g. library catalog, community center events page)

Dependencies: `stagehand>=3.0.0`, `google-genai>=1.26.0`

**Verify**: Rose asks about weather → instant web search. Rose asks about library → Browserbase navigates library site.

### Phase 6: Anonymous Messages + Gatekeeper + Polish (30 min)
**Goal**: Anonymous message option for family members. Passphrase-based verification for unknown callers.

Changes:
- FamilyMemberAgent: `leave_anonymous` tool — agent asks "Would you like this to be anonymous?", saves with from_name="A family member"
- GatekeeperAgent: asks for family passphrase, verifies against Firestore, proceeds or blocks
- `log_unknown_call()` in firebase_client
- Prompt polish, error handling

**Verify**: Family member chooses anonymous message → saved without name. Unknown caller with correct passphrase → connected. Wrong passphrase → blocked.

### Phase 7: Web Dashboard (stretch goal, 30 min)
**Goal**: Basic FastAPI API for account management.

- `GET /api/families/{id}` — family info
- `POST /api/families` — create family
- `POST /api/families/{id}/members` — add member
- `GET /api/families/{id}/messages` — view messages
- `GET /api/families/{id}/call-logs` — view call history

## Notes

- **Data safety**: All demo data is synthetic (fake phone numbers, names). For production, Firestore security rules, field-level encryption for PII, and data retention policies would be required. Out of scope for hackathon.
- **Model IDs verified**: `anthropic/claude-haiku-4-5-20251001` confirmed in SDK examples (chat_supervisor, transfer_agent, sales_with_leads). `cartesia-line==0.2.2` confirmed in `line/pyproject.toml`.

## Environment Variables Required

```
CARTESIA_API_KEY=sk_car_...          # Cartesia platform
ANTHROPIC_API_KEY=sk-ant-...         # Claude API
FIREBASE_SERVICE_ACCOUNT_PATH=...    # Path to service account JSON
BROWSERBASE_API_KEY=...              # Browserbase (Phase 5)
BROWSERBASE_PROJECT_ID=...           # Browserbase (Phase 5)
GEMINI_API_KEY=...                   # For Stagehand (Phase 5)
```

## Testing Checklist

- [ ] `python seed_data.py` populates Firestore with Smith family
- [ ] `uv run python main.py` starts without errors
- [ ] `cartesia chat 8000` connects successfully
- [ ] Device user call → personalized greeting with name
- [ ] Family member call → recognized and greeted
- [ ] Unknown caller → blocked and logged
- [ ] Leave message → saved in Firestore with correct fields
- [ ] Hear messages → reads unread, marks as read
- [ ] Companion chat handoff works
- [ ] Memory persists across calls
- [ ] Reminders: set and retrieve
- [ ] Quick web search (weather, facts) returns results
- [ ] Browserbase site navigation returns results
- [ ] Anonymous message saved without sender name
- [ ] Unknown caller → passphrase challenge → wrong answer = blocked and logged
- [ ] Unknown caller → passphrase challenge → correct answer = proceeds as guest to FamilyMemberAgent
- [ ] Guest caller (passphrase-verified) can leave message but cannot check wellness or set reminders
- [ ] Firestore console shows all data correctly
