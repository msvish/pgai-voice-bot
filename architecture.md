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

## Design tradeoffs

### Speech-to-text

| Option                       | Why it was in consideration                                               | Why not chosen                                                                                                             |
| ---------------------------- | ------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| **Deepgram Nova-3** (chosen) | Purpose-built for real-time streaming, low latency, mature LiveKit plugin | —                                                                                                                          |
| OpenAI Whisper (API)         | High accuracy, well-known                                                 | Not designed for streaming/real-time use — noticeably higher latency, would slow down every turn                           |
| AssemblyAI                   | Also real-time capable, good accuracy                                     | Less established LiveKit plugin support at time of building; no clear latency advantage over Deepgram to justify switching |

**Decision:** Deepgram Nova-3, because turn latency mattered more than marginal accuracy gains — a caller-simulator judged on "realistic pacing" can't afford a slow transcription step.

### LLM

| Option                                     | Why it was in consideration                                     | Why not chosen                                                                                                                             |
| ------------------------------------------ | --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| **GPT-4o-mini** (chosen, default)          | Fast, cheap, good enough reasoning to hold a consistent persona | —                                                                                                                                          |
| **GPT-4o** (chosen, for one scenario only) | Better at improvising under pressure                            | Higher cost/latency — not worth it for straightforward scenarios                                                                           |
| Smaller open-weight models (e.g. via Groq) | Extremely low latency                                           | Weaker persona consistency and instruction-following in early informal testing; not worth the reliability tradeoff for a graded submission |

**Decision:** GPT-4o-mini as the default outweighed everything else on cost and speed for simple, well-defined personas. GPT-4o was used for the `data_leak_stress_test_run[1,2]`,`data_leak_verified_patient_lookup` scenarios, where adapting follow-up pressure after an unexpected refusal mattered more than speed — where accepting higher latency was worth it.

### Text-to-speech

| Option                      | Why it was in consideration                                           | Why not chosen                                                                                                                                              |
| --------------------------- | --------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Cartesia Sonic** (chosen) | Built specifically for low time-to-first-audio in streaming use cases | —                                                                                                                                                           |
| ElevenLabs                  | Higher perceived voice realism/naturalness                            | Slower time-to-first-audio; voice realism matters less here since PGAI's agent is evaluated on conversational flow, not on how convincing the caller sounds |
| PlayHT                      | Also low-latency streaming option                                     | Less mature LiveKit plugin support, no clear advantage over Cartesia                                                                                        |

**Decision:** Cartesia Sonic — latency directly affects whether turn-taking feels natural, which is a criterion the assessment explicitly grades on; voice quality is a secondary concern for this use case.

### Telephony / connecting to the phone network

| Option                                                                | Why it was in consideration                                                             | Why not chosen                                                                                                                                                                                                                                  |
| --------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **LiveKit outbound SIP trunk + Twilio Elastic SIP Trunking** (chosen) | LiveKit has first-class SIP support; Twilio is a well-documented, reliable PSTN gateway | —                                                                                                                                                                                                                                               |
| Hosted voice-agent platforms (Vapi, Retell, Bland)                    | Would handle telephony out of the box                                                   | Explicitly disallowed by the assessment's requirements                                                                                                                                                                                          |
| Twilio's own Voice API directly (no LiveKit)                          | Simpler telephony-only setup                                                            | Would require building the STT/LLM/TTS pipeline orchestration and turn-taking logic from scratch instead of using LiveKit Agents' existing framework — much more engineering for no real benefit given LiveKit's SIP integration already exists |

**Decision:** LiveKit's SIP trunk feature connected directly to Twilio, because it let the whole system (telephony + pipeline + turn detection) live in one framework rather than gluing together two separate systems. Twilio was chosen over other SIP providers mainly for documentation quality and ease of setup within a short project timeline, not because of any measured advantage over alternatives.

### Turn detection and interruptions

| Option                                                                                             | Why it was in consideration                                                                                              | Why not chosen                                                                                                                                                                                                                                                                                                                                                               |
| -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **LiveKit's built-in Silero VAD + adaptive interruption detector** (chosen)                        | Ships with the framework, handles the mechanics of turn-end detection and cutting off the bot's own audio if talked over | —                                                                                                                                                                                                                                                                                                                                                                            |
| Fixed-duration silence timeout (naive VAD only)                                                    | Simpler to reason about                                                                                                  | Less accurate — either cuts callers off too early or leaves long, unnatural pauses; LiveKit's adaptive model already does this better out of the box                                                                                                                                                                                                                         |
| Custom interim-transcript-triggered interruption (bot interrupts PGAI's agent mid-sentence on cue) | Would enable genuinely realistic barge-in scenarios                                                                      | Requires bypassing the standard turn-based response flow entirely — reacting to partial transcripts instead of completed turns. Evaluated as a stretch goal, but scoped out: the engineering cost was high relative to the single line item it would address, versus spending that time on broader scenario coverage (11 calls across every menu path plus security testing) |

**Decision:** Used LiveKit's built-in turn detection as-is, and accepted the caller-simulator's inherent limitation on true audio-level interruptions (it reacts to a turn's _content_ after the fact, not to real-time audio timing). This tradeoff was made deliberately in favor of test coverage breadth over depth on one specific mechanic.

### Latency

The main latency lever was staying within LiveKit's pipeline mode using streaming plugins at every stage (Deepgram, GPT-4o-mini, Cartesia all support streaming rather than batch responses), which keeps time-to-first-audio low even though three separate services are chained together. Across all 11 calls, end-to-end turn latency stayed in the 0.8-2s range, with one isolated spike caused by a cloud turn-detector timeout that correctly fell back to a local model rather than stalling the call.

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
