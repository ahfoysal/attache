# MVP: the mobile app

The smallest version that is the actual product and not a demo of it: **push-to-talk in, one durable task out, a spoken briefing back.** If I can say "find me an open source project to contribute to" on my way out the door and later hear a competent two-sentence answer, the concept is proven. Everything else is elaboration.

## What's in

- React Native app (Expo): hold-to-talk, live transcript with an edit box (typing is a first-class citizen, and it's also how I debug), task list, task detail with live progress, approval prompts, audio playback of replies
- Push notifications for finished / failed / needs-approval
- Gateway with the intent router and the full task state machine (it's small; build it right once)
- One agent runtime (Claude Agent SDK), running on my home machine only, in approved workspaces, plus one Docker profile for other people's repos
- One session per task with resume, so "continue that" works tomorrow
- Project memory: notes files in each workspace plus a facts table with a manual "remember this"
- Permission tiers with approvals from the phone; every command audited
- Spoken completion briefings, written by the agent itself

## What's out, deliberately

Wake word. Desktop client. SSH remotes. Second agent runtime. Automatic memory distillation. Local speech models. Smart speakers and anything IoT. Multi-user anything. iPad layouts. All of it can wait; none of it proves the concept.

## The acceptance script

I'll call the MVP done when this exact sequence works, holding only my phone:

1. Ask "what's the state of my portfolio project?" and get an answer from memory in under two seconds.
2. Say "find a good open source TypeScript project I could contribute to." Acknowledgment within two seconds, task visible in the app, agent researching in its sandbox.
3. Interrupt with an unrelated question mid-task. Answered normally; the task doesn't notice.
4. Task completes while the app is closed. Push arrives; opening it plays a two-sentence briefing; the full report is an artifact.
5. Say "clone the best one and set it up." Same session resumes. The clone hits an approval prompt; I approve from the notification. Setup finishes.
6. Kill the gateway mid-task and restart it. The task picks up from its session file like nothing happened.

Six for six and it ships (to me).

## Honest unknowns

Latency over cellular is the one I can't fully control; Tailscale plus streaming everything should hold it near the ~1.5s target for simple turns, but I won't know until it's on a real network. Mic capture and background-audio quirks differ per platform, which is exactly the kind of thing Expo either handles or makes miserable. And endpointing (knowing when I've stopped talking versus paused to think) is where every voice project quietly loses a month; hold-to-talk sidesteps it for now, which is half the reason the MVP is push-to-talk at all.
