# Architecture

## System overview

The bot is a Python LiveKit Agent running in pipeline mode (separate
speech-to-text, LLM, and text-to-speech stages, per the assessment's
requirements — no realtime/speech-to-speech models). `make_call.py`
dispatches a persona-specific agent job into a LiveKit room and places an
outbound call through a Twilio Elastic SIP Trunk, configured in LiveKit as
an outbound trunk, to Pretty Good AI's test line. Once PGAI's agent
answers, both sides are participants in the same LiveKit room and
converse over real-time audio: Deepgram (Nova-3) transcribes incoming
speech, GPT-4o-mini (GPT-4o for the security-testing scenario) decides how
the persona responds, and Cartesia (Sonic) synthesizes the reply. Each
scenario is a distinct persona with its own goal and constraints, selected
at call time via job metadata so a single codebase drives all 11 test
calls without per-scenario files.

## Why this stack

Deepgram, OpenAI, and Cartesia were chosen primarily for latency, since
the eval criteria explicitly weights "realistic pacing" and "sensible
turn-taking" — a caller-simulator that reasons well but responds slowly
doesn't hold a coherent phone conversation. Deepgram Nova-3 is
purpose-built for low-latency streaming transcription and has mature
LiveKit plugin support. GPT-4o-mini gives fast, cheap responses that are
good enough to sustain a consistent persona; GPT-4o was used specifically
for the data-leak stress-test scenario, where improvising follow-up
pressure against an unexpected refusal mattered more than raw speed.
Cartesia Sonic was chosen over ElevenLabs for faster time-to-first-audio,
which matters more here than voice realism since PGAI's agent is being
evaluated on conversational flow, not on how convincing the caller sounds.
Across all 11 calls, end-to-end turn latency stayed in the 0.8-2s range,
with only isolated spikes (e.g. one cloud turn-detector timeout, handled
by an automatic fallback to a local model).

## Turn-taking and interruptions

LiveKit's built-in VAD (Silero) and adaptive interruption detector handle
the mechanics of knowing when a speaker has finished a turn and of
stopping the bot's own audio if the other party starts talking over it.
However, getting the caller-simulator to _initiate_ a genuine mid-sentence
interruption turned out to be a real limitation worth being upfront about:
the LLM only decides what to say after it receives a completed transcript
of the other side's turn, so anything scripted as "interrupt when you hear
X" actually executes right after the other party finishes, not truly
mid-utterance. This is a structural property of turn-based LLM callers,
not a bug in this implementation — a genuinely interruption-capable caller
would need to react to interim (partial) transcripts and fire speech
before end-of-turn is committed, which was judged out of scope for the
time budget here in favor of broader scenario coverage.

## Design decisions that changed during testing

Two concrete iterations came out of listening to early calls rather than
assuming the design was correct upfront:

1. **`EndCallTool` firing too early on transfers.** The tool's default
   judgment treated "I'll transfer you now" as a natural end of the
   conversation and hung up immediately — meaning the bot never heard
   what happened after a transfer. Fixed by explicitly instructing the
   tool not to end the call on a transfer/handoff announcement, and to
   wait until an actual person (or a new message) is heard first. This
   surfaced a useful finding in its own right: PGAI's "transfer" always
   resolves to the same canned goodbye message rather than a live queue
   or agent, which is a limitation of the test environment worth noting
   for anyone reading these transcripts.
2. **Scenario design shifted toward reusing a single, real patient
   record** (Jamie Carter, created and booked in the first call) rather
   than inventing a new persona identity per call. This made later
   findings — especially the Critical-severity data-leak bug — provable
   rather than speculative, since the leaked appointment details could be
   checked against a known, previously-created ground truth rather than
   trusting the model's own claim.

## Bug-finding approach

Testing proceeded from straightforward, single-intent calls (booking,
cancellation, refill, insurance) toward compounded and adversarial
scenarios (multi-step reschedule-then-cancel flows, social-engineering
attempts to extract another patient's data). This ordering was
deliberate: validating the bot's own pipeline behaved correctly on simple
calls first made later, more complex calls' failures attributable to
PGAI's system rather than to bugs in the test harness itself. See
`bug_report.md` for the full set of findings, ranked by severity.
