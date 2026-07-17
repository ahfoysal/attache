# Roadmap

Phases in order. Each phase must earn the next: if the mobile MVP doesn't survive a month of daily use, there is no phase 2.

## Phase 0 — proof of the seam

Text only. No audio, no app. A typed request becomes a task, an agent runs it in a sandbox, a notification comes back with a summary. This is the unpackaged part, so it goes first; voice is week two.

Done when: the GitHub-search task runs end to end from a typed sentence and can be resumed the next morning.

## Phase 1 — mobile MVP

Everything in [mvp.md](mvp.md). RN app, push-to-talk, streaming STT/TTS through the gateway, tasks, approvals, push notifications.

Risks: cellular latency, mobile audio quirks, and polishing the app instead of the loop. Bar: one month of real daily use without opening a laptop to check on a task.

## Phase 2 — remote machines

Enroll servers over SSH: dedicated user, per-machine keys, Tailscale. Quick commands over a thin SSH tool; long jobs get a runner daemon on the remote so the agent works where the files are. "Continue this on my server" becomes an explicit migration operation.

Blast radius stops being one laptop here — the hardening in [security.md](security.md) lands before the first machine that matters gets enrolled.

## Phase 3 — durable memory

Nightly distillation of conversations and closed tasks into small typed facts. Corrections supersede rather than overwrite. Periodic "still true?" review — silent forgetting or misremembering kills trust faster than any bug. Test: "use the same repo we discussed last week" resolves correctly nine times out of ten.

## Phase 4 — more workers

Second agent runtime (likely Codex), parallel tasks, research-feeds-implementation pipelines, model choice per task. Only if a real queue of work exists by then. Two reliable workers beat five theatrical ones.

## Phase 5 — IoT

Wake-word satellites in rooms: ESP32-class hardware or Home Assistant voice satellites, barge-in polish, proactive briefings, quiet hours. The phone app stays the control surface; satellites are extra microphones and speakers on the same gateway.

Not designed yet beyond one rule: nothing in the gateway may assume there is exactly one client. Cheap insurance now, and it keeps the fun phase from warping the practical ones.
