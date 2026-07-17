# Roadmap

Phases, in order. Each one has to earn the next; if the mobile MVP doesn't survive a month of my own daily use, there is no phase 2 and that's fine, better to learn it early.

## Phase 0 — proof of the seam

Text only, no audio, no app. A request typed into a plain box becomes a task, an agent runs it in a sandbox, a notification comes back with a summary. This is the part nobody has packaged, so it goes first. Voice is week two, not week one.

Done when: the GitHub-search task runs end to end from a typed sentence, and I can resume it the next morning.

## Phase 1 — the mobile MVP

Everything in [mvp.md](mvp.md). React Native app, push-to-talk, streaming STT/TTS through the gateway, tasks, approvals, pushes.

Main risks: cellular latency, mobile audio quirks, and the temptation to polish the app instead of the loop. The bar is a month of real daily use without opening a laptop to check on a task.

## Phase 2 — remote machines

Enroll servers over SSH (dedicated user, per-machine keys, Tailscale). Quick commands run over a thin SSH tool; long jobs get a runner daemon on the remote so the agent works where the files are. "Continue this on my server" becomes a real, explicit migration.

This is where the blast radius stops being one laptop, so the hardening work lands before the first real machine does.

## Phase 3 — memory worth the name

Nightly distillation of conversations and finished tasks into small typed facts. Corrections supersede instead of overwrite. A periodic "is this still true?" review, because an assistant silently forgetting or misremembering things is how trust dies. The test: "use the same repo we discussed last week" resolves correctly nine times out of ten.

## Phase 4 — more hands

A second agent runtime (Codex is the likely candidate), parallel tasks, research-feeds-implementation pipelines, model choice per task. Only if there's a real queue of work by then; two reliable workers beat five theatrical ones.

## Phase 5 — IoT, finally

The dessert phase. Wake-word satellites in rooms (ESP32-class hardware or Home Assistant's voice satellites speak a simple enough protocol to reuse), barge-in polish, proactive morning briefings, quiet hours. The phone app stays the control surface; the satellites are just more microphones and speakers on the same gateway.

I'm deliberately not designing this part yet beyond making sure nothing in the gateway assumes there's exactly one client. That's cheap insurance now and it keeps the fun phase from warping the practical ones.
