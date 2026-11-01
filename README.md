# QuantumGuard

A post-quantum account for the QMS testnet: transactions authorised by a
hash-based one-time signature instead of an ECDSA private key.

**Live on QMS Testnet (chain 19480):** [`0xdF59d13E03928a95A6A9BA5c9c1E815976D64778`](https://testnet.qmsscan.io/address/0xdF59d13E03928a95A6A9BA5c9c1E815976D64778) — source verified.

## Why

Every wallet we use today is owned by a key that can be recovered from public
data if a sufficiently large quantum computer runs Shor's algorithm. QMS
already plans for this (accounts upgradeable to PQ signatures, PQ finality in
v1). QuantumGuard is a working preview of that migration, built entirely inside
the EVM that QMS v0.1 runs today.

## Why hash-based

QMS v0.1 rejects blob transactions, so the KZG point-evaluation precompile is
inactive and lattice schemes (ML-DSA / Dilithium) cannot be verified on-chain.
Hash-based signatures need only `keccak256`, and hash preimage resistance is not
broken by Shor's algorithm.

| Scheme | On-chain on QMS v0.1 | Sig size | Verify gas |
|---|---|---|---|
| ECDSA (today) | yes | 65 B | ~3k |
| ML-DSA (lattice) | **no** — needs KZG | 2.4 KB | n/a |
| WOTS w=8 (this repo) | **yes** | 1088 B | ~1.55M |
| SPHINCS+ | yes | 8–17 KB | much higher |

See [`DESIGN.md`](DESIGN.md) for the parameter set, hash chain definition and
the limitations we state openly (one-time keys, gas, key management).

## What is in the box

```
contracts/
  WOTSVerifier.sol   # WOTS (w=8) verification, keccak-only
  PQAccount.sol      # account that executes calls after WOTS authorisation
qg.py                # key generation, signing, deploy, execute (web3.py)
build_compile.py     # reproducible compile + standard-JSON for verification
verification.json    # compiler settings used by QMSScan
```

## Live transactions

| Step | Tx | Gas |
|---|---|---|
| Deploy (verified) | `e37a17f38987f71b04…` | 666,984 |
| Execute (WOTS-authorised) | see `demo/video/quantumguard-demo.webm` | 1.55M |

Account `nonce()` advances and `currentKeyHash()` changes after every execute:
the one-time key is burned and a pre-committed next key takes over.

## Demo video

`demo/video/quantumguard-demo.webm` (52 s) — recorded from a real run: the
transaction was broadcast to QMS Testnet and included on-chain during
recording. Re-record with `python demo/record.py --execute`.

## Run it…

```bash
python -m venv .venv && . .venv/bin/activate
pip install web3 eth-account py-solc-x
python build_compile.py          # compile to build/
python qg.py selftest            # sign/verify 20 random digests + tamper check
python qg.py deploy              # deploy a new PQAccount
python verify_account.py         # confirm local key == chain key
python qg.py execute --to 0x...  # authorise a call with a WOTS signature
```

Set `QG_KEY` (private key of a funded testnet account) or put it in
`deployer.key`. Get testnet QMS from `https://faucet.testnet.qms.finance`.

## Limitations

- **One-time keys.** WOTS signs one digest per key. `PQAccount` rotates keys
  after every use; reuse would allow forgery. Production systems need an XMSS
  tree or a stateless scheme (SPHINCS+).
- **Gas.** ~1.55M per authorisation, about 4% of a QMS block. Fine for a
  preview, too heavy for routine high-frequency use.
- **Not a protocol feature.** QMS v0.1 has no native PQ accounts or finality
  layer. This runs entirely in user contracts.
- **Not audited.** Testnet demonstration only.

## Roadmap (90 days)

1. **Weeks 1–4** — contracts, verification library, test suite, verified
   testnet deployment (done).
2. **Weeks 5–8** — web demo: upgrade an EOA to a PQ-authorised account, with a
   side-by-side ECDSA vs WOTS key view.
3. **Weeks 9–12** — public testnet users, docs, QMS showcase submission.

## Licence

MIT.
