# Memory and context

The broker stores sessions and tasks in SQLite with WAL. `history()` returns at
most the last 20 successful user and assistant turns. That list is the context
Hermes receives. It is bounded, project-local to this app's database, and
restart-safe.

Hermes itself has memory, skills, and session search in the installed 0.21.1
source. Immortility disables those features for the isolated session. The
user's separate Hermes memory and jobs were not read or migrated.

Mem0 was not added. A vector index is not justified while the only retrieval
is the last 20 turns and tools that could index a repository are disabled.

Approved long-term memory, if added later, needs an explicit user action,
a source and time, and a delete path. Web pages and repository files must not
be able to write those records by themselves.
