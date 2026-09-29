# SemanticDriftRegistry · PolicyDrift V1

**What is it?** A stateful GenLayer Intelligent Contract that records when the meaning of a public policy rule materially changes. A Watch fixes one HTTPS policy page and one normative question. A Baseline records the accepted answer; anyone may request a fresh Observation; only the Watch owner may adopt the latest material Observation as a new Baseline. Baselines and Observations form append-only histories.

**Why not text diffs?** Rewording may leave a rule intact; one changed condition may alter its meaning without changing much text. This contract stores a semantic state, compares four named dimensions, and uses deterministic flags and verdicts after independent validators inspect the actual page.

**Why GenLayer?** Intelligent Contracts let a leader and validators independently retrieve one registered public source and reason about its normative content. The validator compares exact consensus-critical fields, checks a verbatim evidence quote against its independently fetched text, and checks materially equivalent phrasing in the remaining fields. The on-chain logic alone derives the verdict and flags. No central monitoring server can silently rewrite the accepted history.

**How does it work?** `register_watch(source_url, target_question)` validates a single normative target, establishes an initial `PRESENT` or `NOT_STATED` Baseline, and returns its Watch ID. `check_drift(watch_id)` performs a permissionless consensus check, deterministically evaluates the Semantic Delta Vector, deduplicates consecutive equal observations, and returns the Observation ID. `adopt_observation(watch_id, observation_id)` is owner-only and appends a new Baseline only when the latest active-baseline Observation is verifiable and material. The 15-minute cooldown applies to non-owners, never the owner. See [PROTOCOL.md](PROTOCOL.md) and [CONSENSUS.md](CONSENSUS.md).

**Deployment status:** The [Studio contract at `0x914B…B8Ca`](https://explorer-studio.genlayer.com/address/0x914BE63CCAE73DF6f039cdb84D46b951851aB8Ca) is the **historical V1 instance**, with [finalized deployment proof](https://explorer-studio.genlayer.com/tx/0xc3cfc4e9e07cb90fc4d236c3d5e7eb76da23b8cb9edc4b40a3d32457285e01eb). Its source SHA-256 `16b76c91a6960ea3c9fccdc5e10069c09f9ac8824befa20719f456ca2a67b4a5` belongs to commit `873a1f3`; the current [`contracts/semantic_drift_registry.py`](contracts/semantic_drift_registry.py) is the **V1.1 local repair candidate** and has **not** been deployed. Do not attribute the old address, transaction or screenshots to V1.1. See [PROTOCOL.md](PROTOCOL.md) and [CONSENSUS.md](CONSENSUS.md) for the approved, limited presence-transition change.

## Target and version

Studio / Studionet only: chain ID `61999`, API `https://studio.genlayer.com/api`, GenVM `v0.2.16`, Python dependency pinned in the contract header, `from genlayer import *`. The future frontend must pin `genlayer-js@1.1.8`; this repository does not implement React. Full compatibility decisions and the HTTP redirect limitation are in [docs/STUDIO_COMPATIBILITY.md](docs/STUDIO_COMPATIBILITY.md). Additional risks are in [SECURITY.md](SECURITY.md).

## Run deterministic protocol tests

```bash
python -m unittest discover -s tests -v
```

The local tests model the GenLayer host and explicitly verify protocol guards, independent fetch invocations, immutable histories, deterministic verdicts, and adversarial malformed payloads. Studio full-consensus deployment and transaction tests provide the separate live runtime check. No private key or paid external service is required.

## Studio release checks

The release instance registered a fixed [test-server page](https://test-server.genlayer.com/static/genvm/hello.html) as `NOT_STATED`: [register transaction](https://explorer-studio.genlayer.com/tx/0x3ce22ebdc6fe96e3f0cbec0daf99613a3580151bcc67a626b26d22697cab8fd1). Its [first drift check](https://explorer-studio.genlayer.com/tx/0x8652eeec6ae492b45804ba314d045bd5eba0302938a3cfc0beb48e958863696f) finalized `NO_MATERIAL_DRIFT`, flags `0`. The [immediate owner repeat](https://explorer-studio.genlayer.com/tx/0xf2dca8201584166c4749962b87c26453c4ae2e9c78bf3ad8c127102feef84a13) finalized successfully and left `check_count=2`, `observation_count=1`, `last_observation_id=1`. All four transactions, including deployment, used Normal (Full Consensus).

The release instance also [registered an IANA `PRESENT` Baseline](https://explorer-studio.genlayer.com/tx/0xe8c3e2a16af62ef2096a64b5f33100c7a920013e2806bde5edadd0ba81d296df) for Watch 2, with `PROHIBITED` disposition and a direct source quote. Its [drift check](https://explorer-studio.genlayer.com/tx/0x0d02e5869bba80929df72af0e7334556a45b94270a93d1fbe8681dadfec18286) finalized `NO_MATERIAL_DRIFT`, flags `0`, with four `SAME` relations. An [earlier attempt](https://explorer-studio.genlayer.com/tx/0xad5adbbb3d8b797d7662d8acdb7d238f6ec8b8bb5aea83433bdbbc84218d92d4) for that same question finalized `Undetermined` after validator disagreement and created no Watch. See [Studio stage result](docs/STUDIO_STAGE_RESULT.md) for the exact coverage and open items.

## File layout

```text
contracts/semantic_drift_registry.py  deployable self-contained contract
tests/test_protocol.py               local protocol and adversarial checks
docs/STUDIO_COMPATIBILITY.md          network/API/version freeze and probe proofs
docs/STUDIO_STAGE_RESULT.md            release deployment and test evidence
PROTOCOL.md                           records, digest, verdict and history rules
CONSENSUS.md                          independent validation flow
SECURITY.md                           residual risks and source-boundary limitation
```
