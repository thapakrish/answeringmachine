# AnsweringMachine - Implementation Tasks

> TDD approach: each task specifies tests to write FIRST, then implementation to make them pass.

## Legend

- **Priority**: P0 (must have), P1 (should have), P2 (stretch goal)
- **Status**: `[ ]` todo, `[~]` in progress, `[x]` done
- **Deps**: tasks that must be completed first
- **PRD**: requirement IDs this task satisfies

---

## Phase 0: Infrastructure (Terraform + Project Setup)

### Task 0.1: Terraform GCP Setup
- **Priority**: P0
- **Deps**: none
- **PRD**: FR-6.1, FR-6.2, FR-6.3, FR-6.4
- **Status**: `[ ]`

**Tests first:**
```
tests/test_infra.py
- test_terraform_plan_succeeds: run `terraform plan` and assert exit code 0
- test_firestore_database_exists: after apply, verify Firestore DB exists via API
- test_service_account_key_exists: verify key file is generated at expected path
```

**Implementation:**
```
infra/
  main.tf              # Provider, project, APIs
  firestore.tf         # Firestore database (Native mode)
  iam.tf               # Service account + roles
  outputs.tf           # Service account key path
  variables.tf         # Project ID, region
  terraform.tfvars     # Actual values (gitignored)
```

**Terraform resources:**
- `google_project_service`: Enable Firestore API
- `google_firestore_database`: Native mode database
- `google_service_account`: For firebase-admin SDK
- `google_project_iam_member`: `roles/datastore.user` on service account
- `google_service_account_key`: JSON key output
- `local_file`: Write key to `service-account.json`

**Verify:** `terraform plan` succeeds, `terraform apply` creates resources, service account key works with firebase-admin.

---

### Task 0.2: Project Scaffolding
- **Priority**: P0
- **Deps**: none (parallel with 0.1)
- **PRD**: NFR-5
- **Status**: `[ ]`

**Tests first:**
```
tests/test_scaffold.py
- test_pyproject_has_required_deps: parse pyproject.toml, assert cartesia-line, firebase-admin, loguru, pytest
- test_agents_package_importable: import agents package
- test_tools_package_importable: import tools package
```

**Implementation:**
```
pyproject.toml
agents/__init__.py
agents/prompts.py       # Empty prompt constants (filled in later tasks)
tools/__init__.py
tests/__init__.py
tests/conftest.py       # Shared fixtures
```

**Verify:** `uv sync` installs deps, `pytest tests/test_scaffold.py` passes.

---

## Phase 1: Firebase Client + Seed Data

### Task 1.1: FirebaseClient - Family & Member Lookup
- **Priority**: P0
- **Deps**: 0.1, 0.2
- **PRD**: FR-5.1, FR-5.2, FR-1.1, FR-1.2
- **Status**: `[ ]`

**Tests first:**
```
tests/test_firebase_client.py
- test_find_family_by_device_phone_found: seed a family, lookup by device phone, assert match
- test_find_family_by_device_phone_not_found: lookup unknown phone, assert None
- test_find_member_by_phone_found: seed a member, lookup by phone, assert match
- test_find_member_by_phone_not_found: lookup unknown phone, assert None
- test_get_primary_device_user: seed family with device user, assert correct member returned
- test_get_primary_device_user_none: family with no device user, assert None
```

**Implementation:**
```
firebase_client.py
  class FirebaseClient:
    __init__(self)                           # Init firebase_admin + firestore_async client
    find_family_by_device_phone(phone)       # Query families where device_phones contains phone
    find_member_by_phone(family_id, phone)   # Query members where phone_numbers contains phone
    get_primary_device_user(family_id)       # Query members where is_device_user=True
```

**Verify:** `pytest tests/test_firebase_client.py` passes against real Firestore (or emulator).

---

### Task 1.2: Seed Data Script
- **Priority**: P0
- **Deps**: 1.1
- **PRD**: FR-5.1, FR-5.2
- **Status**: `[ ]`

**Tests first:**
```
tests/test_seed_data.py
- test_seed_creates_family: run seed, assert family doc exists with correct fields
- test_seed_creates_members: run seed, assert 4 members exist (Rose, Sarah, Mike, Emma)
- test_seed_creates_messages: run seed, assert 2 pre-loaded messages exist
- test_seed_creates_reminders: run seed, assert 2 pre-loaded reminders exist
- test_seed_creates_memory: run seed, assert memory doc exists for Rose
- test_seed_creates_passphrase: run seed, assert family has passphrase field
- test_seed_is_idempotent: run seed twice, assert no duplicates
```

