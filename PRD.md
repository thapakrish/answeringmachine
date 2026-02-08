# AnsweringMachine - Product Requirements Document

## 1. Product Summary

**AnsweringMachine** is a voice agent system that enables families to stay connected with elderly parents and young children through a simple phone call. A physical device (or provisioned phone number) is backed by an AI voice agent that recognizes callers, relays messages, provides companionship, and searches for local information.

**Target Users:**
- Elderly parents/grandparents who find smartphones overwhelming
- Young children who don't have their own devices
- Family members who want to stay connected without requiring the above to use apps

## 2. Functional Requirements

### FR-1: Caller Identification & Routing

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1.1 | System shall identify callers by matching `call_request.from_` against registered phone numbers in Firestore | P0 |
| FR-1.2 | System shall identify the target family by matching `call_request.to` against `device_phones` in Firestore | P0 |
| FR-1.3 | Known device users shall be routed to `DeviceUserAgent` | P0 |
| FR-1.4 | Known family members shall be routed to `FamilyMemberAgent` | P0 |
| FR-1.5 | Unknown callers shall be routed to `GatekeeperAgent` for passphrase verification | P0 |
| FR-1.6 | Failed passphrase attempts shall be logged to `unknown_call_attempts` collection and the call ended | P1 |
| FR-1.7 | Successful passphrase verification shall create a guest session with `member_id="guest"` | P1 |

### FR-2: Device User Experience (Grandma/Kid picks up)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-2.1 | Agent shall greet device user by name with time-of-day greeting | P0 |
| FR-2.2 | Agent shall announce unread message count in greeting | P0 |
| FR-2.3 | Agent shall reference recent conversation memory in greeting (if available) | P1 |
| FR-2.4 | `hear_messages` tool shall fetch unread messages from Firestore, return formatted text, and mark as read | P0 |
| FR-2.5 | `hear_reminders` tool shall fetch active reminders from Firestore | P1 |
| FR-2.6 | `set_reminder` tool shall save a reminder to Firestore | P1 |
| FR-2.7 | `quick_search` tool shall use built-in `web_search` for simple queries (weather, facts) | P1 |
| FR-2.8 | `browse_website` tool shall use Browserbase/Stagehand to navigate specific websites, running as a background tool | P2 |
| FR-2.9 | `free_conversation` shall hand off to a dedicated LlmAgent for open-ended voice conversation | P1 |
| FR-2.10 | On `CallEnded`, agent shall save a conversation summary to the memory collection | P1 |

### FR-3: Family Member Experience (Sarah/Mike calls in)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-3.1 | Agent shall greet family member by name, referencing their own recent conversation memory if available | P0 |
| FR-3.2 | `leave_message` tool shall save a message to Firestore attributed to the caller | P0 |
| FR-3.3 | `leave_anonymous` tool shall save a message with `from_name="A family member"` and `from_member_id="anonymous"` | P1 |
| FR-3.4 | `check_wellness` tool shall return recent activity, last interaction time, and conversation mood | P1 |
| FR-3.5 | `add_reminder` tool shall save a reminder for the device user | P1 |
| FR-3.6 | Agent shall confirm message content before saving | P0 |

### FR-4: Guest Access (Passphrase-verified unknown callers)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-4.1 | Guest sessions shall only have access to `leave_message` and `end_call` tools | P1 |
| FR-4.2 | Guest messages shall be attributed with `from_member_id="guest"`, `from_name="Guest"` | P1 |
| FR-4.3 | Guest sessions shall NOT have access to `check_wellness`, `add_reminder`, or `leave_anonymous` | P1 |

### FR-5: Data Persistence (Firestore)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-5.1 | Family documents shall store `name`, `device_phones[]`, `passphrase` (string field on family doc), `created_at` | P0 |
| FR-5.2 | Member documents shall store `name`, `role`, `phone_numbers[]`, `is_device_user`, `preferences` | P0 |
| FR-5.3 | Message documents shall store `from_member_id`, `from_name`, `to_member_id`, `content`, `read`, `created_at` | P0 |
| FR-5.4 | Reminder documents shall store `for_member_id`, `created_by_member_id`, `content`, `time`, `recurring`, `active` | P1 |
| FR-5.5 | Memory documents shall store `recent_conversations[]` (with optional `transcript`), `preferences`, `last_interaction`. Memory is per-member — each family member's history is private to them | P1 |
| FR-5.6 | Call log documents shall store `caller_phone`, `caller_member_id`, `caller_name`, `timestamp`, `summary`, `is_anonymous` | P1 |
| FR-5.7 | Unknown call attempts shall store `phone_number`, `target_device_phone`, `family_id`, `timestamp`, `blocked` | P1 |

