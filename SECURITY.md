# Security and known limits

- R1: A source owner may serve validator-specific content; consensus cannot prevent targeted source equivocation.
- R2: A temporary incorrect public page can become an accepted time-of-observation record if validators consistently saw it.
- R3: `NOT_STATED` is weaker negative evidence than a direct quote grounding `PRESENT`.
- R4: Future changes to LLM/model behavior may alter extraction and consensus outcomes.
- R5: Complex multi-document legal interpretation is outside the single-URL V1.
- R6: PolicyDrift is not legal advice or a legal judgment system.
- R7: Authenticated and private policy sources are unsupported.
- R8: Geo-personalized, A/B-tested, dynamic JavaScript-only, and unstable pages may produce inconsistent outcomes.

Studio Web Access follows HTTP redirects but exposes no final URL. A single explicitly registered source is passed to `web.get`, with no page-link crawling; a stronger guarantee that no cross-origin HTTP redirect occurred cannot be enforced on Studio V1. Prefer stable direct-200 public HTTPS policy pages. DNS hostnames resolving to private addresses are also not independently verifiable through this Web Access response; validation rejects literal IPs, localhost, URL credentials, fragments, and non-HTTPS schemes, but cannot attest every DNS resolution.

The 30,000-character limit applies to normalized page text; oversized pages are not silently truncated. A quoted excerpt is checked against independently fetched text after NFKC/whitespace normalization. Deterministic status and verdict guard 404s from becoming rule disappearance. The public cooldown may rate limit non-owners, while the Watch owner always bypasses it.
