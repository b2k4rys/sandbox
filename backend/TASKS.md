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

## 🎯 North Star — a mini Function-as-a-Service platform

The end goal: turn this from "run a script once" into a **serverless function platform**
("mini-Lambda"). Users deploy a function; you invoke it repeatedly, *fast*, under load,
across multiple executor nodes, with metered usage.

The defining engineering problem is the **warm container pool** (Milestone 7) —
eliminating cold starts by reusing pre-warmed containers. That single problem is deeper
than everything in Milestones 1–6 combined, and it's exactly what infra interviewers
probe. Everything before it is foundation that feeds this:

- M2 (persistence) → the source of truth for functions & invocations
- M3 (security) → matters 10× more once containers are reused across users
- M4 (observability) → you cannot tune a pool you can't measure
- M5 (WebSockets/pub-sub) → becomes live invocation log streaming

Don't skip ahead to M7 — build the foundation, *measure the naive cold-start cost first*,
then make it fast. "Measure, then optimize" is the whole lesson.

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

- [x] **1.2 — Move Celery config into `settings.py`**
  - *Concept:* 12-factor config — config comes from the environment, not literals.
  - *Why:* `localhost:6379` hardcoded breaks the moment Redis runs in another
    container. You already use `settings.py` for the DB; Celery should follow the
    same pattern so there's one mental model for "where config lives."
  - *Acceptance:* `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` are fields on your
    settings object with sane local defaults; `worker.py` imports them.

- [x] **1.3 — Define proper response schemas for the two endpoints**
  - *Concept:* API contracts via Pydantic; never return bare strings/dicts.
  - *Why:* `/execute` returns a raw `task.id` string and `/execute/{id}` returns a
    hand-built dict. A typed response model gives you docs, validation, and a stable
    contract a client can depend on.
  - *Acceptance:* `POST /execute` returns `{ "task_id": ... }` typed; the GET returns
    a typed model with `task_id`, `status`, `result`. Visible & correct in `/docs`.

- [x] **1.4 — Understand the task lifecycle (write it down, no code)**
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

- [x] **2.1 — Create a `Job` model (`app/sandbox/models.py`)**
  - *Concept:* data modeling, source of truth, separating durable state from transport.
  - *Why:* You want to answer "what jobs did user X run, and when?" — Redis can't.
    Columns to think about: `id`, `user_id` (FK to users), `status`, `stdout`,
    `stderr`, `created_at`, `finished_at`. Decide types deliberately.
  - *Acceptance:* model defined; imported in `alembic/env.py` (per CLAUDE.md, autogen
    only sees models imported there); migration generated and `alembic upgrade head`
    applies cleanly.

- [x] **2.2 — Persist job state from the worker**
  - *Concept:* write-through from worker to DB; who owns the DB session in a worker
    (workers aren't request-scoped — `get_db` won't work there).
  - *Why:* This is the subtle part — your FastAPI `get_db` dependency is tied to the
    request lifecycle. A Celery worker has no request. You'll learn to create a session
    inside the task. Also: the worker uses `subprocess` (sync) so a **sync** DB session
    is the honest choice here, not async.
  - *Acceptance:* on enqueue, a `Job` row is created with status `queued`; the worker
    updates it to `running` then `success`/`failed` with captured output.

- [x] **2.3 — Add an index where it matters**
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

- [x] **3.1 — Drop privileges & lock down the container**
  - *Concept:* defense in depth, least privilege, container escape surface.
  - *Why:* code runs as root inside the container by default; a kernel/Docker bug
    becomes a host compromise. Add `--read-only`, `--pids-limit`, `--user`, drop all
    Linux capabilities (`--cap-drop ALL`), and consider `--security-opt no-new-privileges`.
  - *Acceptance:* a malicious sample (fork bomb, fill disk, read host files) is contained;
    you can describe what each flag blocks.