**Implementation:**
```
seed_data.py
  async def seed():
    - Create "The Smiths" family with device_phones, passphrase
    - Create 4 members (Rose, Sarah, Mike, Emma)
    - Create 2 messages (from Sarah, from Mike)
    - Create 2 reminders (medicine, doctor)
    - Create memory for Rose (mystery novels, gardening)
    - Idempotent: delete + recreate or check-before-create
```

**Verify:** `python seed_data.py` populates Firestore, visible in Firebase Console.

---

## Phase 2: Core Agent Routing (main.py)

### Task 2.1: pre_call_handler - Caller Identification
- **Priority**: P0
- **Deps**: 1.1
- **PRD**: FR-1.1, FR-1.2, FR-1.3, FR-1.4, FR-1.5
- **Status**: `[ ]`

**Tests first:**
```
tests/test_pre_call_handler.py
- test_device_user_identified: mock call_request with device phone as from_, assert metadata.is_device_user=True
- test_family_member_identified: mock call_request with Sarah's phone, assert metadata.member_name="Sarah"
- test_unknown_caller_flagged: mock call_request with unknown phone, assert metadata.is_authorized=False
- test_family_not_found_returns_none: mock call_request to unknown device phone, assert returns None (reject)
- test_metadata_has_required_fields: assert metadata contains family_id, member_id, member_name, member_role, is_device_user, caller_phone, device_phone
```

**Implementation:**
```
main.py
  pre_call_handler(call_request) -> PreCallResult | None
    - Lookup family by call_request.to
    - If no family: return None
    - Lookup member by call_request.from_
    - Check if caller IS the device user
    - Return PreCallResult with metadata dict
```

**Verify:** Unit tests pass with mocked Firestore.

---

### Task 2.2: get_agent - Agent Factory
- **Priority**: P0
- **Deps**: 2.1
- **PRD**: FR-1.3, FR-1.4, FR-1.5
- **Status**: `[ ]`

**Tests first:**
```
tests/test_get_agent.py
- test_device_user_gets_device_user_agent: metadata.is_device_user=True → isinstance DeviceUserAgent
- test_family_member_gets_family_member_agent: metadata.is_device_user=False, is_authorized=True → isinstance FamilyMemberAgent
- test_unauthorized_gets_gatekeeper_agent: metadata.is_authorized=False → isinstance GatekeeperAgent
- test_guest_gets_family_member_agent_with_guest_flag: is_guest=True → FamilyMemberAgent with is_guest=True
```

**Implementation:**
```
main.py
  get_agent(env, call_request) -> Agent
    - Read metadata from call_request
    - Route to DeviceUserAgent, FamilyMemberAgent, or GatekeeperAgent
```

**Verify:** Unit tests pass. `uv run python main.py` starts without errors.

---

### Task 2.3: System Prompts
- **Priority**: P0
- **Deps**: 0.2
- **PRD**: FR-2.1, FR-3.1
- **Status**: `[ ]`

**Tests first:**
```
tests/test_prompts.py
- test_device_user_prompt_has_placeholders: assert {member_name}, {member_role}, {preferences}, {memory_context} in prompt
- test_family_member_prompt_has_placeholders: assert {member_name}, {device_user_name}, {member_role} in prompt
- test_companion_prompt_has_placeholder: assert {member_name} in prompt
- test_gatekeeper_prompt_exists: assert GATEKEEPER_PROMPT is non-empty string
- test_prompts_no_emoji: assert no emoji characters in any prompt
```

**Implementation:**
```
agents/prompts.py
  DEVICE_USER_GREETER_PROMPT    # Warm, patient, memory-aware
  FAMILY_MEMBER_GREETER_PROMPT  # Efficient, helpful
  COMPANION_PROMPT              # Friendly chat partner
  GATEKEEPER_PROMPT             # Passphrase challenge
```

**Verify:** `pytest tests/test_prompts.py` passes.

---

## Phase 3: Device User Agent

### Task 3.1: DeviceUserAgent - Minimal (Greeting + end_call)
- **Priority**: P0
- **Deps**: 2.2, 2.3
- **PRD**: FR-2.1, NFR-2
- **Status**: `[ ]`

