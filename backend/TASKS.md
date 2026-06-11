# TASKS.md — Learning Backlog

> A sequenced, learning-first backlog for this sandbox.
> Each task names the **concept** it teaches, the **why** (so you can defend the
> decision in an interview), and **acceptance criteria** (how you know it's done).
> Work top-to-bottom — later milestones assume earlier ones exist.
>
> Rule of this repo: **you type every line of implementation by hand.** This file
> is the map; you drive.

Legend: `[ ]` todo · `[~]` in progress · `[x]` done

---

## Milestone 1 — Finish the async job pipeline (Celery + Redis)

You just introduced a **task queue**: the HTTP request no longer blocks while Docker
runs. The web process enqueues a job and returns immediately; a separate **worker**
process does the slow work. This is the single most important pattern for scaling
web backends. Right now it works but it's rough — clean it up and understand every line.

- [x] **1.1 — Kill the dead code & fix config in `worker.py`**
  - *Concept:* configuration hygiene, single source of truth.
  - *Why:* `r = redis.Redis(...)` (line 4) is never used, and you have two
    conflicting URLs (`redis_url` unused, `broker_url`/`result_backend` from env
    with different defaults). Inconsistent config is how prod incidents start —
    "works on my machine, broker points at the wrong DB in staging."
  - *Acceptance:* one place defines the broker/result URLs, both read from
    `settings.py` (not raw `os.getenv` scattered in the module), no unused imports
    or clients. App still enqueues and runs a job end-to-end.

- [ ] **1.2 — Move Celery config into `settings.py`**
  - *Concept:* 12-factor config — config comes from the environment, not literals.
  - *Why:* `localhost:6379` hardcoded breaks the moment Redis runs in another
    container. You already use `settings.py` for the DB; Celery should follow the
    same pattern so there's one mental model for "where config lives."
  - *Acceptance:* `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` are fields on your
    settings object with sane local defaults; `worker.py` imports them.

- [ ] **1.3 — Define proper response schemas for the two endpoints**
  - *Concept:* API contracts via Pydantic; never return bare strings/dicts.
  - *Why:* `/execute` returns a raw `task.id` string and `/execute/{id}` returns a
    hand-built dict. A typed response model gives you docs, validation, and a stable
    contract a client can depend on.
  - *Acceptance:* `POST /execute` returns `{ "task_id": ... }` typed; the GET returns
    a typed model with `task_id`, `status`, `result`. Visible & correct in `/docs`.

- [ ] **1.4 — Understand the task lifecycle (write it down, no code)**
  - *Concept:* states of a distributed job: `PENDING → STARTED → SUCCESS/FAILURE`.
  - *Why:* Your GET handler branches on `status == "SUCCESS"`. Do you know what
    `PENDING` actually means in Celery? (Trap: PENDING also means "task id unknown" —
    Celery can't tell "not started yet" from "never existed.") Knowing this prevents
    a whole class of bugs.
  - *Acceptance:* a short note in this file (below) explaining each state and the
    PENDING ambiguity, in your own words.

---

## Milestone 2 — Persistence & data modeling

Redis result backend is **ephemeral** — restart Redis and job history is gone. Real
systems keep an authoritative record in the relational DB and treat Redis as a cache /
transport. `app/sandbox/models.py` is empty; that's the gap.

- [ ] **2.1 — Create a `Job` model (`app/sandbox/models.py`)**
  - *Concept:* data modeling, source of truth, separating durable state from transport.
  - *Why:* You want to answer "what jobs did user X run, and when?" — Redis can't.
    Columns to think about: `id`, `user_id` (FK to users), `status`, `stdout`,
    `stderr`, `created_at`, `finished_at`. Decide types deliberately.
  - *Acceptance:* model defined; imported in `alembic/env.py` (per CLAUDE.md, autogen
    only sees models imported there); migration generated and `alembic upgrade head`
    applies cleanly.

- [ ] **2.2 — Persist job state from the worker**
  - *Concept:* write-through from worker to DB; who owns the DB session in a worker
    (workers aren't request-scoped — `get_db` won't work there).
  - *Why:* This is the subtle part — your FastAPI `get_db` dependency is tied to the
    request lifecycle. A Celery worker has no request. You'll learn to create a session
    inside the task. Also: the worker uses `subprocess` (sync) so a **sync** DB session
    is the honest choice here, not async.
  - *Acceptance:* on enqueue, a `Job` row is created with status `queued`; the worker
    updates it to `running` then `success`/`failed` with captured output.

- [ ] **2.3 — Add an index where it matters**
  - *Concept:* indexing, query patterns drive schema.
  - *Why:* "list my jobs" filters by `user_id` and sorts by `created_at`. Without an
    index that's a full table scan. Learn to index for the read you actually do.
  - *Acceptance:* index on `user_id` (and/or `(user_id, created_at)`); explain in a note
    why you chose those columns.

---

## Milestone 3 — Harden the sandbox (security)

You already do well here: `--network none`, `--memory 128m`, `--cpus 0.5`, a 10s
timeout, and `docker rm -f` cleanup. That's better than most tutorials. Now push it
to the bar a Big-Tech reviewer would expect.

- [ ] **3.1 — Drop privileges & lock down the container**
  - *Concept:* defense in depth, least privilege, container escape surface.
  - *Why:* code runs as root inside the container by default; a kernel/Docker bug
    becomes a host compromise. Add `--read-only`, `--pids-limit`, `--user`, drop all
    Linux capabilities (`--cap-drop ALL`), and consider `--security-opt no-new-privileges`.
  - *Acceptance:* a malicious sample (fork bomb, fill disk, read host files) is contained;
    you can describe what each flag blocks.

- [ ] **3.2 — Replace the file-on-disk handoff**
  - *Concept:* coupling between processes, race conditions, shared mutable state.
  - *Why:* the router writes `sample_{uuid}.py` to the web container's CWD and the worker
    reads it — they must share a filesystem, which they often won't in prod. Pass the code
    *through the queue* (it's just a string) or via an object store. Removes a whole failure mode.
  - *Acceptance:* no `open(...).write` in the router; worker receives code as data.

- [ ] **3.3 — Rate-limit `/execute`**
  - *Concept:* rate limiting, abuse/DoS protection, token-bucket idea.
  - *Why:* one user can spawn unlimited Docker containers and exhaust the host. Even a
    crude per-user limit (Redis counter with TTL) teaches the mechanism that sits in
    front of every real API.
  - *Acceptance:* N requests/minute/user, the N+1th gets HTTP 429.

---

## Milestone 4 — Production-readiness

- [ ] **4.1 — Wire up Sentry** (`sentry-sdk` is already a dependency, unused)
  - *Concept:* error tracking / observability.
  - *Why:* right now a crash in the worker vanishes. Sentry shows you stack traces from
    both web and worker. Init it once at startup for both processes.
  - *Acceptance:* a deliberate exception in a task shows up in Sentry (or local DSN log).

- [ ] **4.2 — Structured logging + a `/health` endpoint**
  - *Concept:* observability basics, readiness vs liveness.
  - *Why:* a load balancer needs `/health` to know if the instance is alive; structured
    (JSON) logs are greppable/queryable at scale where `print` is not.
  - *Acceptance:* `/health` returns 200 (and ideally checks DB + Redis reachability);
    requests emit structured logs.

- [ ] **4.3 — `docker-compose` for the whole stack**
  - *Concept:* local environment parity, service orchestration.
  - *Why:* you currently run uvicorn, Postgres, Redis, and the Celery worker by hand.
    One `docker compose up` that brings up web + worker + postgres + redis is how teams
    onboard in minutes and how dev matches prod.
  - *Acceptance:* `docker compose up` starts everything; `/execute` works end-to-end
    with zero manual steps.

---

## Milestone 5 — Auth cleanup (flagged in CLAUDE.md)

- [ ] **5.1 — Login returns proper status codes + a typed token response**
  - *Concept:* HTTP semantics, REST correctness.
  - *Why:* returning `False`/a raw token instead of `401` + `{access_token, token_type}`
    is wrong and breaks every standard client. Fix the contract.
- [ ] **5.2 — Register/login take a request body, not query-string params**
  - *Concept:* request modeling; credentials never belong in a URL (they get logged).
- [ ] **5.3 — Review the `get_current_user` dependency**
  - *Concept:* auth middleware / dependency injection; what happens on a bad/expired token.

---

## Milestone 6 — Testing & CI

- [ ] **6.1 — First pytest tests** (none exist yet)
  - *Concept:* the testing pyramid; testing async FastAPI handlers.
  - *Why:* you can't refactor safely without tests. Start with auth (pure-ish) and the
    job-status endpoint (mock Celery).
- [ ] **6.2 — GitHub Actions CI**
  - *Concept:* CI/CD, fast feedback.
  - *Why:* run lint + tests on every push so regressions are caught before merge.

---

## Notes (fill these in as you go)

### 1.4 — Celery task states (in my own words)
> _PENDING means..._
> _STARTED means..._
> _SUCCESS / FAILURE mean..._
> _The PENDING ambiguity is..._

### 2.3 — Why I indexed these columns
> _..._
