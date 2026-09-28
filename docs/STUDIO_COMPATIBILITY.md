# Studio-specific compatibility freeze

Frozen on 2026-09-28. PolicyDrift V1 targets **only** GenLayer Studio / Studionet, `https://studio.genlayer.com/api`, chain ID `61999`. Bradbury and studio-dev were researched earlier but are background only; this repository has no compatibility branch for either.

| Surface | Studio observation / choice | Evidence |
| --- | --- | --- |
| GenVM/Python | Studio GenVM `v0.2.16-x86_64-linux-release`; pinned `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6` | Studio built-in `storage.py`, GenVM execution logs, deployed probes |
| One import style | `from genlayer import *` | Studio built-in contract and full-consensus probe |
| Public contract API | `class Contract(gl.Contract)`, `@gl.public.write`, `@gl.public.view` | Deployed probe and SemanticDriftRegistry schema |
| Persistent storage | `@allow_storage @dataclass`, `TreeMap[u256, Record]`, `TreeMap[u256, DynArray[u256]]` | Full-consensus storage probe; nested array uses `get_or_insert_default(key).append(value)`. Direct `DynArray()` and missing-key `.append()` fail. |
| Custom consensus | `gl.vm.run_nondet_unsafe(leader_fn, validator_fn)`; `leader_fn` returns a serializable dict, `validator_fn(result: gl.vm.Result) -> bool` checks `isinstance(result, gl.vm.Return)` and `.calldata` | Full-consensus independent-web and LLM probes, validator Agree |
| Prompt JSON | `gl.nondet.exec_prompt(prompt, response_format="json")` returned a Python dict | Full-consensus LLM probe, persisted `{ "value": 7 }` |
| Web response | `gl.nondet.web.get(url).status` is an integer; `.body` is bytes; `.status_code` and `.url` absent | Full-consensus fetch of GenLayer test server |
| Redirects | `https://httpbin.org/redirect/1` returned final `200`; no final URL exposed | Full-consensus redirect probe; known limitation below |
| Sender, timestamp | `gl.message.sender_address` and `u256(int(time.time()))`; chain ID `gl.message.chain_id == 61999` | Persisted/read-back storage probe |
| Frontend SDK choice | Pin **`genlayer-js@1.1.8`**. Its published tarball's `chains.studionet` defines this endpoint and chain ID. Do not use the `2.0.0-rc.1` API. | npm package dist source/type declarations inspected |

For a later frontend, `createClient({ chain: chains.studionet, provider })` takes an EIP-1193 wallet provider; `writeContract({address,functionName,args,value:0n})` returns a hash; `estimateTransactionGas({to,from,data,value})` calls `eth_estimateGas`; `waitForTransactionReceipt({hash,status:TransactionStatus.FINALIZED})` polls finality; `getTransaction({hash})` includes `statusName`, `resultName`, `txExecutionResultName`. `ACCEPTED` alone is not proof of final success: inspect `FINALIZED` and success/error outcome, and treat `UNDETERMINED` separately. In Studio UI the built-in zero-GEN account deployed and submitted full-consensus writes. **Unverified for the future frontend:** an external wallet's signing flow, SDK RPC calls from this execution environment (direct RPC returned gateway 403), and actual gas estimation response; these are not asserted as passing tests.

## Known V1 source-boundary limit under HANDOFF §66

1. **Frozen requirement affected:** the single-URL public source boundary, if interpreted to require knowing whether a redirect changes the final origin.
2. **Studio limitation:** `gl.nondet.web.get` automatically follows HTTP 30x and exposes only the final status and body; it does not expose the effective/final URL.
3. **Minimum compatible behavior:** accept only one explicit registered HTTPS URL and never follow links in page content; tell operators to use stable direct-200 pages and record the redirect limitation. The code does not secretly crawl or rewrite the registered URL.
4. **Semantic impact:** an absolute same-origin/no-cross-origin-redirect guarantee cannot currently be enforced. A strict interpretation of that guarantee is blocked in Studio V1.

Other testable frozen consensus/storage mechanisms above have no identified core blocker. HTML that requires client-side JavaScript and private/authenticated pages remain outside V1.

## Proof transactions (Studio, full consensus)

- Independent web fetch: `0xd10d45844b43a1fe9e29a374f76f356e88f5f8a3c9e13540187e22ab9e4c6ab9` — FINALIZED SUCCESS.
- HTTP redirect: `0x79cbbe72e504fcc44c1f144d4e2e127a1c74c8a8719fe8c0b09cd7c3fd805a6b` — FINALIZED SUCCESS.
- Dataclass plus nested `DynArray`: `0xd94940c92c7326d3ba837460db66468a5d439516a6e573445de34a66117daf8e` — FINALIZED SUCCESS.
- JSON LLM result: deployed `0x54D6C9B2C5fb1F93F033e4C5Af000cE1112b5038`, full-consensus write finalized and read-back returned `{"value": 7}`.
- Release source and runtime: [deployment `0xc3cfc4e9e07cb90fc4d236c3d5e7eb76da23b8cb9edc4b40a3d32457285e01eb`](https://explorer-studio.genlayer.com/tx/0xc3cfc4e9e07cb90fc4d236c3d5e7eb76da23b8cb9edc4b40a3d32457285e01eb) — FINALIZED SUCCESS on chain 61999; explorer source SHA-256 `16b76c91a6960ea3c9fccdc5e10069c09f9ac8824befa20719f456ca2a67b4a5`, matching the local contract file. The [stage result](STUDIO_STAGE_RESULT.md) records final-instance calls and one Undetermined attempt.