**Tests first:**
```
tests/test_device_user_agent.py
- test_agent_is_agent_class: assert isinstance(DeviceUserAgent, AgentClass) or has process method
- test_agent_uses_haiku: assert model contains "haiku" (via agent.model_id)
- test_agent_has_end_call_tool: assert end_call in tools list (via agent.tool_names())
- test_greeting_contains_name: mock process with CallStarted, assert AgentSendText contains member_name
```

**Implementation:**
```
agents/device_user_agent.py
  class DeviceUserAgent(AgentClass):
    __init__(metadata, db)
    process(env, event) -> AsyncIterable[OutputEvent]
      - On CallStarted: yield greeting
      - On CallEnded: cleanup
      - Otherwise: delegate to _greeter LlmAgent
    model_id: str
    tool_names() -> list[str]
```

**Verify:** `pytest tests/test_device_user_agent.py` passes. `cartesia chat 8000` shows greeting.

---

### Task 3.2: hear_messages Tool
- **Priority**: P0
- **Deps**: 3.1, 1.1
- **PRD**: FR-2.4, FR-5.3
- **Status**: `[ ]`

**Tests first:**
```
tests/test_message_tools.py
- test_hear_messages_returns_formatted_text: seed 2 messages, call tool, assert both messages in result
- test_hear_messages_marks_as_read: seed messages, call tool, assert messages now have read=True
- test_hear_messages_no_messages: no messages seeded, assert "No new messages" in result
- test_hear_messages_only_unread: seed 1 read + 1 unread, assert only unread in result
```

**Implementation:**
```
tools/message_tools.py (or as methods on DeviceUserAgent)
  hear_messages(ctx) -> str
    - Fetch unread messages from Firestore
    - Format: "Message 1 from Sarah: ..."
    - Mark all as read
    - Return formatted string
```

---

### Task 3.3: leave_message Tool
- **Priority**: P0
- **Deps**: 1.1
- **PRD**: FR-3.2, FR-3.6, FR-5.3
- **Status**: `[ ]`

**Tests first:**
```
tests/test_message_tools.py
- test_leave_message_saves_to_firestore: call tool with content, assert message doc created with correct fields
- test_leave_message_has_correct_attribution: assert from_member_id and from_name match caller
- test_leave_message_defaults_to_unread: assert read=False on saved message
- test_leave_message_has_timestamp: assert created_at is set
```

**Implementation:**
```
tools/message_tools.py (or as methods on FamilyMemberAgent)
  leave_message(ctx, message_content) -> str
    - Save message to Firestore
    - Return confirmation string
```

---

## Phase 4: Family Member Agent

### Task 4.1: FamilyMemberAgent - Minimal (Greeting + end_call)
- **Priority**: P0
- **Deps**: 2.2, 2.3
- **PRD**: FR-3.1, NFR-2
- **Status**: `[ ]`

**Tests first:**
```
tests/test_family_member_agent.py
- test_agent_is_agent_class: has process method
- test_agent_uses_haiku: model contains "haiku" (via agent.model_id)
- test_agent_has_end_call_tool: end_call in tools (via agent.tool_names())
- test_greeting_contains_name: assert AgentSendText contains member_name
- test_guest_mode_excludes_wellness: is_guest=True → check_wellness NOT in tools
- test_guest_mode_excludes_reminder: is_guest=True → add_reminder NOT in tools
- test_guest_mode_excludes_anonymous: is_guest=True → leave_anonymous NOT in tools
- test_normal_mode_includes_all_tools: is_guest=False → all tools present
```

**Implementation:**
```
agents/family_member_agent.py
  class FamilyMemberAgent(AgentClass):
    __init__(metadata, db, is_guest=False)
      - Conditionally include tools based on is_guest
    process(env, event) -> AsyncIterable[OutputEvent]
    model_id: str
    tool_names() -> list[str]
```

**Verify:** `pytest tests/test_family_member_agent.py` passes. Guest tool restriction enforced.

---

### Task 4.2: leave_anonymous Tool
- **Priority**: P1
- **Deps**: 3.3
- **PRD**: FR-3.3
- **Status**: `[ ]`

**Tests first:**
```
tests/test_message_tools.py
- test_leave_anonymous_from_name: call tool, assert from_name="A family member"
- test_leave_anonymous_from_id: assert from_member_id="anonymous"
- test_leave_anonymous_content_saved: assert content matches input
```

**Implementation:**
```
tools/message_tools.py
  leave_anonymous(ctx, message_content) -> str
    - Save message with from_member_id="anonymous", from_name="A family member"
```

---

