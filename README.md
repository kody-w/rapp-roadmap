# 🗺️ The RAPP Roadmap

**One brainstem on a laptop → a planetary swarm of governed Leviathans enhancing every Microsoft Agent 365 workflow — while the sacred single-file kernel never changes.**

This is the roadmap for the [RAPP](https://github.com/kody-w) (Rapid Agent Prototyping Platform) ecosystem to fulfill its goals over its lifespan, ending in a fully-productized version we can bring to the **Microsoft Agent 365** team as a new *medium* — not a competitor.

> Full roadmap: **[ROADMAP.md](ROADMAP.md)** · machine-readable: [`roadmap.json`](roadmap.json) · route any situation: [rapp-spine](https://github.com/kody-w/rapp-spine)

## The new medium

Capability itself, made into a **portable, signed, content-addressed object** — the *cartridge* and the *egg* — that rides one wire (`POST /chat`, or a signed append-only event), needs **no API keys, no procurement, no engine changes** to run. What HTML did for documents, the cartridge/egg does for agent capability. Composed, these objects form a **Leviathan: a fleet of agent-beings driven as one mind** (0.2s heterogeneous fan-out, no shared-token throttle, alive even when a node's own LLM is dead). The unit is capability-as-an-object; the organism is the swarm; the whole thing is an **enhancement layer Agent 365 governs**.

## Why Agent 365 should co-own this on-ramp

- **The gap.** Agent 365 wins the *control plane* — Entra Agent ID, Purview, Defender, registry, observability. But a control plane can only govern a population it does not itself create, and it launches against a **demand/supply cold-start gap**: millions of Copilot seats, no friction-free way to turn one into a *fleet of governed agents*.
- **The enhancement.** RAPP is the **bottom-up on-ramp** that manufactures that population: a Copilot seat becomes a running agent in a minute, a fleet in an afternoon — then *promotes intact* into Agent 365's plane (Entra identity, Purview governance, Copilot Studio).
- **Enhance, never replace.** Not a competing builder, not a competing plane, not a Copilot replacement. RAPP feeds Agent 365 the governed agents it needs to govern.
- **The ask.** Co-own the on-ramp: (1) recognize the **cartridge/egg** as a first-class content-addressed format in the Agent 365 registry; (2) ship an **official connector** so promoted RAPP agents auto-receive Entra Agent ID + Purview/Defender; (3) **co-author the fleet-wire auth standard**.

## The arc

| Phase | Horizon | Theme |
|---|---|---|
| **0 · Lock the kernel, light the funnel** | now | make "kernel sacred" a CI invariant; measure the free first-run; pin the Agent-365 positioning |
| **1 · Close the RCE, make the fleet sellable** | 0–3mo | authenticate the fleet wire (signed, default-deny, audited) — the gating blocker |
| **2 · Distribution + a legible fleet** | 3–9mo | the egg as unit of distribution; signed registry; MCP as the default IDE on-ramp; observable fleets |
| **3 · Land in the plane** | 9–18mo | one-click governed graduation into Agent 365 (Entra/Purview); co-sell |
| **4 · The planetary swarm, productized** | 18mo+ | a fleet of beings driven as one mind, across orgs — the new medium delivered |

## The guarantee that makes it safe

The **kernel never changes.** Every capability — including the swarm, the auth, the registry — ships as an **agent/cartridge/spine-profile on the existing wire**, never an engine edit. A passing CI invariant proves it. (Full guarantees in [ROADMAP.md](ROADMAP.md#the-kernel-stays-sacred--guarantees).)

## The honest blocker, named first

Today the Leviathan fleet wire (`POST /api/agent/<name>`) is **unauthenticated** — LAN-only, fleet-wide RCE. **Phase 1 closes it** (signed bearer + per-agent default-deny allowlist + mTLS/Entra path), entirely as a cartridge + spine profile, zero kernel edits. No enterprise pilot ships before that gate.

---

*The hero use cases are the guiding lights — the Leviathan controller, the Foundry, the Hatchery, the MCP on-ramp, CopilotCLI delegation, portable eggs, doc2cs, the Flight Recorder. Each one is a today, and a productized tomorrow. See [ROADMAP.md](ROADMAP.md#hero-use-cases--the-guiding-lights).*
