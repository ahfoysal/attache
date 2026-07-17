# Decisions

Choices I've already made, with the reasoning, so future me stops relitigating them. Reversible if reality disagrees.

**React Native over Flutter.** I live in React and TypeScript; Flutter would mean learning Dart to build what is, honestly, four screens and a websocket. Expo covers mic capture, background audio and push notifications well enough, and if I ever hit a native audio wall there's the bare-workflow escape hatch. Flutter's rendering advantages buy me nothing here.

**Mobile before desktop, phone before wake word.** The value shows up away from the keyboard. Also, hold-to-talk on a phone sidesteps the two hardest voice problems (wake-word accuracy and knowing when you've finished speaking) until the rest of the system deserves the effort.

**Cascade (STT → model → TTS) over realtime speech-to-speech APIs.** Cheaper by a lot for something idle most of the day, debuggable as text, and I keep free choice of the reasoning model. The realtime APIs can slot in later as a premium conversation mode if the latency ever feels bad.

**One agent session per task.** Isolation matches how tasks actually behave. Yesterday's server debugging should never bleed into today's research. Cross-task continuity flows through the task records and memory, where I can read and correct it, not through a shared context window I can't see into.

**A custom task state machine over Temporal or similar.** The durable-resume problem is mostly solved by the agent SDK's session files; what's left is a few hundred lines of state transitions on Postgres that I'll fully understand at 2am. Workflow engines are the right answer to a problem I don't have yet.

**Python core, React Native shell.** Splitting languages is a real cost, but the voice tooling and the strongest pipeline libraries are Python-first, and the app side is thin. Two processes, one language each, is a shape I already run in other projects.

**Approvals for anything outward, forever.** Pushing code, opening PRs, messaging humans, spending money: confirmed every time, even after the system feels trustworthy. One bad autonomous action costs more trust than a thousand confirmations. This one is not up for revision.

**Nothing public-facing.** The gateway and runners live on a private tailnet only. Tens of thousands of exposed personal-assistant gateways got catalogued by scanners this year; not joining them.
