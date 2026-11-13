# Agent integration guide

Hermes is the only agent. The broker starts one isolated stdio gateway per
task, checks that the tool inventory is empty, and allows at most the guarded
free-model calls. Delegation inside Hermes is present in the installed source
and is not turned on.

OpenMausBot is the named future specialist host. It is not installed. Do not
dispatch a team until all of these exist:

- A reviewed Windows install on a Node version the package accepts.
- A broker operation for each action, with the same deny-by-default policy as
  Hermes tools.
- A parent task id, a depth limit, and cancellation that reaps child processes.
- A zero-cost check. No paid model fallback.

Until that contract is tested, a coding or research request stays one Hermes
conversation. The UI must not invent extra agent nodes.
