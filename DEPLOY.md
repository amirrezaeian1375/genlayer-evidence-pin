# Deployment Record - GenLayer Studionet

Contract: EvidencePin
Deployed: 2026-10-29
Execution mode: Normal (full consensus), 5 initial validators per transaction

## Address

Contract: 0x7973456F5022183BfB9B3156432cE423b8e465c7
Deployer: 0x3d9E39265d74511065f88C987f898c1d02892f3e

## Verified transactions

All transactions below reached FINALIZED with consensus result Accepted and rotation count 0.
Nothing here was produced by direct-mode tests; every result came from live web and LLM
execution on Studionet validators.

| Step | Method | Tx | Result |
|---|---|---|---|
| Deploy | constructor | [0x166dc402](https://explorer-studio.genlayer.com/tx/0x166dc402b2411765d8cee0ae1157fb8f3b40398a938694a3699c27cc5e2160ff) | contract created |
| P1 pin | `pin` | [0xa67a0362](https://explorer-studio.genlayer.com/tx/0xa67a0362119d25197fe039a601b89cd960c541bcc58135ee588964271266eb2f) | `"P1"`, answer `21 million` |
| P1 recheck | `recheck` | [0x30fd850f](https://explorer-studio.genlayer.com/tx/0x30fd850f0f4800db378249fc1dcc5d3ca5dfcf03201b2c72170107889cf7352f) | `ACTIVE` / `PRESENT` |
| P2 pin | `pin` | [0xe0c3d470](https://explorer-studio.genlayer.com/tx/0xe0c3d470e39188c85a9e7c5b8db628830fde1f390960b1805925362d58c1eda5) | `"P2"`, answer `proof of stake` |
| P3 pin | `pin` | [0x5b3fcada](https://explorer-studio.genlayer.com/tx/0x5b3fcadadcdd9aaf2a5e46516a5c13e2f4ee0a275d26d6c47c24bf8e179a7987) | `"P3"`, answer `99.9 percent` |
| P3 recheck after source edit | `recheck` | [0xd3370a63](https://explorer-studio.genlayer.com/tx/0xd3370a63a90f5ed5d9e92ee7ba1803bfdd9202bf78e8bea670e1918e9cf491f7) | `ACTIVE` / `CHANGED` -> version 2, answer `99.5 percent` |
| P3 recheck after source retired | `recheck` | [0xfb642656](https://explorer-studio.genlayer.com/tx/0xfb6426561e03a0e0a0d53581b65e4f2ed24cb51fce75897b345c21361da75707) | `NOT_FOUND`, answer and quote empty |

## What each run proves

- The quote is re-derived from the validator's own copy of the page, not copied from the
  leader's calldata: P3's stored quote stopped matching the live page and the deterministic
  step reported `CHANGED` before any model was called.
- The deterministic path needs no LLM: the `PRESENT` recheck passed with strict equality only.
- A changed source produces a new pinned version (v1 -> v2) instead of silently keeping stale
  evidence.
- A retired source produces `NOT_FOUND`. The contract does not claim the old value was false.

## Not yet proven

- Behavior on Bradbury or any network other than Studionet.
- Sources that reflow text between the leader and validator fetches inside one transaction
  (`UNSTABLE_SOURCE`). This path is implemented but was not observed on chain.
- Pages behind login walls, heavy JavaScript rendering, or bot filtering.
- The `FETCH_FAILED` branch was not exercised on chain.
