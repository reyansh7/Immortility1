# Evolution direction — analysis of the user's additional notes

Status: design input accepted on 2026-11-13; no learning features claimed implemented.
The master prompt and blueprint remain authoritative for P0/P1.

## Intended contribution

Build a Windows companion around Hermes, then study **verified experience-driven adaptation**.
The first-party contribution is cross-agent trajectory normalization, independent outcome
verification, controlled skill promotion, adaptive route selection, and reproducible evaluation.
Hermes already supplies an agent harness, skills, memory and delegation; duplicating those
does not establish novelty. “Agentic operating system” describes a product ambition, not an
OS kernel or a claim of new model training.

## Learning levels and implementation sequence

1. Finish P0/P1: real text conversation, safe process isolation, durable task events, stop,
   cost controls, reproducible setup. The persisted events are evidence for future tracing,
   not yet an Experience Graph or training dataset.
2. Add independently verified trajectories: input provenance, attempt and parent IDs,
   environment/version, chosen route, actual tool calls, timing, quota, artifact references,
   verifier evidence, correction lineage and failure class. Export metadata only by default.
3. P4: opt-in episodic/project memory and an experience graph with retrieval, deletion,
   retention and provenance. Start with SQLite relationships and FTS; justify a graph DB by
   measured need. Separate ephemeral OS context (P3) from durable memory.
4. P5–P7: have Hermes propose candidate reusable skills. A separate verifier replays them in
   approved isolated workspaces, compares a versioned baseline, checks regression and policy,
   then records promotion/rejection. Candidates never grant tools or edit their own authority.
5. Once two genuinely eligible routes and sufficient outcomes exist, compare a fixed baseline
   with contextual Thompson Sampling or LinUCB. Apply privacy, cost, modality, permissions,
   quota and availability as hard admission filters before scoring any eligible route.
6. Add an accessible Evaluation Lab before 3D visualization. Version experiments and publish
   actual results with held-out tasks, repeated trials and confidence intervals.

L1 changes stored knowledge. L2 changes skills, prompts and selection policy. These are the
initial research scope. L3 weight training / reinforcement learning is separate optional work;
it requires hardware, licensing and cost review and is not needed to demonstrate adaptation.

## Experimental claims to test

Primary hypothesis: retrieving verified prior strategies increases independently measured
completion on new tasks in the same family without increasing unauthorized action attempts.
Secondary hypotheses: gated skill promotion reduces tool calls; learned routing improves
success/latency/quota tradeoffs over static selection; bounded recovery improves completion.

Compare A baseline Hermes, B retrieval, C retrieval + skills, D plus learned routing, E plus
verification/recovery. Control model versions, task starts, permission profiles and trial counts.
Split by task family/project to reduce leakage. Keep validation and test tasks out of skill
optimization. Separate verifier false positives from agent failure. A model judge alone is
insufficient evidence of desktop or coding success.

Record completion, wall time, calls, quota, recovery success, policy denials, unsafe attempts,
and verifier confidence. Free-tier outages and changing models are confounders; report them.
With a $0 ceiling, cost is an eligibility condition; quota and latency distinguish eligible routes.
Do not claim a bandit outperforms static routing until the held-out comparison demonstrates it.

## Boundaries and risks

- Immutable, versioned evidence plus append-only corrections; privacy deletion must also remove
  raw content and linked indexes. “Immutable” does not mean keeping personal data forever.
- Separate learner, verifier and permission authority. A proposed skill is untrusted content.
- Roll back only actions with tested inverses/checkpoints. External sends and submissions may
  be irreversible. Recovery is bounded and cannot bypass approval.
- Do not automatically install an evolution service, benchmark cloud infrastructure or extra
  observability servers. Begin inside the modular monolith when the phase needs real code.
- Evaluate Agent Lightning, WindowsAgentArena, OSWorld, Phoenix, OpenInference and trajectory
  research before adoption. The pasted references are research candidates, not verified package
  specifications or authorization to incur cloud costs.
- Résumé bullets and novelty claims must distinguish upstream Hermes behavior from first-party
  contributions and cite measured experiments. There are no measured learning improvements yet.

The first convincing research demo is a baseline and learning-enabled run from identical
starting states on a new comparable coding task, showing traces, a genuine failure/recovery,
candidate skill tests and a measured outcome. Preserve the orb and future avatar as the product
surface; evaluation evidence is the foundation of the technical claim.
