# SemanticDriftRegistry · PolicyDrift V1.1 Studio

A reusable GenLayer Intelligent Contract for recording **material changes in public policy rules**. Each Watch binds one public HTTPS policy source to one focused normative question. Validators independently inspect the source; the contract stores a semantic Baseline, checks new Observations, and computes deterministic verdicts and change flags. The history is append-only.

This repository is the **canonical Intelligent Contract source**, separate from the [PolicyDrift browser Project](https://github.com/halihalibt/policydrift). The React UI is a way to use the primitive, not its implementation or core innovation.

## Why a semantic registry?

A rephrased rule may retain its meaning, while changing one condition can materially change what is allowed. A text diff cannot reliably separate these cases. The contract models a Semantic State with `presence`, `disposition`, `conditions`, `scope`, `exceptions`, and `quantitative_terms`. A `PRESENT` state needs an anchored direct excerpt; `NOT_STATED` stores no quote and uses `NONE` for the other fields. Normalized state and schema version yield a SHA-256 integrity digest, not a semantic equivalence verdict.

`register_watch(source_url, target_question)` creates the initial Baseline. `check_drift(watch_id)` independently re-reads the registered source and records an Observation; consecutive identical observations are deduplicated while check counts advance. `adopt_observation(watch_id, observation_id)` is owner-only and, if the latest Observation is eligible and material, appends a new Baseline without erasing earlier records. The three official Demo Watches have **not** adopted V2 and retain their V1 Baselines.

## Independent consensus and deterministic decision

GenLayer nondeterministic execution retrieves the registered public source and extracts the current state and four Semantic Delta Vector relations. A leader and validators fetch and assess the source independently. Strict schema and enums, source status, state consistency, relation values, and positive evidence quotes are validated. The Consensus Critical Vector is compared exactly: `(source_status, presence, disposition)` on registration and those fields plus four ordered relations on drift checks. A constrained equivalence check may accept materially equivalent phrasing in noncritical semantic fields; it cannot set the final verdict or flags. Wrong presence or disposition, malformed payloads, unknown enums, unanchored quotes, materially different states and validator failures fail closed.

After consensus, **contract code** runs the deterministic drift engine. A definite `NOT_STATED → PRESENT` yields `MATERIAL_DRIFT + RULE_APPEARED`; `PRESENT → NOT_STATED` yields `MATERIAL_DRIFT + RULE_DISAPPEARED`. For these definite transitions, V1.1 canonicalizes globally known, non-ambiguous relations to `NOT_APPLICABLE` before exact CCV comparison. `AMBIGUOUS` is never normalized and retains priority. A changed condition can yield `CONDITION_CHANGED`; an unchanged material state yields `NO_MATERIAL_DRIFT`. Unavailable or oversized source content is `UNVERIFIABLE`, never fabricated rule disappearance. The contract derives all 13 material flag bits. See [protocol](PROTOCOL.md) and [consensus validation](CONSENSUS.md).

## Current Studio deployment and live verification

| Item | Verified value |
| --- | --- |
| Network | GenLayer Studio / Studionet, chain ID `61999`, API `https://studio.genlayer.com/api` |
| Contract | [`0x4bBF1Eaa4947686F2291605Caf1DC4e19F55C3C2`](https://explorer-studio.genlayer.com/address/0x4bBF1Eaa4947686F2291605Caf1DC4e19F55C3C2) |
| Deployment | [`0x6af424…e9dff8`](https://explorer-studio.genlayer.com/tx/0x6af424162efcb45e997fdfa8bd759948cf140ae022ec797088a98acf7ee9dff8), `FINALIZED / Accepted / GenVM SUCCESS` |
| View result | `get_protocol_version() = PolicyDrift-V1.1-Studio` |
| Canonical source | [`contracts/semantic_drift_registry.py`](contracts/semantic_drift_registry.py), commit `5d96d9f1b175b16c27f62280bdbb5cc6bfee3819`, SHA-256 `3a7ef302bf57b4c9ee7e8993dd7aac2496c4272faa168f61368af219d657e3d4` |

The isolated Presence Transition validation on this V1.1 instance finalized both [`RULE_APPEARED`](https://explorer-studio.genlayer.com/tx/0xedbbe5a5f21a8bf1c5a7f0ac65a45bec36e256dd546a03251acb456243a7d579) and [`RULE_DISAPPEARED`](https://explorer-studio.genlayer.com/tx/0x79de5188467b519154abd99c975e545a5a0642c6d07f055d7890a744b8ce77c5). These are distinct validation Watches 1 and 2, not the official three-Watch Demo.

The official published-policy V1→V2 Demo was then established on the **same V1.1 contract**. Each Watch has one V1 Baseline, one check and one Observation, with no adoption:

| Official Watch | Finalized Studio check | Final Registry outcome |
| --- | --- | --- |
| [#3, commercial-use condition](https://halihalibt.github.io/policydrift/#/watch/3) | [`0x70aa98…0bdb8`](https://explorer-studio.genlayer.com/tx/0x70aa98f64f9327d73a118a5aec3d9bc73f4dfca1f6f736d5ee2dc8db54e0bdb8) | `MATERIAL_DRIFT + CONDITION_CHANGED`, attribution → prior written approval |
| [#4, independent redistribution](https://halihalibt.github.io/policydrift/#/watch/4) | [`0xf2fdc2…cdcb7`](https://explorer-studio.genlayer.com/tx/0xf2fdc2916a983487ce0b94d501ad892146fed9b2fc68047378960c18a5fcdcb7) | `NO_MATERIAL_DRIFT`, flags `0` |
| [#5, AI training](https://halihalibt.github.io/policydrift/#/watch/5) | [`0xb71d2f…524b6`](https://explorer-studio.genlayer.com/tx/0xb71d2f743f88c28983773b88f9c030b5421d4121c49a8ef960cc2e2926d524b6) | `MATERIAL_DRIFT + RULE_APPEARED`, `NOT_STATED/NONE → PRESENT/PROHIBITED` |

All three transactions finalized with majority acceptance in Normal mode with five initial validators. Watch #5 took three consensus rounds and two leader rotations. Preserve its complete history; final acceptance does not imply every intermediate execution succeeded or every validator agreed. The separate Project repo holds the browser workflow and published [official V2 source](https://halihalibt.github.io/policydrift/demo/policy.html).

## Test, runtime and security assumptions

```bash
python -m unittest discover -s tests -v
```

**18 protocol tests pass**, including independent fetch, strict parsing, malformed and adversarial payload rejection, deterministic verdicts, presence transitions, deduplication and immutable history. Mocks test deterministic guards; the linked Studio transactions separately exercise live GenVM and validator consensus. The Studio Python dependency is pinned in the contract header; GenVM runtime and compatibility notes are in [Studio compatibility](docs/STUDIO_COMPATIBILITY.md).

This primitive assumes one focused question and a stable, public, direct-200 HTTPS source. A `NOT_STATED` conclusion has weaker direct evidence than a positive anchored quote. Source owners may equivocate between validators, and dynamic or personalized pages can be unstable. Studio Web Access does not expose a redirect's final URL, so cross-origin redirect behavior cannot be fully attested. The result records consensus-backed observations of public text, not legal advice. See [security limitations](SECURITY.md).

## Historical V1 release

The older [`0x914BE63CCAE73DF6f039cdb84D46b951851aB8Ca`](https://explorer-studio.genlayer.com/address/0x914BE63CCAE73DF6f039cdb84D46b951851aB8Ca) is a **historical V1 instance**, never upgraded or modified to become V1.1. Its [V1 deployment](https://explorer-studio.genlayer.com/tx/0xc3cfc4e9e07cb90fc4d236c3d5e7eb76da23b8cb9edc4b40a3d32457285e01eb), source hash `16b76c91a6960ea3c9fccdc5e10069c09f9ac8824befa20719f456ca2a67b4a5` and commit `873a1f337f6a3d28c968f57bd1aee6dbad64e394` remain historical diagnostic evidence. [Historical V1 stage result](docs/STUDIO_STAGE_RESULT.md) records the state as of that earlier stage; do not attribute its transactions or screenshots to V1.1.

## Repository map

```text
contracts/semantic_drift_registry.py  canonical, deployable V1.1 contract
tests/test_protocol.py               protocol and adversarial tests
PROTOCOL.md                           state, digest, verdict, flags and history
CONSENSUS.md                          independent validator and CCV rules
SECURITY.md                           assumptions and residual limits
docs/STUDIO_COMPATIBILITY.md          historical compatibility probes
docs/STUDIO_STAGE_RESULT.md           historical V1 deployment proof
```
