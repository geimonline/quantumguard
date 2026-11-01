# QuantumGuard — WOTS+ design notes

## Scope

QuantumGuard demonstrates a **post-quantum account** on QMS Testnet: an account
whose transactions are authorised by a hash-based one-time signature (WOTS,
Winternitz parameter w = 8) instead of ECDSA.

## Why hash-based, not lattice

QMS Testnet (v0.1) does not accept type-3 blob transactions, and the KZG point
evaluation precompile is inactive. Lattice schemes such as ML-DSA (Dilithium)
rely on KZG-style polynomial commitments for efficient verification and cannot
be verified on-chain in this environment. Hash-based signatures need only
keccak256, which is available, cheap, and believed to be quantum-resistant
(Shor's algorithm breaks factoring and discrete log, not hash preimages).

## Parameters

| Parameter | Value |
|-----------|-------|
| Hash | keccak256 |
| n (element size) | 32 bytes |
| w (Winternitz) | 8 |
| len_1 | 32 |
| len_2 (checksum digits) | 2 |
| len = len_1 + len_2 | 34 |
| Public key | 1088 bytes |
| Signature | 1088 bytes |
| Security (pre-quantum / Grover) | ~128 bit hash → ~85 bit collision, preimage still 128 bit |

## One-time property

WOTS is a **one-time** signature. Signing two different digests with the same
key leaks chain positions and enables forgery. QuantumGuard therefore rotates
to a fresh key pair after every successful verification:

1. `authorize()` verifies the signature and immediately stores the *next*
   public key hash, invalidating the used one.
2. Used keys are recorded in a mapping; a replayed signature reverts.

This is the same trade-off real hash-based schemes make; SPHINCS+ solves it
with a hypertree at the cost of much larger signatures (~8–17 KB) and higher
verification gas.

## Gas

| Operation | Approx gas |
|-----------|-----------|
| WOTS verify (worst case, 34 × 128 avg keccak) | ~180k–320k |
| Account authorisation (verify + nonce + rotate) | ~220k–380k |

QMS block gas limit is 36M, so verification costs well under 1% of a block.

## Limitations (stated honestly)

- **One-time keys.** Not a drop-in replacement for a reusable ECDSA key.
- **No PQ finality layer.** QMS Testnet v0.1 has no finality layer and no
  native PQ account support; QuantumGuard runs entirely inside the EVM and is
  a migration *preview*, not a protocol feature.
- **Key management is the hard part.** A production system needs a Merkle tree
  of many WOTS keys (as in XMSS) or a stateless scheme (SPHINCS+).
- **Signature size.** 1088 bytes per signature versus 65 bytes for ECDSA.

## Roadmap

Phase 1 (weeks 1–4): contracts, verification library, test suite, testnet
deployment with source verification.
Phase 2 (weeks 5–8): web demo that upgrades an EOA to a PQ-authorised account,
including a side-by-side "ECDSA vs WOTS" key display.
Phase 3 (weeks 9–12): public testnet users, documentation, showcase submission.
