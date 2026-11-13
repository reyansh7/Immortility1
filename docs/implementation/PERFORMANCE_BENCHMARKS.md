# Performance

No new benchmark was run in this pass. The current idle numbers are in
[BASELINES.md](../performance/BASELINES.md):

| Measurement | Result |
|---|---|
| Idle UI CPU, 10 minutes | 0.0368% average |
| Idle UI working set | 284.93 MB average, above the 250 MB target |
| Owned-tree working set | 330.38 MB average |
| GPU engine sum while idle | 0.941% average |
| CreateProcess | 923 ms, not time to first token |

The execution-trace panel fetches one JSON document when opened. It does not
poll and does not start a 3D render loop. Multi-agent overhead was not
measured because no second agent runs.
