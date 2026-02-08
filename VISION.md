# AnsweringMachine

## The Problem

Modern technology leaves two groups behind: **elderly parents** who struggle with smartphones and apps, and **young kids** who don't have their own devices yet. Family communication increasingly happens through group chats, apps, and social media — channels these groups can't access.

Meanwhile, families worry about their elderly parents' safety, forget to check in, and have no easy way to leave them a message they'll actually receive. Scam calls targeting the elderly are at an all-time high.

## The Solution

**AnsweringMachine** is a physical phone device backed by an AI voice agent. Pick it up, and you're talking to a warm, personalized assistant that knows you by name, reads your messages, reminds you to take your medicine, and can even look up what's happening at the local library this weekend.

For family members, it's a simple phone call away — leave a message, check on mom's wellbeing, or set a reminder. No app downloads. No accounts to manage. Just a phone call.

## How It Works

### For the Device User (Grandma, Grandpa, Young Kids)

Pick up the phone. That's it.

> "Good morning, Rose! You have 2 new messages. Last time we talked, you mentioned finishing that mystery novel. What would you like to do?"

- **Hear messages** from family members
- **Have a conversation** — the agent is a warm, patient conversationalist who remembers past chats
- **Ask questions** — "What's the weather this weekend?" or "Are there any events at the library?"
- **Set reminders** — "Remind me to call Sarah on Thursday"

### For Family Members (Kids, Grandkids, Spouses)

Call the family number from your own phone. The agent recognizes you by caller ID.

> "Hi Sarah! You've reached the family answering machine. Would you like to leave a message, check in, or set a reminder?"

- **Leave a message** for the device user — read back in a natural voice
- **Check wellness** — "How has Grandma been? When did she last use the phone?"
- **Set reminders** — "Remind Mom to take her medicine at 2 PM"
- **Anonymous mode** — after being recognized, choose "leave an anonymous message" so the recipient hears it as "A family member says..." (birthday surprises!)

### Security

- Only registered family phone numbers or callers who know the family passphrase can interact with the agent
- Guests (passphrase-verified) can leave messages but cannot view wellness or set reminders
- Unrecognized numbers are challenged with a passphrase; failure is blocked and logged
- No scammers, no telemarketers, no strangers

## Key Features

| Feature | Description |
|---|---|
| **Caller Identity** | Recognizes who's calling by phone number, personalizes the experience |
| **Message Relay** | Family leaves voice messages → agent reads them naturally to device user |
| **Conversation Memory** | Agent remembers past interactions: "You mentioned you were reading a mystery novel..." |
| **Local Search** | Quick web search for weather/facts + Browserbase for navigating specific sites (library, community center) |
| **Reminders** | Family or device user can set reminders (medicine, appointments, calls) |
| **Free Conversation** | Warm, patient conversational partner — not a chatbot, but a natural voice experience |
| **Anonymous Calling** | In-call option to leave a message without revealing the sender |
| **Wellness Check** | Family can ask about recent activity, mood, last interaction |
| **Unknown Caller Handling** | Unregistered numbers can verify via family passphrase, or are blocked and logged |
| **Expressive Voice** | Different Cartesia voices for different contexts — warm grandma voice for device user, casual voice for family members |
| **Language Handoff** | Mid-call language switching — if a caller speaks Hindi or asks to switch languages, the agent hands off to a language-specific agent with a matching voice |
| **Memory Privacy** | Each family member's conversation history is private to them — no cross-member leakage |

## Target Users

1. **Elderly parents/grandparents** — who find smartphones overwhelming but can pick up a phone
2. **Young children** — who don't have their own devices but want to talk to family
3. **Busy families** — who want an easy way to stay connected with loved ones across generations

## Tech Stack

| Component | Technology |
|---|---|
| Voice Agent | Cartesia Line SDK (Sonic TTS + voice pipeline) |
| LLM | Anthropic Claude Haiku 4.5 (fast, conversational) |
| Database | Firebase Firestore (accounts, messages, memory) |
| Web Search | Built-in web_search (quick queries) + Browserbase/Stagehand (site navigation) |
| Web Dashboard | FastAPI (account management) |
| Deployment | Cartesia Cloud (agent) + GCP (web app) |

## Demo Narrative (2 minutes)

**Act 1 — Sarah leaves a message (30s)**
Sarah calls the family number. The agent greets her by name. She leaves a message for Grandma about Sunday dinner and sets a medicine reminder.

**Act 2 — Grandma picks up (45s)**
Rose picks up the device. "Good morning, Rose! You have 1 new message. Last time we talked, you were finishing a mystery novel." She hears Sarah's message, asks about Sunday's weather (web search), then asks the agent to look up library events (Browserbase navigates the library website). Has an open-ended conversation about her book.

**Act 3 — Unknown caller with passphrase (15s)**
Unknown number calls. "I don't recognize this number. If you're a family member, please say the family passphrase." Caller says passphrase → verified and connected. Wrong answer → blocked and logged.

**Act 4 — Anonymous surprise (15s)**
Mike calls from his registered number. Chooses to leave an anonymous message: "I hid your birthday present in the garage." Rose hears it later as "A family member says..."

## Why This Wins

1. **Real human need** — elderly isolation and family disconnection are growing problems
2. **All sponsor tech** — Cartesia (voice), Anthropic (LLM), Browserbase (web), Firebase (data)
3. **Technically impressive** — multi-agent routing, caller identification, conversation memory, real-time web search
4. **Emotionally compelling** — "Last time we talked, you mentioned..." creates genuine connection
5. **Broad market** — works for elderly AND kids, families of all sizes
