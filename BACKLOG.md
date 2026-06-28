# The RAPP Adversarial Backlog — `rapp-backlog/1.0`

> **165 wrenches** thrown at the whole architecture by 8 red-team lenses + a completeness critic, so when we hit them from the real world the answer is already banked. **This does not block the build** — it's the long-term hardening backlog. `60 P0 · 76 P1 · 28 P2 · 1 P3`. Full machine-readable set: [`backlog.json`](backlog.json).

## The honest summary

The architecture is sound *as a research medium and a bottom-up on-ramp*, and the read path (static, content-addressed, hydra-mirrored) is genuinely hard to kill. The pressure concentrates in five places, all already on the roadmap: **(1)** the unauthenticated `/api/agent` RCE and the kernel-freeze-vs-real-bugs tension (you can't both freeze the kernel and patch a kernel CVE — needs a signed, versioned, rollback-tagged kernel-update channel that is itself not an engine edit); **(2)** the offline-LLM problem — an edge that loses its link also loses its *reasoner* unless a local model backs it; **(3)** enterprise rejection of public-GitHub telemetry (GDPR right-to-erasure vs immutable append-only logs, data residency) — the sealed/private layer must be the default for anything regulated; **(4)** single-vendor capture (GitHub owns transport, Microsoft owns the plane) — the hydra's multi-host story is the answer but must be real, not aspirational; **(5)** supply-chain (pip-auto-install, unsigned cartridges/frames) — everything executable must be signed + pinned + verified-before-run. None block a *pilot*; all must be answered before *scale*.

## Pre-solve first — the sharpest P0s (detail)

### The frame foundry is a single-tenant GitHub Actions cost sink that scales linearly with fleet size and hits a hard monthly quota
- **Scenario:** The foundry forges a per-edge echo from telemetry on every contact, implemented as a GitHub Action. Actions minutes are metered and capped: ~2,000-3,000 free min/month per account, then ~$0.008/min (linux). One echo-forge job is seconds, but millions of edges 
- **Mitigation (banked):** Bank a foundry-economics model: tokens-and-minutes per echo, echos/edge/day, break-even fleet size. Make forging incremental/debounced (only re-forge when telemetry hash changes, batch many edges per job), move heavy forging off Actions onto the operator's own
- **Horizon:** 0-3mo · residual: Batching adds echo latency (an edge's guidance is staler), and any operator who under-provisions still has a fleet-wide 

### Telemetry-via-Issues-API shares ONE per-account quota bucket — a few hundred active edges trip GitHub's secondary rate limits
- **Scenario:** Edges write telemetry append-only via the GitHub Issues API. Authenticated REST is 5,000 req/hr PER ACCOUNT (not per edge), with secondary limits of roughly 80 content-creation requests/min and aggressive abuse detection specifically on bulk issue/comment crea
- **Mitigation (banked):** Bank a write-fan-out design: shard telemetry across many repos/accounts (per-region or per-cohort) so each stays under 5k/hr, give each edge (or twin) its OWN installation token so quota is per-edge not per-fleet, switch telemetry to git-push of append-only bl
- **Horizon:** 0-3mo · residual: Sharding multiplies the key-management and discovery problem (now you have N accounts to secure and rotate), and any sin

### No per-edge budget ceiling — one confusing echo can trigger fleet-wide runaway spend (infinite-loop-equals-infinite-bill, at planetary scale)
- **Scenario:** /chat runs up to 3 tool rounds (for _ in range(3)) but an edge LLM that keeps getting a confusing echo can re-enter /chat indefinitely on its own cadence, each pass burning Copilot tokens AND writing telemetry (more Issues-API quota). There is no per-edge toke
- **Mitigation (banked):** Bank a per-edge budget governor: a daily token + API-write budget enforced in the call_copilot seam, an exponential circuit breaker that drops the edge to 'degrade-to-one, act on last good echo, stop calling LLM' when spend/loop-rate exceeds threshold, and a g
- **Horizon:** 0-3mo · residual: A governor that trips fleet-wide turns an economic-DoS into an availability-DoS (the swarm goes quiet to protect the wal

### Issues-as-write-API trips GitHub secondary-rate-limit/abuse detection and bans the account — killing the whole swarm's write path at once
- **Scenario:** Telemetry is appended via the Issues API. That is precisely the pattern GitHub's abuse heuristics flag: high-frequency programmatic content creation from one account. Secondary rate limits (separate from the documented 5000/hr primary) trip on 'creating conten
- **Mitigation (banked):** Bank: (1) Define a Transport interface NOW (read/write/heartbeat) so GitHub is one pluggable impl, not the architecture. (2) Batch telemetry into ONE append per cadence per edge (e.g., a single appended file blob via contents API or one Issue comment per windo
- **Horizon:** 0-3mo · residual: Even batched, a planetary fleet cannot durably use one account as a write bus (see throughput wrench). Mitigations buy h

### HMAC-signed frames use a SHARED secret — every edge that can verify can forge; one compromised edge or the CI secret is a swarm-wide skeleton key
- **Scenario:** 'HMAC now' means a symmetric key. Verification and forgery use the same secret, so every edge holding the verify key can mint a validly-signed echo telling the whole swarm to do anything. The prev-hash chain offers no protection — the attacker holds the signin
- **Mitigation (banked):** Bank: (1) Move the root of trust to asymmetric signing (Ed25519/ECDSA, already 'planned') BEFORE any multi-edge or untrusted-edge deployment; edges hold only PUBLIC keys, forging requires the private key. (2) Custody the private key OUTSIDE GitHub Actions — a 
- **Horizon:** 0-3mo · residual: Asymmetric keys narrow forgery to whoever holds the private key/KMS access; the foundry that calls the signer remains a 

### Public Issues/state.json telemetry is world-readable forever — edge telemetry is a permanent data-exfiltration broadcast (archived, cloned, trained on)
- **Scenario:** Telemetry to public Issues and state.json on a public repo is globally readable, mirrored by GHArchive, clonable, and harvested into training corpora. Real edge telemetry — location, sensor readings, operational state, possibly PII or mission-sensitive data — 
- **Mitigation (banked):** Bank: (1) Separate the public TWIN (identity + verify key + coarse last-known) from PRIVATE telemetry — telemetry goes to a private repo/private channel/Purview, never public Issues. (2) Encrypt telemetry payloads to the foundry's key so even a private-repo le
- **Horizon:** 0-3mo · residual: Encryption + private channels fix confidentiality going forward but anything already published is permanently exposed; m

### No Entra Agent ID — autonomous agents impersonate a human's Copilot OAuth token
- **Scenario:** Agent 365's non-negotiable premise is that every agent is a first-class non-human identity in Entra (Agent ID), governed by Conditional Access, lifecycle, and least privilege. The brainstem instead runs autonomous, tool-executing agents under a HUMAN user's Gi
- **Mitigation (banked):** Define a mapping where each brainstem/edge and each agent cartridge gets an Entra Agent ID; exchange GitHub auth for an Entra workload token at the boundary; carry agent identity through /chat and the Leviathan wire so every action is attributable to an agent 
- **Horizon:** 0-3mo · residual: Tier-1 (Copilot-only, no Entra) remains ungoverned; you must hard-gate it out of enterprise tenants, and the dual-identi

### Telemetry as public GitHub Issues is an uncontrolled, immutable, cross-boundary exfiltration channel
- **Scenario:** Edges write telemetry append-only via the GitHub Issues API, and /diagnostics/report already opens public issues with only a 3-key scrub ({user_code, device_code, session_id}). Everything else in event data — prompts, file paths, agent outputs, hostnames, erro
- **Mitigation (banked):** Invert to deny-by-default: telemetry carries only an allowlisted, typed schema of non-sensitive fields; everything else dropped at source. Route telemetry to an in-tenant sink (Log Analytics / Sentinel / a tenant-owned private store) with Purview governance; p
- **Horizon:** 0-3mo · residual: Schema drift can still leak; redaction is probabilistic; and the community/public mode remains a tempting misconfigurati

### _auto_install pip-installs package names derived from a malicious agent's import error
- **Scenario:** On agent import, a ModuleNotFoundError feeds _extract_package_name, and _auto_install runs `pip install <name>` from public PyPI with no pin, no hash, no private feed, no allowlist. A dropped agent that does `import totall-legit-lib` (a typosquat / dependency-
- **Mitigation (banked):** Remove silent auto-install in enterprise mode. Resolve only against a curated, hash-pinned internal index (Azure Artifacts) with an allowlist; require explicit operator approval for any new dependency; record an SBOM per agent. Never derive an install target f
- **Horizon:** 0-3mo · residual: Curated feed still inherits upstream PyPI compromises until mirrored+scanned; approval fatigue leads operators to rubber

### Agents/cartridges/.eggs are unsigned, unscanned code with no provenance attestation
- **Scenario:** 'Capability-as-a-signed-object' currently means HMAC with a shared secret (Ed25519/ECDSA 'planned'). Community agents from RAR and portable .eggs are arbitrary Python ingested and executed. There is no code signing with a real trust root, no SBOM, no SLSA prov
- **Mitigation (banked):** Move to asymmetric per-publisher signing (Ed25519/Sigstore-style) with an identity-bound key, mandatory SBOM + provenance, automated malware/secret/static-analysis gate before an object is installable, and a revocation list. Map publisher identity to Entra. Tr
- **Horizon:** 0-3mo · residual: Signing proves origin, not safety; a legitimately-signed-but-malicious-or-buggy agent still runs. Key compromise + slow 

### HMAC + public verify key in the twin = every edge is forgeable on day one (no asymmetry, no revocation)
- **Scenario:** The plan is 'HMAC now / Ed25519 / ECDSA planned,' and every edge has a PUBLIC twin.json carrying its verify key. HMAC is SYMMETRIC: the verify key IS the signing key. Publishing it in a world-readable twin.json means anyone who reads the twin can mint perfectl
- **Mitigation (banked):** Never ship HMAC alongside public twins — go asymmetric (Ed25519) from the first pilot; only the public verify key is ever published. Bake key lifecycle into the FRAME FORMAT now: every signed object carries (key-id, valid-from-tick, valid-to-tick); ship a sign
- **Horizon:** 0-3mo · residual: Asymmetric crypto on tiny intermittent edges costs CPU/storage; revocation still can't reach an offline edge faster than

### Content-addressing is integrity, not authenticity — and the canonical-hash index is the unsigned root
- **Scenario:** Specs/cartridges are content-addressed and rapp-god detects drift against the 'canonical hash.' But content-addressing only proves 'you got the bytes this hash names' — if an attacker gets a MALICIOUS artifact's hash into the canonical index (via a typo'd pin,
- **Mitigation (banked):** Separate authenticity from integrity: the canonical index must be SIGNED by an offline org root key, not just hosted; require signed, reviewed, multi-party-approved updates to canon (branch protection + required reviews + signed commits + tag protection); keep
- **Horizon:** 0-3mo · residual: An offline root key still has a compromise/loss story; multi-party review slows legitimate publishing; an attacker who c

### Leviathan is a built-in botnet C2 with a clean API — adding auth is necessary but not sufficient
- **Scenario:** POST /api/agent/<name>: one external mind drives many no-LLM bodies directly. Even AFTER auth is added, the design IS structurally command-and-control fan-out: a single LEGITIMATELY-authed driver that gets phished/stolen becomes a fleet-wide actuator in one re
- **Mitigation (banked):** Auth is table stakes; add per-body authorization and capability scoping (a driver is granted specific agents on specific bodies, not '*'); rate-limit and require quorum/human confirm for fan-out beyond N bodies; give even no-LLM bodies a minimal local policy v
- **Horizon:** 0-3mo · residual: A compromised authorized driver within its granted scope still does real damage; per-body scoping is operationally heavy

### latest.json / the chain-head pointer is the unsigned root — spoof the POINTER, replay a genuinely-valid frame
- **Scenario:** Even with perfectly signed frames, an edge learns WHICH frame is current from latest.json {tick, hash, updated} (the 'cheap heartbeat pointer'). If that pointer is unsigned (or signed but not freshness-bound), an attacker — a stale CDN edge of raw.githubuserco
- **Mitigation (banked):** Sign latest.json itself, and bind it for freshness: include a monotonic tick + a signed 'as-of' and a max-staleness window, and bind it to the current chain-head hash. Edge persists highest-seen tick to durable storage and rejects any pointer whose tick <= las
- **Horizon:** 0-3mo · residual: A long-offline edge legitimately has a stale head and a wide acceptance window by design (degrade-to-one), so a 'just sl

## P0 — before any real pilot (60)

| Wrench | Horizon | Mitigation (banked) |
|---|---|---|
| The frame foundry is a single-tenant GitHub Actions cost sink that scales linear | 0-3mo | Bank a foundry-economics model: tokens-and-minutes per echo, echos/edge/day, break-even fleet size. Make forging incremental/debounced (only |
| Telemetry-via-Issues-API shares ONE per-account quota bucket — a few hundred act | 0-3mo | Bank a write-fan-out design: shard telemetry across many repos/accounts (per-region or per-cohort) so each stays under 5k/hr, give each edge |
| No per-edge budget ceiling — one confusing echo can trigger fleet-wide runaway s | 0-3mo | Bank a per-edge budget governor: a daily token + API-write budget enforced in the call_copilot seam, an exponential circuit breaker that dro |
| Issues-as-write-API trips GitHub secondary-rate-limit/abuse detection and bans t | 0-3mo | Bank: (1) Define a Transport interface NOW (read/write/heartbeat) so GitHub is one pluggable impl, not the architecture. (2) Batch telemetry |
| HMAC-signed frames use a SHARED secret — every edge that can verify can forge; o | 0-3mo | Bank: (1) Move the root of trust to asymmetric signing (Ed25519/ECDSA, already 'planned') BEFORE any multi-edge or untrusted-edge deployment |
| Public Issues/state.json telemetry is world-readable forever — edge telemetry is | 0-3mo | Bank: (1) Separate the public TWIN (identity + verify key + coarse last-known) from PRIVATE telemetry — telemetry goes to a private repo/pri |
| No Entra Agent ID — autonomous agents impersonate a human's Copilot OAuth token | 0-3mo | Define a mapping where each brainstem/edge and each agent cartridge gets an Entra Agent ID; exchange GitHub auth for an Entra workload token |
| Telemetry as public GitHub Issues is an uncontrolled, immutable, cross-boundary  | 0-3mo | Invert to deny-by-default: telemetry carries only an allowlisted, typed schema of non-sensitive fields; everything else dropped at source. R |
| _auto_install pip-installs package names derived from a malicious agent's import | 0-3mo | Remove silent auto-install in enterprise mode. Resolve only against a curated, hash-pinned internal index (Azure Artifacts) with an allowlis |
| Agents/cartridges/.eggs are unsigned, unscanned code with no provenance attestat | 0-3mo | Move to asymmetric per-publisher signing (Ed25519/Sigstore-style) with an identity-bound key, mandatory SBOM + provenance, automated malware |
| HMAC + public verify key in the twin = every edge is forgeable on day one (no as | 0-3mo | Never ship HMAC alongside public twins — go asymmetric (Ed25519) from the first pilot; only the public verify key is ever published. Bake ke |
| Content-addressing is integrity, not authenticity — and the canonical-hash index | 0-3mo | Separate authenticity from integrity: the canonical index must be SIGNED by an offline org root key, not just hosted; require signed, review |
| Leviathan is a built-in botnet C2 with a clean API — adding auth is necessary bu | 0-3mo | Auth is table stakes; add per-body authorization and capability scoping (a driver is granted specific agents on specific bodies, not '*'); r |
| latest.json / the chain-head pointer is the unsigned root — spoof the POINTER, r | 0-3mo | Sign latest.json itself, and bind it for freshness: include a monotonic tick + a signed 'as-of' and a max-staleness window, and bind it to t |
| The frame foundry is a GitHub Action holding the signing secret — the real root  | 0-3mo | Get the private key OUT of the runner: sign via GitHub OIDC -> cloud KMS/HSM so the key is never materialized in the Action; or use an offli |
| Copilot token TTL is a silent kill-switch shorter than the contact window | 0-3mo | Mint a long-lived, edge-scoped delegated credential at provisioning (Entra Agent ID / device-bound token) with offline-tolerant refresh, OR  |
| Stale-guidance destructive action — the month-old echo that confidently does har | 0-3mo | Every echo carries an explicit freshness budget / confidence half-life and a valid-until tick. Past expiry the edge MUST downgrade to conser |
| GitHub Issues as the write transport: public-writable injection, abuse limits, a | 0-3mo | Sign EVERY telemetry payload with the edge's private key; the foundry trusts the SIGNATURE, never the GitHub issue author, and rejects unsig |
| The public twin is a spoofing and command-injection surface (self-asserted verif | 0-3mo | Anchor each edge's key to a trust ROOT (keypair registered at provisioning in a signed swarm roster / rapp-moment ECDSA identity), not self- |
| Reconciliation is an unspecified, non-deterministic, unlogged hallucination | 0-3mo | Make reconciliation STRUCTURED and LOGGED: the LLM may only choose within an envelope the echo defines (guidance sets HARD constraints the m |
| Echo as prompt-injection / confused-deputy into the edge LLM | 0-3mo | Echos carry STRUCTURED guidance (typed: goal, constraints, action-allowlist, params), not freeform instructions executed verbatim; the deter |
| Forked frame chain / two heads — single-writer is never enforced | 0-3mo | Enforce single-writer: GitHub Actions concurrency group (group: foundry, cancel-in-progress: false) so foundry runs serialize. Require a str |
| Telemetry-via-GitHub-Issues is forgeable, editable, and Sybil-able — the 'append | 0-3mo | Telemetry payloads MUST be signed by the edge's twin key; the foundry records and processes the immutable signed blob, ignoring the live (ed |
| Echo-forge GitHub Action is a centralized SPOF and a fleet-wide blast-radius com | 0-3mo | Lean hard on DEGRADE-TO-ONE — edges keep functioning on last verified echo, so outage is survivable IF echo-staleness is bounded and the edg |
| Echos are an attacker-reachable prompt-injection channel feeding the edge LLM wi | 0-3mo | Add a hard, NON-LLM safety kernel at the edge: deterministic interlocks (geofence, power floor, irreversible-action gate) that NO frame/echo |
| The frame foundry (a GitHub Action) is the crown jewel and a classic software-su | 0-3mo | Pin every Action by full commit SHA; minimal GITHUB_TOKEN permissions; NO pull_request_target with secrets. Move the signing key to an HSM o |
| HMAC 'now' means a shared symmetric secret signs swarm-shared frames — one leake | 3-9mo | Treat Ed25519 (or rapp-moment ECDSA) per-publisher signing as P0, not 'planned': only the foundry/authority holds a signing private key; edg |
| The unit economics never close because there is no payer of record, no metering, | 3-9mo | Bank the COGS model as a deliverable: instrument tokens-in/out + API writes + Actions minutes per edge, derive $/edge/day under copilot|azur |
| The .egg as a 'signed capability object' is a planetary malware-distribution cha | 3-9mo | Bank a supply-chain gate: pin and hash-lock all pip deps inside the .egg (no open-ended install at import), require a signature from a known |
| GitHub-as-control-plane is a separate trust/compliance/residency boundary Condit | 3-9mo | Abstract the transport behind a pluggable substrate interface; ship an Azure-native backend (Storage + Queues/Service Bus, or an Agent 365 c |
| The unsigned latest.json heartbeat is the rollback root-of-trust — signed frames | 3-9mo | Sign latest.json too, and make freshness first-class: include a monotonic tick + a not-before/not-after timestamp + the signer's key-id in t |
| Echo poisoning via Byzantine-but-signed telemetry: one compromised edge poisons  | 3-9mo | Foundry must do Byzantine filtering, not blind relay: cross-check each edge's telemetry against siblings/priors, bound rate-of-change, quara |
| Prompt-injection through the frame/echo channel into the edge's reconciling LLM | 3-9mo | Treat all frame/echo/inbox text as untrusted data, never instructions: structured, typed guidance fields (waypoints, setpoints, constraints) |
| The frame foundry Action is the crown jewel — CI holds the master signing key an | 3-9mo | Never use pull_request_target with checkout of untrusted code; pin all Actions by full SHA; minimum-privilege GITHUB_TOKEN; move signing to  |
| Light-delay makes incident response physically too slow — the model must be fail | 3-9mo | Design for containment, not response: edges treat SIBLING-derived guidance as strictly lower trust than foundry-signed echos; the foundry ne |
| Byzantine rogue edge: an honestly-signed liar poisons the foundry and every sibl | 3-9mo | Byzantine-tolerant fusion at the foundry: cross-check telemetry against siblings, physics, and plausibility before it can influence shared f |
| Agent 365 cannot govern an edge that acts offline for days — the productization  | 3-9mo | Reframe to Agent 365 as POLICY-AT-PROVISIONING + ATTESTED-REPLAY: Entra issues the Agent ID and binds a signed POLICY ENVELOPE into the echo |
| The canonical-hash trust anchor lives in a repo on a free GitHub account — a sin | 9-18mo | Bank trust-root resilience: pin the canonical root by hash in each edge out-of-band (not just by URL), mirror the canonical corpus across mu |
| The kernel-freeze is a security liability: the found bugs ARE kernel bugs, and t | now | Separate 'frozen interface/behavioral contract' from 'frozen bytes': allow a SIGNED kernel security-update channel (versioned, hash-pinned,  |
| pip-auto-install-at-import is an unpinned, dependency-confusable PyPI supply-cha | now | Never auto-install at import in any non-dev posture: require a pre-vetted, hash-pinned dependency lockfile per cartridge that is part of the |
| The cost basis is a borrowed Copilot seat — the whole 'no API keys = free' pitch | now | Bank a first-party billing path NOW: an adapter that swaps the borrowed-Copilot transport for (a) the customer's own Azure OpenAI / Agent 36 |
| Leviathan's unauthenticated /api/agent is present-tense fleet-wide RCE and a Cop | now | Bank mutual auth + capability scoping before any non-loopback bind: bind to 127.0.0.1 by default, require a per-body token / mTLS for /api/a |
| GitHub raw CDN staleness silently corrupts the heartbeat and the verify-before-a | now | Treat raw as best-effort and NEVER as a consistency source. Bank: (1) every frame/echo carries a monotonic per-edge tick + wall-clock 'forge |
| Leviathan POST /api/agent/<name> is unauthenticated and a shell-capable cartridg | now | Bank and prioritize: (1) Authenticate /api/agent/* before ANY non-loopback deployment — mutual token / mTLS / signed-request with a per-body |
| Unauthenticated /agents/import + 0.0.0.0 bind + open CORS = remote drive-by RCE, | now | Bind 127.0.0.1 by default; require explicit opt-in + bound token for any non-loopback bind. Replace CORS(app) with an explicit origin allowl |
| Leviathan /api/agent/<name> is fleet-wide RCE from one unauthenticated request | now | Mutual auth on the Leviathan wire: each body verifies a signed, short-lived driver credential (mTLS or signed nonce challenge); per-body cap |
| Driving GitHub Copilot via the internal token-exchange for an autonomous multi-a | now | For the enterprise tier, swap the inference plane to a licensed surface (Azure OpenAI / Foundry models / Agent 365's own model access) with  |
| 0.0.0.0 bind + unauth /agents/import = present-day RCE via DNS rebinding, no LAN | now | Bind 127.0.0.1 by default; require an explicit opt-in env var to bind 0.0.0.0. Add an Origin/Host allowlist check (reject cross-origin and n |
| Verify-at-import, execute-from-disk-every-request = TOCTOU live-swap defeats ALL | now | Verify-on-execute, not verify-on-import: hash each agent file at load time against a signed manifest, refuse to run on mismatch. Or load-onc |
| Content-addressing is being used as authenticity — but a hash of attacker-chosen | now | Draw a hard line in the spec between integrity (hash, accidental corruption) and authenticity (signature, motivated adversary). Every object |
| HMAC shared-secret means every verifier is a forger — one rover's disk = swarm-w | now | Never ship HMAC as the trust root for the foundry->edge (guidance) direction. Use asymmetric signatures (Ed25519) from day one for anything  |
| Fail-open: an edge that CANNOT verify is the cheapest, most devastating attack — | now | Make verify-before-act FAIL-CLOSED for NEW guidance: an unverifiable new echo/frame is DISCARDED, full stop. Redefine 'degrade-to-one' preci |
| The offline brainstem cannot think — cognition is a cloud dependency wearing a l | now | Decouple cognition from transport with a 'cognition provider' interface: Copilot is the ON-LINK provider only; an on-device SLM (Phi-3/llama |
| HMAC-now signing = one shared secret = swarm-wide forgery from any single edge | now | Treat HMAC as DEV-ONLY and add a CI invariant that production frames must be asymmetric-signed (Ed25519 / rapp-moment ECDSA) so private keys |
| No human-in-the-loop on irreversible actions — and light-delay makes synchronous | now | Define an action-class taxonomy with autonomy levels: reversible+low → autonomous; irreversible/high → require a pre-authorization token IN  |
| HMAC symmetric secret = any one edge can forge frames/echos for the entire swarm | now | Move frames/echos to asymmetric signatures IMMEDIATELY for the planetary wire (Ed25519, or rapp-moment ECDSA per the plan): edges hold ONLY  |
| The foundation is already unauthenticated AND mutating — caller identity does no | now | Bind loopback-only by default with an explicit opt-in to expose. Require a local capability bearer token on ALL mutating routes (/chat, /age |
| Identity is bound to a keypair and a repo PATH, not to a vetted edge — signature | now | Make identity = the public KEY fingerprint (or content hash of a signed enrollment record), NOT the path/name — the GitHub path is a mere di |
| Frame authority capture — HMAC is symmetric, so every verifier can forge; even E | now | NEVER ship HMAC for cross-trust-boundary frames — it conflates sign and verify. Asymmetric from day one for anything multi-party. Make frame |
| Replay, rollback, and equivocation on a cached, eventually-consistent, append-on | now | Bake monotonicity into the wire format NOW: every signed frame carries an epoch + strictly-increasing tick + timestamp; edges reject any non |

## P1 — before scale (76)

| Wrench | Horizon | Mitigation (banked) |
|---|---|---|
| Honest operator error has no undo at light-delay, and offline-root-key LOSS (not | 0-3mo | Make destructive/objective-changing echos require a typed confirmation + a second human signer (threshold) + a mandatory soak/dry-run window |
| Immutable, append-only, content-addressed, publicly-archived telemetry is struct | 0-3mo | Keep personal data OFF the immutable chain entirely: the chain stores only signed hashes/commitments; the actual payload lives in a mutable, |
| Token-cost amplification per tick: 3-round loop × full-history resend × full age | 0-3mo | Bank a token-budget model and caching: use provider prompt-caching (Anthropic/Azure) for the static soul+metadata prefix once off the borrow |
| Synchronized contact windows create a thundering herd that trips secondary rate  | 0-3mo | Bank backpressure-by-design: randomized jitter on every edge's contact schedule, client token-bucket + exponential backoff with respect for  |
| Model-'auto' plus model-hopping on 429 is the exact traffic signature GitHub ant | 0-3mo | Bank honest backoff: on 429 respect Retry-After and back off rather than immediately model-hopping; reserve model-fallback for genuine model |
| Install one-liner pulls from main — a planetary fleet bootstraps from an unpinne | 0-3mo | Bank installer supply-chain hygiene: sign the installer and verify the signature before exec, pin installs to an immutable tag (BRAINSTEM_VE |
| Using GitHub as a CDN + app backend + telemetry datastore is an Acceptable-Use-P | 0-3mo | Bank: (1) Multi-home from day one behind the Transport interface — mirror frames to >=2 independent origins (e.g., a second git host + an ob |
| No replay/freshness enforcement: an offline-reconnecting edge can be fed an old- | 0-3mo | Bank: (1) Per-edge monotonic tick: reject any echo with tick <= last-applied; persist last-applied across reboots. (2) Explicit valid_until/ |
| No Transport abstraction seam — READ is hardcoded to raw and WRITE to Issues, so | 0-3mo | Bank and do early: (1) Define a Transport interface NOW — read_object(hash), read_pointer(), append(record), even while GitHub is the only i |
| Kernel-lock blocks security remediation of the kernel's own attack surface | 0-3mo | Carve out an explicit, fast-track security-exception path in the governance model: kernel security patches are permitted, expedited, and sig |
| Memory / ContextMemory is an unsigned, auto-injected, self-reinforcing prompt-in | 0-3mo | Treat memory as untrusted data with provenance: tag every memory entry with who/what wrote it and never let memory content be interpreted as |
| Signed .egg teaches users 'signed = safe' — pre-arming the social-engineering ex | 0-3mo | In UX and docs, signature == 'who made this,' never 'this is safe' — show identity + reputation, require a separate consent for code that bo |
| Replay / rollback of a validly-signed OLD frame — signatures never expire, and ' | 0-3mo | Make freshness intrinsic to the frame, not just the pointer: include a monotonic per-edge tick and a signed valid-for-N-ticks / not-after, a |
| Runaway autonomous loop → actuator/battery burn and reconnect telemetry storm | 0-3mo | Hard local governors INDEPENDENT of cognition: max-actions-per-interval, energy budget, actuator duty-cycle caps, and a watchdog that forces |
| Revocation latency equals connectivity latency — you can't recall a key from a d | 0-3mo | Make safety fail-safe by TTL, not by reachability: short echo validity windows so a stale (possibly-revoked) echo expires on its own. Requir |
| latest.json heartbeat is a forgeable/replayable liveness lie, and raw CDN cachin | 0-3mo | latest.json carries a SIGNED monotonic tick + foundry timestamp; the edge enforces monotonicity (never accept a tick ≤ last-seen) → replays  |
| Copilot ToS and per-account rate limits make fleet cognition a thundering-herd o | 0-3mo | Per-edge identity and quota via Entra Agent ID + a sanctioned fleet inference endpoint (Azure OpenAI), NOT shared personal Copilot — this is |
| Replay and reordering attacks on the append-only telemetry/echo log | 0-3mo | Every signed message includes a monotonic nonce/tick + edge-id; each consumer tracks a per-edge high-water mark and rejects anything ≤ seen  |
| The universal 'safe-state / hold' fallback is itself catastrophic in inaction-fa | 0-3mo | Require each edge/domain to declare a DOMAIN-SPECIFIC FAILSAFE ROUTINE — deterministic, validated, NO-LLM (e.g., 'maintain current setpoint, |
| latest.json pointer/content TOCTOU across the raw CDN | 0-3mo | Treat latest.json strictly as a HINT, never as truth. Verify by (a) fetching the named frame, (b) checking its signature, (c) confirming it  |
| Clock skew on tick/sol — wall-clock causality on a body where wall-clock is mean | 0-3mo | Never use wall-clock for causality. Tick = a foundry-assigned monotonic SEQUENCE on the frame chain (logical clock). Edge telemetry carries  |
| Out-of-order, lost, and duplicate telemetry over an intermittent link — record i | 0-3mo | Every telemetry record carries a stable idempotency key (edge_id + edge_seq + content-hash); foundry dedupes on it. Prefer last-writer-wins  |
| Twin state.json vs live brainstem: stale last-known masquerades as current state | 0-3mo | state.json must carry its own as-of tick and an explicit staleness/age. Consumers MUST decay confidence with age and treat twin state as las |
| Replay / rollback of validly-signed old frames and echos | 0-3mo | Consumers enforce strict MONOTONICITY: never accept a frame/echo whose tick/seq is <= last-applied, and persist last-applied durably across  |
| New-edge trust bootstrap: TOFU over the untrusted GitHub wire owns an edge from  | 0-3mo | Bake the foundry public verify key + genesis hash into the .egg / edge image OUT-OF-BAND via signed provisioning — never fetch the root of t |
| Action idempotency: re-reading an inbox echo after reboot re-executes the physic | 0-3mo | Edge durably persists 'last-applied echo-seq' and NEVER re-executes an echo at or below it, even after reboot. Echos carry an idempotency to |
| Force-push / history rewrite quietly violates 'append-only' on a mutable git bra | 0-3mo | Protected branch with force-push DISABLED, required linear history, and no direct human pushes (foundry-only via reviewed workflow). Consume |
| Telemetry poisoning — lie to the foundry through the channel it trusts and it fo | 0-3mo | Every telemetry item must be SIGNED by the originating edge's key; the foundry verifies origin before ingesting — no anonymous Issue becomes |
| No revocation story over a one-way, light-delayed, append-only, server-less wire | 0-3mo | Design revocation IN NOW, not later. Short-lived signing keys with frequent rotation so the default blast radius is a window, not forever. A |
| HMAC-now creates a downgrade attack and an unattributable shared-secret leak dur | 0-3mo | Treat HMAC as DEV-ONLY / single-trust-domain — never let HMAC and asymmetric be acceptable for the same trust boundary; no negotiated downgr |
| Confused-deputy: the foundry/twin holds the union of all authority and the inbox | 0-3mo | Strict origin-binding and least authority in the foundry: edge B's echo is a pure function of B's OWN signed telemetry plus the swarm frame, |
| Frozen kernel vs churning upstream: Copilot auth/model deprecation, GitHub API c | 3-9mo | Isolate all volatile upstream contracts behind a thin, updatable ADAPTER layer that is explicitly NOT part of the frozen kernel (auth flow,  |
| raw.githubusercontent.com is a ~5-minute-TTL CDN with no SLA and geo-blocking —  | 3-9mo | Bank transport-realism: treat latest.json as eventually-consistent with an explicit max-staleness budget surfaced to the edge LLM ('this ech |
| Frame/echo poisoning: 'verify-before-act' checks the signature, not the wisdom — | 3-9mo | Bank semantic guardrails: constrain what guidance CAN change (echos carry data/aims, never security policy, trust roots, or executable instr |
| Observability across a planet with no server: you're blind by design, and the on | 3-9mo | Bank an observability tier: lightweight per-edge health beacons (a tiny signed status.json the twin updates) cheaper than full telemetry, a  |
| GitHub is hard-blocked for whole classes of edges (GFW, sanctions, corp proxies, | 3-9mo | Bank: (1) Reframe GitHub as the DEFAULT Earth-connected transport, not THE wire; the Transport interface must admit store-and-forward bundle |
| raw.githubusercontent.com refuses to serve files >100MB — the append-only ledger | 3-9mo | Bank: (1) Segment the ledger: rolling windowed log files (frames-<epoch>.jsonl) with a small always-fresh latest.json pointer + a manifest o |
| Issues-as-ledger throughput is capped at ~one account's rate limit regardless of | 3-9mo | Bank: (1) Hierarchical aggregation: edges report to regional aggregators/twins; only aggregators write to the ledger, collapsing N edges int |
| The frame foundry is a GitHub Action — Actions outages/quotas/scheduler-drift fr | 3-9mo | Bank: (1) Make the foundry portable (plain container/process) so it can run off-GitHub (a tiny VM, a function, on-prem) — Actions is one hos |
| Copilot token + sessions are plaintext on disk with no Purview/DLP, eDiscovery,  | 3-9mo | Store secrets via OS keychain / Key Vault, never plaintext. Emit a tamper-evident, append-only audit of every tool invocation to an in-tenan |
| No Defender/XDR visibility — compromised or rogue agents are invisible to the SO | 3-9mo | Ship a Defender/MDE sensor hook and Sentinel connector emitting agent-action and anomaly events; define detections (unexpected shell agent,  |
| Echo/frame poisoning: signed-but-malicious guidance steers the edge LLM into har | 3-9mo | Treat all frame/echo/telemetry content as untrusted data, never instructions: strict structured schemas (typed fields, no free-form imperati |
| Frame-foundry GitHub Action is CI/CD-as-the-forge — workflow compromise = forge  | 3-9mo | Harden the foundry like a production signing service: isolated, least-privilege runner; OIDC short-lived creds not stored secrets; pinned ac |
| Security controls implemented as agents are bypassable — no mandatory, non-remov | 3-9mo | Define a fail-closed policy kernel: identity, authz, audit emission, and DLP gating live in the protected core (not in removable agents) and |
| GitHub is an unSLA'd, ToS-constrained single point of failure for the entire con | 3-9mo | Get explicit AUP sign-off or move to GitHub Enterprise / Azure-native substrate with real SLAs for enterprise tier; implement rate-limit bac |
| Multi-tenant data bleed through shared canonical twins, frames, and community ag | 3-9mo | Hard tenant-scoped namespaces with no implicit cross-tenant object sharing; enterprise canon/frames live in a tenant-bound substrate; explic |
| Stored prompt-injection via memory + the 3-round tool loop = injection-to-action | 3-9mo | Privilege-separate the tool loop: data-plane content can never directly authorize high-impact tools; require explicit human-approval (or a s |
| GitHub as transport = someone else's kill-switch, ToS, rate-limiter, and legal d | 3-9mo | Treat GitHub as ONE transport behind an abstraction, not THE transport — define a transport interface so frames/echos/telemetry can also flo |
| 'Append-only telemetry via Issues API' is neither append-only nor authenticated- | 3-9mo | Require every telemetry issue to be signed by a known edge key and reject all others at ingest (don't trust GitHub identity); capture and pi |
| Twin squatting + TOFU first-contact: register a Mars edge's twin before it ever  | 3-9mo | Pre-provision each edge's identity out-of-band BEFORE deployment: its public key and canonical twin path are registered in the SIGNED canoni |
| Twin inbox = unauthenticated command mailbox + precious-bandwidth DoS | 3-9mo | Inbox writes must be signed by allowlisted senders only; the edge fetches a signed manifest of inbox contents and pulls only verified items, |
| Replay of public telemetry + tick rollback across reboot/clock-skew (Mars has no | 3-9mo | Enforce strict tick monotonicity at BOTH foundry and edge, persisted in tamper-resistant local storage that survives reboot; nonce/per-recor |
| Downgrade & algorithm-confusion at the Ed25519 migration — the public key become | 3-9mo | Never let the message choose its own verification algorithm. Pin the expected alg per-key in twin.json/the key record (a key is bound to exa |
| Telemetry poisoning -> confused-deputy echo: crypto verifies the SIGNER, never t | 3-9mo | Authenticate telemetry at the source: every outbox entry signed by the EDGE's own key; the foundry rejects unsigned/wrong-key/wrong-edge tel |
| No revocation/rotation story on an append-only, intermittent net — and the thing | 3-9mo | Design the key hierarchy NOW, before pilot: a long-lived OFFLINE ROOT key (air-gapped, quorum/multi-party, signs ONLY delegation+rotation ce |
| twin.json TOFU — who signs the twin's verify key? The PKI bottoms out in 'who ca | 3-9mo | Bind each edge's identity to a key FINGERPRINT published in an independent root-of-trust (the rapp-god canonical registry / a transparency l |
| Split-brain: an implicit distributed-consensus system with no consensus protocol | 3-9mo | State the model explicitly: eventually-consistent, single-writer-foundry, last-echo-wins per edge. Design tasks to be partition-tolerant — C |
| Edge clock is the unguarded root of every freshness/crypto assumption | 3-9mo | Use frame TICKS (the foundry's monotonic logical clock) as the PRIMARY ordering, not wall-clock — 'I am N ticks behind' is robust to drift.  |
| 'No server' hides the real SPOF: the single frame foundry and its forge key in A | 3-9mo | Treat the foundry as the trust-critical control plane and harden it: forge key in an HSM or OIDC-federated short-lived signing (not a long-l |
| Conflicting telemetry from many edges — merge/conflict-resolution policy is unde | 3-9mo | Define an explicit, deterministic conflict-resolution policy: trust/reputation-weighted merge, quorum or sensor-fusion for shared facts, and |
| Eventual-consistency lag -> edges take contradictory coordinated actions simulta | 3-9mo | Do NOT require synchronous consensus over this wire. Design guidance to be asynchronous, idempotent, and self-stabilizing (aim points and in |
| Sybil edge flood via free, unlimited GitHub accounts | 3-9mo | Decouple identity from keypair: a new edge must be vouched/co-signed by an existing quorum (web-of-trust) or anchored to a scarce, attestabl |
| First-contact trust for a brand-new edge — the bootstrap paradox where the first | 3-9mo | Enrollment ceremony: a new edge ships with an operator/manufacturer-signed birth certificate (key endorsed by an offline root or the Agent 3 |
| No abuse/eviction governance — a captured or malfunctioning edge cannot be clean | 3-9mo | Make a signed allow/deny 'swarm roster' a first-class, versioned, content-addressed artifact (like the frame chain) that edges fetch and ENF |
| GitHub is the planet's single point of failure, control, and censorship — an aut | 3-9mo | Abstract transport behind a signed, content-addressed interface so GitHub is ONE backend among several (IPFS / S3 / other static hosts) — th |
| Hostile fork of the canonical foundation — drift detection turned against itself | 3-9mo | Root canonicity cryptographically, not by URL: sign the canonical hash-set with an offline foundation root key shipped pinned with the kerne |
| An LLM as the edge's decision authority is non-deterministic and uncertifiable f | 9-18mo | For any consequential actuation, the LLM must be advisory only, BELOW a deterministic, certifiable, version-pinned safety/policy kernel that |
| Export control, dual-use classification, and autonomous-systems liability — a si | 9-18mo | Get an export-control/regulatory read BEFORE any cross-border or physical-actuation pilot: classify the crypto and the control system (ECCN/ |
| Single-vendor capture: Microsoft owns the transport (GitHub/raw), the auth (Copi | 9-18mo | Abstract all three layers behind interfaces NOW so none is load-bearing-singular: a transport interface (GitHub as one impl, plus an object  |
| Two control planes: the frame-net's controller IS GitHub, but Agent 365 must own | 9-18mo | Bank: (1) Make frames carry Entra-issued Agent identity and have the foundry's signing key be an Entra-managed identity / Agent 365-register |
| No real-time revocation on intermittent/light-delayed edges — a compromised key  | 9-18mo | Short-lived, auto-expiring echos/keys with an enforced max validity so absence-of-renewal = automatic de-authorization (revocation by expiry |
| Canonical-twin trust root is repo control: account takeover or repo deletion poi | 9-18mo | Anchor the canon to publisher signing keys (Ed25519/rapp-moment ECDSA) and a transparency log, not to repo control; multi-maintainer signing |
| Pre-blackout poison timing + no echo freshness/dead-man = guaranteed days-long p | 9-18mo | Echos carry an explicit validity horizon ('valid until tick/contact N'); past horizon the edge degrades to a conservative local-only safe mo |
| The Agent 365 on-ramp becomes a trust-laundering / shadow-IT bypass of the very  | 9-18mo | Define the trust handoff BEFORE the pitch: every signed object crossing into Agent 365 registers an Entra Agent ID, undergoes a Purview cont |
| The signature LAUNDERS adversarial guidance — verifying the signer is not verify | 9-18mo | Bank this as the boundary of crypto and start the control work now: constrain signed guidance to a TYPED, bounded action grammar (not free-f |
| Kernel-lock is a CI policy on one repo, not a runtime or cryptographic property  | 9-18mo | Runtime kernel attestation: the brainstem measures its own kernel hash and publishes it in twin.json/telemetry; foundry and peers refuse to  |

## P2 — hardening (28)

| Wrench | Horizon | Mitigation (banked) |
|---|---|---|
| Unauthenticated request amplification: one /chat triggers pip installs, model ca | 0-3mo | Auth-gate /chat (covered above); add rate limiting + concurrency caps; cache agent discovery with a watch instead of full reload-per-request |
| Canonicalization / duplicate-key JSON: the signature covers different bytes than | 0-3mo | Define ONE canonical serialization (JCS / sorted keys / no insignificant whitespace, normalized numbers + unicode) used identically by signi |
| No domain separation or recipient binding — one key signs frames, echos, telemet | 0-3mo | Bake a domain-separation tag INSIDE the signed bytes of every object: {object-type + protocol-version + chain-id + recipient-edge-id + valid |
| No global 'now': at relativistic / multi-day delay, 'latest', 'valid_until', and | 18mo+ | Stop relying on wall-clock time for security/correctness; order by CAUSALITY, not time — use logical clocks / vector clocks / a hash-DAG (pr |
| A 'planetary' nervous system on one US vendor's free tier is a single-vendor, si | 18mo+ | Bank transport abstraction: define a transport interface (read frames / write telemetry / store twin) with GitHub as one implementation, and |
| Issues are MUTABLE — 'append-only ledger' is a convention GitHub does not enforc | 3-9mo | Bank: (1) Make append-only cryptographic, not platform-trusted: every reader (and the foundry) pins and persists prev-hashes locally; a chai |
| Twin inbox poisoning: 'reach the edge through its twin' makes the inbox/ a writa | 3-9mo | Bank: (1) Strict trust separation in the reconciler: SIGNED echos are guidance; unsigned inbox messages are UNTRUSTED DATA and must never be |
| latest.json update is an unlocked lost-update/split-brain race in the foundry | 3-9mo | Bank: (1) Single-writer discipline: leader election / a workflow concurrency group so only one foundry run can publish at a time (concurrenc |
| Secrets-in-agents and no Key Vault path: developers embed credentials in plainte | 3-9mo | Provide a first-class secret-reference mechanism (Key Vault / OS keychain / env injection) so agents reference rather than embed secrets; ma |
| 'Append-only telemetry via the Issues API' isn't actually append-only or immutab | 3-9mo | Make telemetry self-verifying independent of GitHub's mutability: each entry edge-signed AND prev-hash-chained, so any edit/delete/reorder s |
| Unbounded append-only log: repo limits, forever-growing cold-start, and no check | 3-9mo | Introduce signed CHECKPOINT frames (a periodic state-root that summarizes accumulated state, like a blockchain snapshot). Cold-start = fetch |
| Heartbeat thundering herd: raw rate-limits cause correlated fleet blindness | 3-9mo | Jittered, exponentially-backed-off polling. Use conditional requests (ETag / If-None-Match) so unchanged latest.json rides the CDN cache nea |
| Foundry non-determinism blocks failover and audit, and re-creates split-brain at | 3-9mo | Make the foundry a PURE, DETERMINISTIC function of (ordered+deduped telemetry set, frame chain): fixed iteration order, no wall-clock in the |
| The always-public twin is a reconnaissance, targeting, and privacy goldmine even | 3-9mo | Minimize and compartmentalize public twin data: publish only what rendezvous strictly requires (identity + verify key + an opaque pointer);  |
| No root-of-trust ceremony or succession plan — the meta-governance gap under eve | 3-9mo | Define a documented, ceremonial root-of-trust (this ecosystem already has a CONSTITUTION culture to anchor it to): threshold-held root key ( |
| Emergent multi-agent dynamics: delayed-feedback control-loop instability, synchr | 9-18mo | Treat the swarm as a control system: add per-edge jitter/randomized cadence (no TTL-synchronized herds), damping/hysteresis on how fast an e |
| Physical edge reality: cosmic-ray bit-flips and fault-injection make crypto chec | 9-18mo | Defend the silicon: ECC memory + radiation-hardened or redundant compute on space/high-radiation edges; verify-twice / triple-redundant comp |
| The reconciling LLM is a remote, mutable, unowned brain — silent model swaps cha | 9-18mo | Pin and attest the exact model build in the signed config; refuse to actuate on an unexpected model version; prefer locally-hosted, frozen,  |
| Append-only chained frames + GitHub repo soft-limits = an inevitable wall you ca | 9-18mo | Bank a checkpoint-and-archive design from day one: periodic signed 'checkpoint' frames that summarize and allow safe pruning of pre-checkpoi |
| Per-twin PKI with no server and no CA: revocation is unsolved — you cannot push  | 9-18mo | Bank a revocation strategy suited to disconnection: short-lived keys / signed validity windows so a key auto-expires without an explicit CRL |
| Public twins (twin.json/state.json/inbox/outbox) are a fleet reconnaissance and  | 9-18mo | Minimize public twin contents to an opaque identifier + verify key + signed liveness pointer; move state/inbox/outbox behind authenticated,  |
| Anti-rollback gap: latest.json + HMAC chain can be replayed/forked to pin an edg | 9-18mo | Add monotonic, signed freshness: strictly increasing signed ticks with a max-age that flips the edge to safe-mode when exceeded; asymmetric  |
| IP/licensing contamination: community agents and mixed licenses (PolyForm-NC) in | 9-18mo | Mandatory license metadata + SPDX on every registry object; license-policy gate that blocks NC/copyleft/unknown from enterprise install; pro |
| rapp-god is detect-not-prevent and is itself attackable via alert fatigue and ba | 9-18mo | Verify against a SIGNED baseline, and alarm loudly on changes to the baseline itself (a baseline change is the highest-severity event, not a |
| raw CDN cache fragmentation = infrastructure-induced split-brain across edges | 9-18mo | Don't depend on CDN coherence for correctness: edges converge via the SIGNED chain (prev-hash + monotonic tick) and reconcile to the highest |
| Forced-staleness / eclipse: cachedGhJson + tick-without-a-clock + a wipeable tic | 9-18mo | Use a monotonic LOGICAL tick (not wall-clock) as the primary freshness primitive, persisted to tamper-resistant/append-only durable storage  |
| Transport == one GitHub repo: suspension, rename, or going private kills the pla | 9-18mo | Make the protocol transport-AGNOSTIC: frames/echos are already content-addressed and signed, so identity is the KEY, not the URL. Mirror to  |
| Economic / rate-limit DoS of the substrate as a governance-grade silencing weapo | 9-18mo | Per-edge quotas and admission control BEFORE the foundry spends a cent. Batch/debounce foundry runs (never run-per-telemetry-item); cap fan- |

## P3 — far future (1)

| Wrench | Horizon | Mitigation (banked) |
|---|---|---|
| Long-lived immutable signed objects + a quantum future = harvest-now, forge-late | 18mo+ | Bake crypto-agility into the OBJECT FORMAT, not just the roadmap: every signed object carries (sig-suite-id, key-id) so the verifier can req |

---
*Banked, not blocking. When reality throws one of these, the answer is already here.*
