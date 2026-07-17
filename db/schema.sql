-- Attaché schema, Phase 0.
-- Mirrors docs/data-model.md, minus the pgvector column on `memories`
-- (semantic retrieval is Phase 3; a later migration adds the extension +
-- embedding column + HNSW index). gen_random_uuid() is built into PG13+.

create table if not exists users (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  preferences jsonb not null default '{}'
);

create table if not exists machines (
  id uuid primary key default gen_random_uuid(),
  name text unique not null,
  kind text not null check (kind in ('local','ssh','container_host')),
  address text, ssh_user text, ssh_key_ref text,
  runner_url text,
  capabilities jsonb not null default '{}',
  status text not null default 'unknown',
  last_seen_at timestamptz
);

create table if not exists projects (
  id uuid primary key default gen_random_uuid(),
  name text unique not null,
  repo_url text,
  default_machine_id uuid references machines(id),
  notes_path text,
  metadata jsonb not null default '{}'
);

create table if not exists workspaces (
  id uuid primary key default gen_random_uuid(),
  machine_id uuid not null references machines(id),
  project_id uuid references projects(id),
  path text not null,
  isolation text not null default 'sandbox'
    check (isolation in ('sandbox','container','none')),
  approved boolean not null default false,
  unique (machine_id, path)
);

create table if not exists conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id),
  started_at timestamptz not null default now(),
  summary text
);

create table if not exists turns (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references conversations(id),
  role text not null check (role in ('user','assistant')),
  text text not null,
  audio_ref text,
  heard_fraction real,
  task_id uuid,
  created_at timestamptz not null default now()
);

create table if not exists tasks (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id),
  project_id uuid references projects(id),
  parent_task_id uuid references tasks(id),
  title text not null,
  spec jsonb not null,
  state text not null default 'created' check (state in
    ('created','planning','waiting_approval','running','blocked',
     'paused','failed','completed','cancelled')),
  blocked_reason text,
  spoken_summary text,
  budget jsonb not null default '{}',
  spent jsonb not null default '{}',
  created_at timestamptz not null default now(),
  last_activity_at timestamptz not null default now()
);
create index if not exists tasks_state_activity on tasks (state, last_activity_at desc);

create table if not exists task_events (
  id bigint generated always as identity primary key,
  task_id uuid not null references tasks(id),
  type text not null,
  payload jsonb not null,
  created_at timestamptz not null default now()
);
create index if not exists task_events_task on task_events (task_id, id);

create table if not exists agent_sessions (
  id uuid primary key default gen_random_uuid(),
  task_id uuid not null references tasks(id),
  runtime text not null default 'claude-agent-sdk',
  external_session_id text,
  machine_id uuid references machines(id),
  workspace_id uuid references workspaces(id),
  model text not null,
  status text not null default 'active' check (status in ('active','closed','abandoned')),
  closeout jsonb,
  cost_usd numeric(10,4) not null default 0,
  started_at timestamptz not null default now(),
  closed_at timestamptz
);
create index if not exists agent_sessions_task on agent_sessions (task_id);

create table if not exists approvals (
  id uuid primary key default gen_random_uuid(),
  task_id uuid not null references tasks(id),
  action text not null,
  detail jsonb not null,
  risk_tier text not null check (risk_tier in ('T2','T3')),
  status text not null default 'pending'
    check (status in ('pending','approved','denied','expired')),
  decided_via text,
  requested_at timestamptz not null default now(),
  expires_at timestamptz,
  decided_at timestamptz
);
create index if not exists approvals_task on approvals (task_id, status);

create table if not exists memories (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id),
  scope text not null check (scope in ('user','project','task')),
  project_id uuid references projects(id),
  type text not null,
  content text not null,
  confidence real not null default 0.8,
  source_kind text,
  source_id uuid,
  superseded_by uuid references memories(id),
  created_at timestamptz not null default now(),
  last_confirmed_at timestamptz,
  last_retrieved_at timestamptz
);
create index if not exists memories_scope on memories (user_id, scope) where superseded_by is null;

create table if not exists artifacts (
  id uuid primary key default gen_random_uuid(),
  task_id uuid not null references tasks(id),
  kind text not null,
  name text not null,
  uri text not null,
  media_type text,
  size_bytes bigint,
  digest text,
  created_at timestamptz not null default now()
);
create index if not exists artifacts_task on artifacts (task_id);

create table if not exists tool_calls (
  id bigint generated always as identity primary key,
  task_id uuid references tasks(id),
  session_id uuid references agent_sessions(id),
  machine_id uuid references machines(id),
  tool text not null,
  input_digest jsonb not null,
  policy_decision text not null,
  exit_code int,
  duration_ms int,
  output_ref text,
  created_at timestamptz not null default now()
);
create index if not exists tool_calls_task on tool_calls (task_id, id);

create table if not exists notifications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id),
  task_id uuid references tasks(id),
  kind text not null,
  spoken text,
  body text,
  channel text,
  status text not null default 'queued',
  created_at timestamptz not null default now(),
  delivered_at timestamptz
);
create index if not exists notifications_status on notifications (status, created_at);

-- Single-user bootstrap: one user row the whole system hangs off of.
insert into users (id, name, preferences)
values ('00000000-0000-0000-0000-000000000001', 'owner', '{}')
on conflict (id) do nothing;

-- The home-base machine.
insert into machines (name, kind, status)
values ('home-base', 'local', 'online')
on conflict (name) do nothing;
