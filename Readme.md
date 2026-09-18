# PGAI Voice Bot

An automated caller-simulator built with [LiveKit Agents](https://docs.livekit.io/agents/)
that dials Pretty Good AI's test clinic line, runs realistic patient
personas through a variety of scenarios, and surfaces bugs in their voice
agent's responses.

## How it works

The bot places outbound calls over a Twilio SIP trunk into a LiveKit room,
where a pipeline agent (Deepgram STT → OpenAI LLM → Cartesia TTS) plays the
role of a patient calling the clinic. Each scenario is a distinct persona
with its own goal (book an appointment, request a refill, dispute a
charge, attempt a data-leak exploit, etc.), selected at call time via a
scenario name passed as job metadata. See `ARCHITECTURE.md` for design
rationale and tradeoffs.

## Setup

**Accounts needed:**

- [LiveKit Cloud](https://cloud.livekit.io) project
- [Twilio](https://www.twilio.com) account with an Elastic SIP Trunk configured for outbound calling, connected to LiveKit as an outbound trunk
- [Deepgram](https://deepgram.com) API key
- [OpenAI](https://platform.openai.com) API key
- [Cartesia](https://cartesia.ai) API key

**Install:**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Configure:** copy `.env.example` to `.env` and fill in all values (LiveKit
credentials, provider API keys, and your LiveKit SIP outbound trunk ID).

## Run

Start the agent worker (leave running in one terminal):

```bash
python agent.py dev
```

In a second terminal, trigger a call for a given scenario:

```bash
python make_call.py <scenario_name>
```

Available scenarios (defined in `agent.py`'s `SCENARIOS` dict):
`book_appointment`, `cancel_appointment`, `list_reschedule_cancel`,
`early_refill`, `insurance_update`, `confused_billing`,
`general_questions_edge`, `data_leak_stress_tes_run1_`,`data_leak_stress_test_run2`,`book_appointment_2`,
`data_leak_verified_patient_lookup`

If a room ever gets stuck open (e.g. after a crash), clean it up manually:

```bash
python end_call.py <room_name>
```

## Project structure

- agent.py — LiveKit worker: defines personas and the STT/LLM/TTS pipeline
- make_call.py — dispatches the agent and dials the test line for a given scenario
- end_call.py — manual utility to force-delete a stuck LiveKit room
- archive/ — early passthrough-only proof-of-concept, kept for reference
- recordings/ — call audio (.ogg) for all 11 test calls
- transcripts/ — corresponding transcripts for each call
- bug_report.md — documented findings, ranked by severity
- ARCHITECTURE.md — design decisions and tradeoffs

## Test call details

- 11 calls placed, all from the same phone number (used consistently as required)
- Full recordings and transcripts for each call are in `/recordings` and `/transcripts`
- See `bug_report.md` for findings (1 Critical, 4 High, 2 Medium)
