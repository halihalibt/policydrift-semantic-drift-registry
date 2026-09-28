# PolicyDrift V1 · Studio Intelligent Contract stage

Status on 2026-09-28: the self-contained `SemanticDriftRegistry` contract is implemented, locally tested, and deployed and exercised in **GenLayer Studio / Studionet**. This is the HANDOFF Work Execution Order through step 28. The Project/React repository and frontend (step 29 onward) have not started.

## Frozen runtime and deployment

| Item | Verified value |
| --- | --- |
| Network | Studio / Studionet, chain ID `61999`, API `https://studio.genlayer.com/api` |
| GenVM Python runtime | `v0.2.16-x86_64-linux-release` |
| Python SDK dependency | `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`, pinned in the contract header |
| Import and contract API | `from genlayer import *`; `gl.Contract`, `@gl.public.write`, `@gl.public.view` |
| Studio source SHA-256 | `16b76c91a6960ea3c9fccdc5e10069c09f9ac8824befa20719f456ca2a67b4a5`, equal to `contracts/semantic_drift_registry.py` |
| Release test instance | [`0x914BE63CCAE73DF6f039cdb84D46b951851aB8Ca`](https://explorer-studio.genlayer.com/address/0x914BE63CCAE73DF6f039cdb84D46b951851aB8Ca) |
| Deployment transaction | [`0xc3cfc4e9e07cb90fc4d236c3d5e7eb76da23b8cb9edc4b40a3d32457285e01eb`](https://explorer-studio.genlayer.com/tx/0xc3cfc4e9e07cb90fc4d236c3d5e7eb76da23b8cb9edc4b40a3d32457285e01eb) — `FINALIZED`, GenVM `SUCCESS`, consensus `Accepted`, Normal Full Consensus |

[Studio Explorer proof screenshot](studio_release_proof.png) shows the release address, deploy transaction and latest finalized calls. The transaction links above are authoritative for full hashes and outcomes.

The same release source was also deployed earlier at [`0x28011fa4C83D311d028Fb89A23827d4B6C704f48`](https://explorer-studio.genlayer.com/address/0x28011fa4C83D311d028Fb89A23827d4B6C704f48), [deployment `0xfb87d67778c660c49da0b4757ff73c6eb2e12f302cfbf6f2f3a893f6f61d312e`](https://explorer-studio.genlayer.com/tx/0xfb87d67778c660c49da0b4757ff73c6eb2e12f302cfbf6f2f3a893f6f61d312e), also `FINALIZED / SUCCESS / Accepted`. A browser-session reset removed that editor's local deployment panel, so the identical source was redeployed for final-instance transaction tests; the source SHA-256 matched both on-chain copies.

## Files and local tests

| Path | Purpose |
| --- | --- |
| `contracts/semantic_drift_registry.py` | Deployable Intelligent Contract, record types, independent validation, deterministic drift engine and public APIs |
| `tests/test_protocol.py` | 12 deterministic and adversarial tests using a minimal mocked GenLayer host |
| `PROTOCOL.md` | Frozen state machine, digest, verdict, flags, history, errors |
| `CONSENSUS.md` | Independent Web and LLM validation, exact critical comparison and evidence grounding |
| `SECURITY.md` | Threat model and remaining source limits |
| `docs/STUDIO_COMPATIBILITY.md` | Studio-specific runtime/API/SDK freeze and probe evidence |
| `README.md` | Setup, contract purpose and live proofs |

`python -m unittest discover -s tests -v` passed **12/12**. The tests cover registration and independent fetches, positive and negative baselines, representative deterministic verdict and flag paths, `RULE_APPEARED` / `RULE_DISAPPEARED`, condition and disposition change, deduplication, append-only adoption, owner/latest/cross-Watch guards, public cooldown with owner bypass, 404 and transport failures, size limit, invalid URL/target, strict payload and evidence rejection, HTML extraction and digest normalization. These local tests do not pretend to run the GenVM; the transactions below check the live Studio runtime separately.

## Live full-consensus tests on the release instance

| Test | Transaction / state | Result |
| --- | --- | --- |
| `NOT_STATED` initial Baseline, Watch 1 | [register](https://explorer-studio.genlayer.com/tx/0x3ce22ebdc6fe96e3f0cbec0daf99613a3580151bcc67a626b26d22697cab8fd1); finalized view: `presence=2`, `disposition=0`, `version=1` | `FINALIZED / SUCCESS / Accepted` |
| Fixed-page drift | [check](https://explorer-studio.genlayer.com/tx/0x8652eeec6ae492b45804ba314d045bd5eba0302938a3cfc0beb48e958863696f); finalized Observation 1: `source_status=1`, `verdict=1` (`NO_MATERIAL_DRIFT`), flags `0` | `FINALIZED / SUCCESS / Accepted` |
| Immediate owner repeat and dedup | [repeat check](https://explorer-studio.genlayer.com/tx/0xf2dca8201584166c4749962b87c26453c4ae2e9c78bf3ad8c127102feef84a13); finalized Watch 1: `check_count=2`, `observation_count=1`, `last_observation_id=1` | `FINALIZED / SUCCESS / Accepted` |
| Direct-quote `PRESENT` Baseline, Watch 2 | [IANA register](https://explorer-studio.genlayer.com/tx/0xe8c3e2a16af62ef2096a64b5f33100c7a920013e2806bde5edadd0ba81d296df); finalized view: `presence=1`, `disposition=2` (`PROHIBITED`), direct quotation from the registered URL | `FINALIZED / SUCCESS / Accepted` |
| `PRESENT` rule drift with semantically equivalent scope wording | [IANA check](https://explorer-studio.genlayer.com/tx/0x0d02e5869bba80929df72af0e7334556a45b94270a93d1fbe8681dadfec18286); finalized Observation 2: four `SAME` relations, `verdict=1`, flags `0` | `FINALIZED / SUCCESS / Accepted` |

**Unsuccessful live attempt:** an [earlier IANA registration](https://explorer-studio.genlayer.com/tx/0xad5adbbb3d8b797d7662d8acdb7d238f6ec8b8bb5aea83433bdbbc84218d92d4) on the same release instance finalized with consensus `Undetermined` after three leader rotations and validator disagreement. GenVM reported `SUCCESS`, but the consensus outcome was not accepted; finalized Watch count remained 0 until the fixed-page registration. This is a liveness failure for that attempt, not a successful Watch. The later IANA registration and check above succeeded. **No local tests failed.**

**Not yet exercised as a live mutable-page scenario:** material `CONDITION_CHANGED`, `RULE_APPEARED`, owner adoption, and three-Watch V1→V2 demo. Their deterministic branches passed local tests; public source publication and the demo sequence are later HANDOFF steps 40–53. External wallet signing, `genlayer-js` transaction and fee-estimation calls also await the frontend phase. Do not count any of those as a passed Studio end-to-end test.

## Frozen design and next phase

There is no intentional protocol change from the HANDOFF. The §66 limitation is explicit: Studio `gl.nondet.web.get` follows 30x, exposes `status:int` and `body:bytes`, and does not expose the final URL. The contract accepts one explicit HTTPS URL and never crawls page links; it cannot enforce a stronger cross-origin redirect guarantee. This affects strict source-boundary semantics and is documented in `STUDIO_COMPATIBILITY.md` and `SECURITY.md`. No compatibility branch for another network or alternate SDK was added.

The contract and its view/write interface are ready for Project frontend integration. The later frontend must validate external wallet signing, SDK RPC/finality and fee estimation against Studio itself; the Studio UI's zero-GEN account is not proof of those client flows. React work is intentionally paused as instructed. A local git repository with the required name exists; a remote GitHub repository could not yet be created with the available connection/session, so remote publishing and final submission proof remain open.

### Checkpoint

- **Project goal:** a public, auditable semantic policy drift registry and later Project UI, as frozen in the HANDOFF.
- **Stage goal achieved:** Intelligent Contract implementation, 12 local tests, full-consensus deployment and core Studio registration/check/dedup tests.
- **Frozen decisions:** Studio chain `61999`, one pinned Python SDK/import style, future `genlayer-js@1.1.8`, no multi-network branches, no protocol redesign.
- **Open work:** remote git publishing; later live mutable-page material/adoption demo; external wallet/fee/finality validation; React and Project tasks after stage review.
- **Rejected paths:** Bradbury and studio-dev for V1 implementation; interpreting `ACCEPTED` or `Undetermined` as final success; silently treating redirects as known same-origin.
- **Assumptions:** a stable public direct-200 policy URL and validators' ability to reach it are required for reliable source consensus.
