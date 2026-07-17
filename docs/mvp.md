# MVP: the mobile app

Smallest version that is the product, not a demo of it: **push-to-talk in, one durable task out, a spoken briefing back.** If "find an open source project to contribute to" spoken on the way out the door produces a competent two-sentence answer later, the concept is proven.

## In scope

- React Native app (Expo): hold-to-talk, live transcript with an edit box (typed input is a first-class path and the main debugging tool), task list, task detail with live progress, approval prompts, audio playback of replies
- Push notifications: finished / failed / needs approval
- Gateway with intent router and the full task state machine
- One agent runtime (Claude Agent SDK), home machine only, approved workspaces, plus one Docker profile for untrusted repos
- One session per task with resume ("continue that" works the next day)
- Project memory: notes files per workspace + a facts table with manual "remember this"
- Permission tiers, approvals from the phone, every command audited
- Spoken completion briefings, written by the agent at close

## Out of scope

Wake word. Desktop client. SSH remotes. Second agent runtime. Automatic memory distillation. Local speech models. Anything IoT. Multi-user. Tablet layouts. None of it proves the concept.

## Acceptance script

MVP is done when this sequence works with only a phone in hand:

1. Hold-to-talk: "what's the state of the portfolio project?" → answered from memory in under two seconds.
2. "Find a good open source TypeScript project to contribute to." → acknowledgment within two seconds, task visible in the app, agent researching in its sandbox.
3. Unrelated question mid-task → answered normally; the task is unaffected.
4. Task completes while the app is closed → push arrives; opening the app plays a two-sentence briefing; full report saved as an artifact.
5. "Clone the best one and set it up." → same session resumes; the clone hits an approval prompt; approve from the notification; setup completes.
6. Kill the gateway mid-task, restart → the task resumes from its session file.

## Known unknowns

Cellular latency is outside the design's control; Tailscale plus end-to-end streaming should keep simple turns near the ~1.5s target, unverified until tested on a real network. Mic capture and background-audio behavior differ per platform; Expo either handles it or the bare workflow does. Endpointing (finished vs pausing to think) is where voice projects lose a month — hold-to-talk sidesteps it entirely, which is half the reason the MVP is push-to-talk.
