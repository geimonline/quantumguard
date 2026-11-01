# QMS Builder Program — application draft (Cohort 1)

Copy-paste each block into the matching form field. Text is English.

---

## Step 1 — You & your team

| Field | Value |
|---|---|
| Name or nickname | _(your name)_ |
| Email | _(your email)_ |
| Discord handle | _(your handle)_ |
| X handle | _(project or personal X handle)_ |
| Founder 1 — name | _(your name)_ |
| Founder 1 — role | Founder / Engineer |
| Founder 1 — link | `https://github.com/<your-handle>/quantumguard` |
| Are the founders publicly identifiable? | **Partially** |

**Relevant experience and past projects (max 80 words):**

> I build and operate EVM infrastructure end to end: deployment pipelines,
> automated verification, and multi-wallet testnet operations at scale
> (50+ verified contracts, 900+ transactions, zero failed runs). I have written
> signing and verification libraries from scratch and run them against live
> networks. QuantumGuard is my first post-quantum implementation: a hash-based
> signature scheme verified on-chain and shipped to QMS Testnet, with source
> verification and reproducible builds.
> **Links:** `github.com/geimonline/quantumguard`

---

## Step 2 — Your project

**Project name:** QuantumGuard

**One-line description:**

> A working post-quantum account on QMS Testnet — transactions authorised by
> hash-based signatures instead of ECDSA.

**What it does (short):**

> QuantumGuard demonstrates the migration QMS describes for v1: an account whose
> ownership is proved with a post-quantum signature rather than an ECDSA private
> key. It is a live contract on QMS Testnet, verified on QMSScan, where each
> transaction consumes a one-time hash-based key and rotates to the next one.

**Why QMS (this is the field they weight):**

> QMS is the only L1 we found that treats post-quantum as a protocol-level
> default rather than an add-on. But QMS v0.1 has no PQ execution yet, and that
> gap is exactly where builders can help: QuantumGuard validates a concrete
> account-migration path today, inside the EVM that QMS already runs. It gives
> the core team a working reference implementation, and the community an
> understandable answer to "what does a PQ account actually look like?" Before
> shipping we verified the constraints that make this non-obvious: QMS v0.1
> rejects blob transactions, so the KZG precompile is inactive and lattice
> schemes cannot be verified on-chain — hash-based signatures are the only
> post-quantum family that works here. We measured real gas (~1.55M per
> authorisation) rather than guessing.

**Current status:** Live on testnet — deployed, source verified, multiple
authorised executions, key rotation confirmed on-chain.

**Links:**
- Repo: `github.com/geimonline/quantumguard`
- Contract: `https://testnet.qmsscan.io/address/0x2504F2793886d959e5671e4027d290b736df8306`
- Demo video: _(record a 60–90s screen capture: deploy, sign, execute, key rotates)_

**Category:** Infrastructure / developer tooling / account security

---

## Step 3 — Traction & funding

**What we have shipped:**

> 3 live transactions on QMS Testnet (1 deploy + 2 authorised executions), source
> verified on QMSScan, reproducible build script, signature library with a
> 20-iteration self-test including tamper rejection.

**Users:** 0 external users so far — this is a pre-launch infrastructure demo.
**Funding:** none.
**Team size:** 1.

**Honest framing:** we would rather show a small number of real, verifiable
transactions than projected user counts. The metric we intend to report in 90
days is *accounts upgraded*, not followers.

---

## Step 4 — Support & submit

**What support we are asking for:**

1. **Technical review** — is a hash-based account the right reference for the v1
   PQ migration, or should we align with a specific scheme the core team plans
   to support?
2. **Access to PQ feature specs** — anything that lets the demo match the real
   v1 account model instead of an approximation.
3. **Showcase** — if the demo is useful, we would like it listed alongside the
   docs as a community example.

**Anything else we should know:**

> We are deliberately not claiming to be a PQ protocol implementation. QMS v0.1
> has no finality layer and no native PQ accounts; QuantumGuard runs entirely in
> user contracts. The value is in the migration pattern and the measured
> constraints, both of which we can hand to the core team immediately.

---

## 90-day plan (paste into Step 3 or Step 4 if there is a free-text box)

**Weeks 1–4 — done before applying**
- WOTS (w=8) verifier in Solidity, keccak-only
- `PQAccount` with one-time key rotation and replay protection
- Deploy + verify on QMS Testnet, two authorised executions confirmed

**Weeks 5–8 — make it usable**
- Web demo: connect wallet → show current ECDSA key → upgrade to a PQ-authorised
  account → sign an action with a WOTS key in the browser
- Side-by-side key/security comparison page (ECDSA vs WOTS vs ML-DSA vs SPHINCS+)
- Reduce verification gas (batch hash steps, calldata packing)

**Weeks 9–12 — make it real**
- Target: 100 testnet accounts upgraded, each performing at least one PQ-signed
  action
- Publish the gas and failure numbers openly
- Submit as a QMS docs example and "Built on QMS" showcase entry

**Success looks like:** a developer can explain, using our demo, why QMS's
post-quantum direction matters and what upgrading an account actually costs.

---

## Pre-submit checklist

- [ ] GitHub repo public, README renders, LICENSE present
- [ ] Contract verified on QMSScan (done)
- [ ] 60–90s demo video recorded
- [ ] X post announcing the demo, linking repo + contract
- [ ] Personal X handle active and consistent with the repo
- [ ] Email and Discord handle double-checked