## Phase 5: Memory System

### Task 5.1: FirebaseClient - Memory Operations
- **Priority**: P1
- **Deps**: 1.1
- **PRD**: FR-5.5
- **Status**: `[ ]`

**Tests first:**
```
tests/test_firebase_client.py
- test_get_memory_exists: seed memory, assert correct fields returned
- test_get_memory_not_exists: no memory seeded, assert empty defaults returned
- test_save_memory_creates_doc: save memory, assert doc created
- test_save_memory_appends_conversation: save twice, assert 2 entries in recent_conversations
- test_save_memory_caps_at_20: save 25 times, assert only last 20 kept
- test_save_memory_updates_last_interaction: assert last_interaction timestamp updated
```

**Implementation:**
```
firebase_client.py
  get_memory(family_id, member_id) -> dict
  save_memory(family_id, member_id, summary, topics, mood) -> None
```

---

### Task 5.2: Dynamic Greeting with Memory
- **Priority**: P1
- **Deps**: 3.1, 5.1
- **PRD**: FR-2.1, FR-2.2, FR-2.3
- **Status**: `[ ]`

**Tests first:**
```
tests/test_device_user_agent.py
- test_greeting_includes_time_of_day: mock morning → "Good morning", mock evening → "Good evening"
- test_greeting_includes_unread_count: seed 3 messages → "3 new messages" in greeting
- test_greeting_includes_memory: seed memory with "mystery novel" → referenced in greeting
- test_greeting_no_memory: no memory → no memory reference, still works
- test_greeting_no_messages: 0 unread → no message mention or "no new messages"
```

**Implementation:**
- Modify DeviceUserAgent `CallStarted` handler to build dynamic intro from memory + unread count.

---

### Task 5.3: Save Memory on CallEnded
- **Priority**: P1
- **Deps**: 5.1
- **PRD**: FR-2.10
- **Status**: `[ ]`

**Tests first:**
```
tests/test_device_user_agent.py
- test_call_ended_saves_memory: process CallEnded event, assert save_memory called
- test_call_ended_cleans_up: process CallEnded, assert agent cleanup called
```

**Implementation:**
- On `CallEnded` in DeviceUserAgent, summarize conversation and call `save_memory()`.

---

## Phase 6: Companion Chat

### Task 6.1: Companion Chat Handoff
- **Priority**: P1
- **Deps**: 3.1
- **PRD**: FR-2.9
- **Status**: `[ ]`

**Tests first:**
```
tests/test_device_user_agent.py
- test_companion_agent_exists: assert _companion is an LlmAgent
- test_companion_handoff_tool_exists: assert "companion_chat" in tool names
- test_companion_uses_haiku: assert _companion model contains "haiku"
```

**Implementation:**
- Add `_companion` LlmAgent to DeviceUserAgent
- Add `agent_as_handoff` wrapping `_companion` to greeter's tools

---

## Phase 7: Reminders

### Task 7.1: FirebaseClient - Reminder Operations
- **Priority**: P1
- **Deps**: 1.1
- **PRD**: FR-5.4
- **Status**: `[ ]`

**Tests first:**
```
tests/test_firebase_client.py
- test_save_reminder: save reminder, assert doc created with correct fields
- test_get_reminders: seed reminders, assert correct list returned
- test_get_reminders_only_active: seed active + inactive, assert only active returned
- test_get_reminders_filters_by_member: seed for 2 members, assert correct filtering
```

**Implementation:**
```
firebase_client.py
  save_reminder(family_id, for_member_id, created_by_id, content, time_str, recurring)
  get_reminders(family_id, member_id) -> list[dict]
```

---

### Task 7.2: Reminder Tools (set, hear, add)
- **Priority**: P1
- **Deps**: 7.1
- **PRD**: FR-2.5, FR-2.6, FR-3.5
- **Status**: `[ ]`

**Tests first:**
```
tests/test_reminder_tools.py
- test_set_reminder_saves: call set_reminder, assert saved to Firestore
- test_hear_reminders_returns_formatted: seed reminders, call tool, assert formatted text
- test_hear_reminders_empty: no reminders, assert "no reminders" message
- test_add_reminder_saves_for_device_user: family member adds reminder, assert for_member_id is device user
```

**Implementation:**
```
tools/reminder_tools.py
  set_reminder(ctx, content, time) -> str          # DeviceUserAgent
  hear_reminders(ctx) -> str                       # DeviceUserAgent
  add_reminder(ctx, content, time) -> str           # FamilyMemberAgent
```