- [x] **3.2 — Replace the file-on-disk handoff**
  - *Concept:* coupling between processes, race conditions, shared mutable state.
  - *Why:* the router writes `sample_{uuid}.py` to the web container's CWD and the worker
    reads it — they must share a filesystem, which they often won't in prod. Pass the code
    *through the queue* (it's just a string) or via an object store. Removes a whole failure mode.
  - *Acceptance:* no `open(...).write` in the router; worker receives code as data.

- [x] **3.3 — Rate-limit `/execute`**
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

## Milestone 5 — Real-time job updates via WebSockets

Right now a client has to **poll** `GET /execute/{task_id}` repeatedly to find out
when a job finishes. That's wasteful and adds latency. The better model is **push**:
the server notifies the client the moment the job state changes. This is one of the
most common system design questions at Big Tech — "how would you make this real-time?"

- [ ] **5.1 — Understand push vs pull (write it down, no code)**
  - *Concept:* polling vs WebSockets vs SSE vs long-polling — four different answers
    to the same problem. Know the trade-offs.
  - *Why:* polling is simple but wastes connections and adds latency equal to your
    poll interval. WebSockets are a persistent bidirectional TCP connection — the
    server can push at any time. SSE (Server-Sent Events) is a simpler one-way push
    over HTTP. Long-polling is a hack that bridges the two worlds.
  - *Acceptance:* a note in this file (below) comparing all four approaches and
    stating which you'd use for job status updates and why.

- [ ] **5.2 — Add a WebSocket endpoint for job status**
  - *Concept:* WebSocket lifecycle in FastAPI (`websocket.accept()`, `send_json()`,
    `close()`), connection management.
  - *Why:* `websocket.py` is already in your requirements. FastAPI has first-class
    WebSocket support. The endpoint opens a connection, and when the job transitions
    to `SUCCESS` or `FAILURE`, it pushes the final result and closes.
  - *Acceptance:* `WS /sandbox/execute/{task_id}/ws` — client connects, server
    polls Celery state internally (every ~0.5s), pushes status updates as JSON, closes
    when terminal state is reached. Test it via `wscat` or a simple Python client.

- [ ] **5.3 — Use Redis pub/sub to replace internal polling**
  - *Concept:* Redis pub/sub, event-driven architecture, decoupling producer from consumer.
  - *Why:* the WebSocket endpoint in 5.2 polls Celery state in a loop — that's still
    polling, just moved server-side. The real solution: the worker **publishes** a
    message to a Redis channel when the job finishes, and the WebSocket handler
    **subscribes** to that channel and pushes it to the client immediately. Zero
    polling, sub-millisecond latency, and scales to multiple web server instances.
  - *Acceptance:* worker publishes `{"task_id": ..., "status": ..., "result": ...}`
    to a Redis channel on completion; WebSocket handler subscribes and forwards to
    the client. No polling loop anywhere.

- [ ] **5.4 — Handle connection edge cases**
  - *Concept:* distributed systems failure modes — what happens when the client
    disconnects before the job finishes? What if the job finishes before the client
    connects?
  - *Why:* real systems need to handle these. If the client connects *after* the job
    already finished, the pub/sub message is gone — you need to check Redis/DB first
    and send the cached result immediately. If the client disconnects mid-run, you
    need to catch `WebSocketDisconnect` and clean up the subscription.
  - *Acceptance:* both edge cases handled; explain in a note what each failure mode
    is and how you handled it.

---

## Milestone 6 — Auth cleanup (flagged in CLAUDE.md)

- [ ] **6.1 — Login returns proper status codes + a typed token response**
  - *Concept:* HTTP semantics, REST correctness.
  - *Why:* returning `False`/a raw token instead of `401` + `{access_token, token_type}`
    is wrong and breaks every standard client. Fix the contract.
- [ ] **6.2 — Register/login take a request body, not query-string params**
  - *Concept:* request modeling; credentials never belong in a URL (they get logged).
- [ ] **6.3 — Review the `get_current_user` dependency**
  - *Concept:* auth middleware / dependency injection; what happens on a bad/expired token.

---

## Milestone 7 — Testing & CI

- [ ] **7.1 — First pytest tests** (none exist yet)
  - *Concept:* the testing pyramid; testing async FastAPI handlers.
  - *Why:* you can't refactor safely without tests. Start with auth (pure-ish) and the
    job-status endpoint (mock Celery).
- [ ] **7.2 — GitHub Actions CI**
  - *Concept:* CI/CD, fast feedback.
  - *Why:* run lint + tests on every push so regressions are caught before merge.

---

## 🎯 Milestone 8 — From sandbox to FaaS platform (THE north star)

This is where it stops being a tutorial project. Build it in order — each task assumes
the previous one, and the *measure-before-you-optimize* sequence (8.2 → 8.3) is the
entire point. Don't merge them.

- [ ] **8.1 — Model a "function" and split deploy from invoke**
  - *Concept:* what a serverless function actually *is* — code + runtime + config,
    registered once and invoked many times. The deploy/invoke split is the core FaaS idea.
  - *Why:* today you upload code and run it in one shot. A FaaS separates the two:
    `POST /functions` registers a function (returns a `function_id`); `POST /functions/{id}/invoke`
    runs the already-registered code with a request payload. This separation is what lets
    you cache, warm, and meter per function.
  - *Acceptance:* `Function` model (id, name, runtime, code, owner); deploy + invoke
    endpoints; invoking a registered function returns its output.

- [ ] **8.2 — Naive invoke path + MEASURE the cold start**
  - *Concept:* baselining. You cannot claim "I made it fast" without a before-number.
  - *Why:* wire invoke to spin up a fresh container per call (what you do now). Then
    instrument it: how long from request → container ready → output? Record p50 and p99
    over ~50 invocations. This ugly number is the thing 8.3 destroys — and the story you'll
    tell in an interview ("cold start was ~900ms p99; warm pool cut it to ~40ms").
  - *Acceptance:* invoke works container-per-call; a documented latency benchmark (p50/p99)
    written into the Notes section below.

- [ ] **8.3 — ⭐ Warm container pool (the centerpiece)**
  - *Concept:* pooling, cold-start elimination, checkout/return lifecycle, **state reset
    between tenants**. This is the defining problem of serverless.
  - *Why:* maintain a pool of pre-warmed, idle containers. An invoke *checks one out*,
    runs the payload, *resets its state*, and *returns it* to the pool — no `docker run`
    on the hot path. The subtle, security-critical part: resetting so user B never sees
    user A's leftover files/memory/env. Get this wrong and it's a data-leak vuln.
  - *Acceptance:* p99 invoke latency drops dramatically vs 8.2 (record the new number);
    you can explain pool sizing, eviction, and how you guarantee clean reuse.

- [ ] **8.4 — Concurrency & pool exhaustion under load**
  - *Concept:* backpressure, queueing vs scaling vs rejecting, min/max pool size.
  - *Why:* what happens when more invokes arrive than there are warm containers? You must
    *choose* a policy — queue and wait, spin up more (scale-up), or reject with 429. Each
    has trade-offs. Load-test it (e.g. `hey`/`locust`) and observe behavior past the pool size.
  - *Acceptance:* a documented policy; a load test showing what happens at concurrency >
    pool size; min/max pool bounds with scale-up/down.

- [ ] **8.5 — Horizontal executor fleet + node failure**
  - *Concept:* distributed scheduling, a node registry, graceful drain, failure handling.
  - *Why:* one machine's pool has a ceiling. Run *multiple* executor processes/nodes; a
    scheduler picks one per invoke (least-loaded / round-robin); if a node dies mid-invoke,
    the platform survives and the request is retried or fails cleanly.
  - *Acceptance:* 2+ executor nodes; invokes distribute across them; killing one node does
    not take down the platform.

- [ ] **8.6 — Per-invocation metering**
  - *Concept:* usage accounting — the thing every FaaS bills on (CPU-ms, memory, count).
  - *Why:* capture and store per-invocation CPU time, peak memory, and duration. Expose
    per-function usage. This is real ops/billing infrastructure.
  - *Acceptance:* `GET /functions/{id}/usage` returns aggregate invocation count + resource
    totals, sourced from measured values (ties into M4 observability).

- [ ] **8.7 — Live invocation log streaming**
  - *Concept:* streaming stdout as it's produced (not after exit); reuses M5 WebSocket/pub-sub.
  - *Why:* `kubectl logs -f` for your platform. The executor publishes log lines to a Redis
    channel as they're produced; the client streams them live over a WebSocket.
  - *Acceptance:* invoking a long-running function streams its output line-by-line in real time.

---

## Milestone 9 — Make it reviewable (ship it)

A project a recruiter can't run or understand scores far below one they can. This is the
half-day of work that disproportionately raises the project's value for your actual goal.

- [ ] **9.1 — README with an architecture diagram + the trade-offs you made**
  - *Why:* engineers care more about "why Celery over a thread pool" and "why warm pools
    over container-per-call" than about features. Include the before/after latency numbers
    from 8.2/8.3 — concrete numbers are what make it credible.
- [ ] **9.2 — Live deployment + a one-command local setup**
  - *Why:* a deployed demo (or a flawless `docker compose up`) means a reviewer can *try*
    it. Untriable projects get skimmed and forgotten.

---

## Notes (fill these in as you go)

### 1.4 — Celery task states (in my own words)
> _PENDING means..._
> _STARTED means..._
> _SUCCESS / FAILURE mean..._
> _The PENDING ambiguity is..._

### 2.3 — Why I indexed these columns
> _..._