### FR-6: Infrastructure (Terraform/GCP)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-6.1 | Terraform shall provision a GCP project (or use existing) with required APIs enabled | P0 |
| FR-6.2 | Terraform shall provision a Firestore database in Native mode | P0 |
| FR-6.3 | Terraform shall create a service account with Firestore read/write permissions | P0 |
| FR-6.4 | Terraform shall output the service account key path for use in `.env` | P0 |
| FR-6.5 | Terraform shall create Firestore security rules (deny all unauthenticated access). Note: requires Firebase project linkage via `google_firebase_project` resource | P2 |
| FR-6.6 | Terraform shall provision Cloud Run service for FastAPI dashboard (stretch goal) | P2 |

### FR-7: Web Dashboard (Stretch Goal)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-7.1 | `GET /api/families/{id}` shall return family info with members | P2 |
| FR-7.2 | `POST /api/families` shall create a new family | P2 |
| FR-7.3 | `POST /api/families/{id}/members` shall add a member | P2 |
| FR-7.4 | `GET /api/families/{id}/messages` shall return messages | P2 |
| FR-7.5 | `GET /api/families/{id}/call-logs` shall return call history | P2 |

## 3. Non-Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR-1 | Voice agent response latency shall be under 2 seconds for tool-free responses | P0 |
| NFR-2 | All real-time agents shall use Claude Haiku 4.5 (not Opus) | P0 |
| NFR-3 | Background tools (browse_website) shall yield an immediate acknowledgment before processing | P1 |
| NFR-4 | All demo data shall be synthetic (no real PII) | P0 |
| NFR-5 | System shall be testable via `cartesia chat <port>` in text mode | P0 |
| NFR-6 | Firestore operations shall be async (non-blocking) using `firebase-admin`'s `firestore.AsyncClient()` | P0 |
| NFR-7 | Agent shall use distinct Cartesia voices per context (Mabel/Grandma for device user, Maya/Easygoing for family member, Tessa/Kind for free conversation) | P1 |
| NFR-8 | Each family member's conversation memory shall be private — only accessible when that member calls | P0 |
| NFR-9 | Agent shall support mid-call language switching via handoff to language-specific agents with matching Cartesia voices (configured per role) | P1 |

## 4. Out of Scope

- Real hardware device integration
- Voice biometrics / speaker verification
- SMS/email notifications for blocked calls
- User registration via web UI (seed data only for hackathon)
- Firestore field-level encryption
- Production deployment to GCP (Cartesia Cloud handles agent deployment)
- ~~Multi-language support~~ (implemented: Hindi and Spanish language handoff with voice switching)

## 5. Success Criteria

The demo is successful if a judge can witness:
1. A family member calling and leaving a message (caller recognized by name)
2. The device user picking up and hearing the message (personalized greeting with memory)
3. The device user asking a question and getting a web search result
4. An unknown caller being challenged with a passphrase
5. A family member leaving an anonymous message

## 6. Assumptions

- Cartesia Line SDK v0.2.2 is stable and the `pre_call_handler` API works as documented
- `call_request.from_` reliably contains the caller's phone number for registered PSTN calls
- `firebase-admin` v6+ provides `firestore.AsyncClient()` which is compatible with the Line SDK's event loop
- Browserbase/Stagehand can navigate arbitrary websites without consistent failures
- Demo will use `cartesia chat <port>` for text-mode testing, with phone calls via Cartesia's provisioned number

## 7. Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| cartesia-line | >=0.2.2 | Voice agent framework |
| firebase-admin | >=6.0.0 | Firestore client |
| loguru | >=0.7.0 | Logging |
| python-dotenv | >=1.0.0 | Environment variables |
| stagehand | >=3.0.0 | Browserbase integration (Phase 5) |
| google-genai | >=1.26.0 | Stagehand model (Phase 5) |
| fastapi | >=0.115.0 | Web dashboard (Phase 7) |
| uvicorn | >=0.35.0 | Dashboard server (Phase 7) |
| pytest | >=8.0.0 | Testing |
| pytest-asyncio | >=0.23.0 | Async test support |