---

## Phase 8: Wellness Check

### Task 8.1: FirebaseClient - Activity Query
- **Priority**: P1
- **Deps**: 1.1, 5.1
- **PRD**: FR-3.4
- **Status**: `[ ]`

**Tests first:**
```
tests/test_firebase_client.py
- test_get_recent_activity_returns_memory: seed memory, assert included in result
- test_get_recent_activity_returns_call_logs: seed call logs, assert included
- test_get_recent_activity_limits_calls: seed 10 calls, assert only last 5 returned
```

**Implementation:**
```
firebase_client.py
  get_recent_activity(family_id, member_id) -> dict
    - Fetch memory + last 5 call logs
```

---

### Task 8.2: check_wellness Tool
- **Priority**: P1
- **Deps**: 8.1
- **PRD**: FR-3.4
- **Status**: `[ ]`

**Tests first:**
```
tests/test_wellness_tools.py
- test_check_wellness_returns_activity: seed data, call tool, assert last_interaction in result
- test_check_wellness_returns_mood: seed memory with mood, assert mood in result
- test_check_wellness_not_available_for_guests: is_guest=True → tool not in tools list (tested in 4.1)
```

**Implementation:**
```
tools/wellness_tools.py (or method on FamilyMemberAgent)
  check_wellness(ctx) -> str
    - Fetch recent activity
    - Format summary for LLM
```

---

## Phase 9: Search Tools

### Task 9.1: quick_search (web_search)
- **Priority**: P1
- **Deps**: 3.1
- **PRD**: FR-2.7
- **Status**: `[ ]`

**Tests first:**
```
tests/test_search_tools.py
- test_quick_search_tool_exists: assert web_search or quick_search in DeviceUserAgent tools
- test_quick_search_is_not_background: assert tool is not a background tool (instant response)
```

**Implementation:**
- Add built-in `web_search` tool to DeviceUserAgent's greeter tools list.
- May need a wrapper to rename for clarity in the prompt.

---

### Task 9.2: browse_website (Browserbase)
- **Priority**: P2
- **Deps**: 3.1
- **PRD**: FR-2.8
- **Status**: `[ ]`

**Tests first:**
```
tests/test_search_tools.py
- test_browse_website_tool_exists: assert browse_website in tools
- test_browse_website_is_background: assert tool is decorated with is_background=True
- test_browse_website_yields_acknowledgment: call tool, assert first yield is "Let me look that up..."
```

**Implementation:**
```
tools/search_tools.py
  @loopback_tool(is_background=True)
  browse_website(ctx, url, query) -> AsyncIterable[str]
    - yield acknowledgment
    - Init Stagehand session
    - Navigate to URL
    - Extract relevant info
    - yield results
    - Cleanup session
```

---

## Phase 10: Gatekeeper Agent

### Task 10.1: GatekeeperAgent
- **Priority**: P1
- **Deps**: 2.2, 1.1
- **PRD**: FR-1.5, FR-1.6, FR-1.7, FR-4.1, FR-4.2, FR-4.3
- **Status**: `[ ]`

**Tests first:**
```
tests/test_gatekeeper_agent.py
- test_gatekeeper_has_process_method: assert has process method
- test_gatekeeper_fetches_passphrase: mock DB, assert get_passphrase called with correct family_id
- test_correct_passphrase_yields_welcome: simulate correct passphrase, assert welcome message
- test_wrong_passphrase_yields_rejection: simulate wrong passphrase, assert rejection + end_call
- test_wrong_passphrase_logs_attempt: simulate wrong passphrase, assert log_unknown_call called
- test_guest_session_metadata: after correct passphrase, assert member_id="guest", from_name="Guest"
```

**Implementation:**
```
agents/gatekeeper_agent.py (or in family_member_agent.py)
  class GatekeeperAgent(AgentClass):
    __init__(metadata, db)
    process(env, event)
      - On CallStarted: ask for passphrase
      - On UserTextSent: verify passphrase
        - Correct: handoff to FamilyMemberAgent(is_guest=True) via agent_as_handoff or app-supported agent transition
        - Wrong: log + end_call
```

---

### Task 10.2: FirebaseClient - Passphrase & Logging
- **Priority**: P1
- **Deps**: 1.1
- **PRD**: FR-5.1, FR-5.7, FR-1.6
- **Status**: `[ ]`

