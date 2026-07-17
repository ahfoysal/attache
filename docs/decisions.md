# Decisions

Settled choices with reasons. Revisit only with new information.

**React Native over Flutter.** Existing React/TS experience; the app is four screens and a websocket, so Dart buys nothing. Expo covers mic capture, background audio and push notifications; the bare workflow is the escape hatch if native audio gets in the way. Flutter's rendering advantages are irrelevant here.

**Mobile before desktop, phone before wake word.** The value shows up away from the keyboard. Hold-to-talk on a phone also sidesteps the two hardest voice problems — wake-word accuracy and end-of-speech detection — until the rest of the system deserves that effort.

**Cascade (STT → model → TTS) over realtime speech-to-speech APIs.** Far cheaper for a system idle most of the day, debuggable as text, and keeps the reasoning model swappable. Realtime APIs can be added later as a premium conversation mode.

**One agent session per task.** Task isolation matches how work actually behaves; one task's debugging must never bleed into another's research. Cross-task continuity flows through task records and memory — readable and correctable — not through a shared context window.

**Custom task state machine over Temporal and friends.** Durable resume is already provided by the agent SDK's session files. What remains is a few hundred lines of state transitions on Postgres, fully understandable at 2am. Workflow engines solve a problem this system doesn't have yet; DBOS then Temporal is the graduation path if that changes.

**Python core, React Native shell.** Two languages is a real cost, but the voice tooling and strongest pipeline libraries are Python-first and the app side is thin. Two processes, one language each.

**Approvals for anything outward, permanently.** Pushing code, opening PRs, messaging humans, spending money: confirmed every time, even after the system feels trustworthy. One bad autonomous action costs more trust than a thousand confirmations. Not up for revision.

**Nothing public-facing.** Gateway and runners exist only on a private tailnet. Scanners catalogued tens of thousands of exposed personal-assistant gateways this year; not joining them.
