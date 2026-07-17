# Voice pipeline and intent routing

## The pipeline

I'm using Pipecat rather than hand-rolling audio plumbing. It handles the four things that are miserable to build correctly: voice-activity detection, barge-in (cancel TTS mid-sentence and flush the pipeline when I start talking), turn-taking (deciding I'm done rather than pausing to think), and pluggable STT/LLM/TTS behind one frame-based abstraction. Hand-rolled versions of these work in a demo and fail in daily use.

Shape: `audio in (from the app, over WS) → VAD → streaming STT partials → conversation manager → sentence-chunked streaming TTS → back to the app`, with an interruption watcher that flushes everything downstream the moment I barge in, and records how much of the reply I actually heard.

For the MVP, hold-to-talk makes half of this trivial: the button press *is* the endpoint decision. The clever turn-taking models (Pipecat's smart-turn, Deepgram's Flux with end-of-turn built into the ASR) come into play in the IoT phase when there's no button.

## Latency budget

The number that matters: end of my speech → first assistant audio. Target under 1.5s, sub-1s with tuning.

| Stage | Typical | Notes |
|---|---|---|
| Endpointing | 0–600ms | Free with hold-to-talk; the silent killer once wake word arrives |
| STT finalization | 100–300ms | Mostly overlapped; partials stream during speech |
| Router LLM first token | 300–600ms | Keep the prompt small; start TTS on the first complete sentence |
| TTS first byte | 100–300ms | Flash/Sonic-class cloud, or Kokoro locally |
| **Total** | **~0.8–1.5s** | Cellular adds its tax; Tailscale + streaming keeps it tolerable |

## Decisions

**Cascade, not speech-to-speech.** The realtime APIs (OpenAI Realtime, Gemini Live) have lovely prosody and lower latency, but I'd lose model choice for the brain, text-level debuggability, and provider independence — and realtime audio pricing is hostile to something idle 95% of the day. The cascade can always grow a premium speech-to-speech mode later; Pipecat supports those transports too.

**Interruption is a conversation-manager concern.** On barge-in I record how far playback got and mark the unheard remainder undelivered, so "wait, what was that?" works and the model doesn't believe it said things I never heard.

**The transcript is an equal citizen.** Every turn is a row; the app renders the conversation with an edit box, and a corrected or typed turn goes through the same `/v1/turns` endpoint as speech. Voice and text are two clients of one API — which is also how I debug the whole system before audio exists.

**Proactive speech has manners.** Announcements queue in the notifier, not the voice pipeline. Speak only if I've been voice-active in the last few minutes; otherwise push notification plus app badge. Never talk over me; wait for an idle gap.

## Intent routing

Requests need classifying: conversation, lookup, quick command, coding task, research task, status check, follow-up, sensitive action. Two stages:

1. **Reflex rules, ~0ms.** A tiny regex layer for the vocabulary where determinism matters: "stop", "cancel that", "pause", "status". Under 20 patterns, ever. It's a fast path, not an NLU system.
2. **The fast LLM itself, via tool calls.** The conversation model gets a small tool set — `answer`, `create_task`, `continue_task`, `task_status`, `cancel_task`, `run_quick_command`, `ask_confirmation` — and routing *is* tool selection. Classification, parameter extraction ("which task? which repo?") and the spoken reply come out of one call, so routing adds no extra round trip.

Things I considered and rejected: a separate fine-tuned classifier (training-data and maintenance burden duplicating what the router does for free), pure rules (dies on "that thing from yesterday, do it on the server instead"), and routing with the big model (wrong latency and cost for every single turn).

## Model routing across the system

| Role | Model class | Why |
|---|---|---|
| Voice brain / router | Haiku-class | Sub-second first token, cheap per-turn, good tool use. Never does real work |
| Task agents | Sonnet-class default, big-model opt-in per task | Frontier capability where it pays; the task spec carries a model field |
| Summaries, close-outs, distillation | Haiku-class | High volume, low difficulty, off the critical path |
| Embeddings | voyage-lite or text-embedding-3-small | Cheap, boring |
| Local model | Maybe, much later | Offline and privacy-routed commands only; local models aren't reliable task workers yet |

Context flows *down* as a composed task prompt (spec + memory pack + workspace pointers) and results flow *up* only as structured close-outs and taskboard events. The merge point is the task record — never one model's raw transcript pasted into another's context.