**Tests first:**
```
tests/test_firebase_client.py
- test_get_passphrase: seed family with passphrase, assert returned correctly
- test_get_passphrase_no_passphrase: family without passphrase, assert None or empty string
- test_log_unknown_call: call method, assert doc created in unknown_call_attempts
- test_log_call: call method, assert doc created in call_logs with correct fields
```

**Implementation:**
```
firebase_client.py
  get_passphrase(family_id) -> str | None
  log_unknown_call(phone, device_phone, family_id) -> None
  log_call(family_id, caller_phone, member_id, member_name, summary, is_anonymous) -> None
```

---

## Phase 11: Integration Testing

### Task 11.1: End-to-End Call Flow Tests
- **Priority**: P0
- **Deps**: all above
- **PRD**: Success Criteria
- **Status**: `[ ]`

**Tests:**
```
tests/test_e2e.py
- test_device_user_full_flow: seed data → create DeviceUserAgent → process CallStarted → assert greeting → process "read messages" → assert messages read → process CallEnded → assert memory saved
- test_family_member_leave_message_flow: create FamilyMemberAgent → process "leave message for grandma" → assert message in Firestore
- test_unknown_caller_passphrase_correct: create GatekeeperAgent → process correct passphrase → assert guest session created
- test_unknown_caller_passphrase_wrong: create GatekeeperAgent → process wrong passphrase → assert call ended + logged
- test_guest_cannot_check_wellness: create FamilyMemberAgent(is_guest=True) → assert check_wellness not in tools
- test_anonymous_message_attribution: leave_anonymous → assert from_name="A family member"
```

---

## Phase 12: Web Dashboard (Stretch)

### Task 12.1: FastAPI Dashboard
- **Priority**: P2
- **Deps**: 1.1
- **PRD**: FR-7.1 through FR-7.5
- **Status**: `[ ]`

**Tests first:**
```
tests/test_dashboard.py
- test_get_family: GET /api/families/{id} → 200 with family data
- test_get_family_not_found: GET unknown id → 404
- test_create_family: POST /api/families → 201
- test_add_member: POST /api/families/{id}/members → 201
- test_get_messages: GET /api/families/{id}/messages → 200 with list
- test_get_call_logs: GET /api/families/{id}/call-logs → 200 with list
```

**Implementation:**
```
web/dashboard.py
  FastAPI app with CRUD endpoints backed by FirebaseClient
```

---

## Task Dependency Graph

```
0.1 (Terraform) ──┐
                   ├── 1.1 (Firebase Client) ── 1.2 (Seed Data)
0.2 (Scaffold) ───┘         │
                             ├── 2.1 (pre_call_handler)
                             │         │
                             │         ├── 2.2 (get_agent)
                             │         │       │
                    2.3 (Prompts) ─────┤       │
                             │         │       │
                             ├── 3.1 (DeviceUserAgent minimal)
                             │    │    ├── 3.2 (hear_messages)
                             │    │    ├── 5.2 (dynamic greeting)
                             │    │    ├── 6.1 (companion chat)
                             │    │    ├── 9.1 (quick_search)
                             │    │    └── 9.2 (browse_website)
                             │    │
                             │    ├── 5.1 (memory ops) ── 5.3 (save on CallEnded)
                             │    │                   └── 8.1 (activity query)
                             │    │
                             │    └── 7.1 (reminder ops) ── 7.2 (reminder tools)
                             │
                             ├── 3.3 (leave_message) ── 4.2 (leave_anonymous)
                             │
                             ├── 4.1 (FamilyMemberAgent minimal)
                             │                        └── 8.2 (check_wellness)
                             │
                             ├── 10.2 (passphrase/logging ops)
                             │         └── 10.1 (GatekeeperAgent)
                             │
                             └── 11.1 (E2E tests)
                                       └── 12.1 (Dashboard, stretch)
```

## Parallelization Opportunities

These tasks can be worked on simultaneously by different team members:

| Stream A (Voice Agents) | Stream B (Data Layer) | Stream C (Infra) |
|---|---|---|
| 2.3 Prompts | 1.1 Firebase Client | 0.1 Terraform |
| 3.1 DeviceUserAgent | 1.2 Seed Data | 0.2 Scaffold |
| 4.1 FamilyMemberAgent | 5.1 Memory Ops | |
| 6.1 Companion Chat | 7.1 Reminder Ops | |
| 10.1 GatekeeperAgent | 8.1 Activity Query | |
| | 10.2 Passphrase Ops | |
