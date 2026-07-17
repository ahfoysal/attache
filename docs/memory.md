# Memory

Governing principle: **memory is retrieval into prompts, not accumulation of prompts.** Nothing is "in memory" because it was said; it's in memory because a write path put it somewhere queryable and a read path chose to surface it for this turn.

## Layers and where they live

| Layer | Store | Written by | Read by | Lifetime |
|---|---|---|---|---|
| Current conversation | LLM context, backed by `turns` rows | every turn | router, last ~20 turns | hours, then summarized |
| Active task state | `tasks` + `task_events`; the agent's own session transcript | task engine, taskboard | shortlist, app, resumed agents | until close; events kept |
| Project memory | `NOTES.md` in the workspace + `memories(scope=project)` | agent close-outs, `remember` | any agent on that project | long-lived, curated |
| Preferences | `memories(scope=user, type=preference)` | explicit "remember that…" + confirmed inferences | router + every task prompt | until corrected |
| Long-term facts | `memories`: one fact per row, embedded, typed, dated | nightly distillation + `remember` | semantic retrieval | long, with review |
| Tool output / logs | `tool_calls` rows + full logs as artifacts | runners | app, audits | weeks hot, then archived |
| Old-conversation summaries | `conversations.summary` + promoted facts | nightly job | semantic retrieval | indefinite, they're small |
| Task ↔ repos/machines/files | plain relational columns | task engine | "same repo as before", migration | with the task/project |

## Why each store

**Postgres for everything with identity.** Tasks, sessions, machines, repos, approvals. Most "memory" questions here — which repo, what's running, what did we decide — are lookups and joins, not similarity search. Getting this right removes most of the pressure people put on vector databases.

**pgvector, same database, for meaning without identity.** Distilled facts, summaries, close-out notes. A dedicated vector DB is unjustifiable at single-user scale; pgvector over tens of thousands of rows is instant, and metadata filtering in plain SQL does more for retrieval precision than the embedding model does.

**Disk/object storage for bulk.** Artifacts, reports, logs, repos. Local directory tree first, content-addressed; the schema stores URIs so moving to S3-compatible storage later is config.

**Workspace markdown as agent-native memory.** Claude-family agents are trained to read and honor workspace notes. Project memory as a human-editable `NOTES.md` in the repo beats injecting rows — correctable in any editor. The DB mirrors it for search.

**LLM history is a cache, never a system of record.** A wiped session must never lose real information.

**No knowledge graph.** The entity graph (user–projects–repos–machines–tasks) is small and already relational. Temporal graph memory earns its complexity with large multi-entity histories; not a single-user problem. Revisit only if multi-hop relationship queries start getting written by hand.

## Retrieval per turn

Budget ~800–1,200 tokens, one round trip: an always-on block (preference digest + active-task shortlist, indexed SQL, no embeddings), then a semantic block (embed the utterance, query `memories` filtered by scope and recency-weighted cosine, top 5 above a floor). If the router picks a task tool, a second, larger retrieval builds the *task memory pack* — project notes, related close-outs, repo pointers — into the task prompt. Depth belongs in the task path, not the voice path.

## Writing, correcting, forgetting

- **Distill, don't transcribe.** A nightly cheap-model job turns the day's turns and closed tasks into atomic facts with type, scope, confidence and a source pointer. Raw transcripts as embeddings produce retrieval sludge; distilled facts produce memory.
- **Correction is an update with provenance.** "Actually, use the staging server" supersedes the old fact but keeps the row for audit. A retrieved memory that contradicts the user's current statement loses, and the update fires.
- **Expire by review, not silently.** Facts carry a last-confirmed date; stale, never-retrieved ones surface in a periodic "still true?" sweep. An assistant silently forgetting things it was told destroys trust; not building that.
- **Deletion and privacy.** "Forget that" hard-deletes and tombstones the source from future distillation. Everything is local-first on owned disks. Secrets never become memories — the distiller runs a redaction pass first. Honest caveat: anything spoken to cloud STT or placed in a prompt transits a provider under their retention terms; content where that matters routes to the local pipeline, which is a real reason to keep local STT/TTS working even when cloud quality wins.
