# Demo video

`video/quantumguard-demo.webm` — 52 s, 1600×900, VP8/WebM.
Recorded from a real run: the transaction in the video was broadcast to
QMS Testnet and included on-chain while the browser was recording.

## What the video shows

| Time | Slide |
|------|-------|
| 0:00 | Title — a post-quantum account |
| 0:05 | The problem: ECDSA keys are recoverable by Shor's algorithm |
| 0:12 | Why hash-based: the KZG precompile is inactive on QMS v0.1, so lattice schemes cannot be verified |
| 0:19 | The live contract, deployed and source-verified, with real nonce and key hash |
| 0:24 | Authorising a transaction: build digest → sign with WOTS → on-chain verify → rotate key (live tx hash and block inclusion appear) |
| 0:38 | Key rotation proof: key hash before vs after, nonce advanced |
| 0:47 | 90-day plan |

## Re-record

```bash
python demo/record.py             # rehearse, no transaction (labels the run as cached)
python demo/record.py --execute   # real transaction on QMS Testnet
```

Output goes to `demo/video/`. Requires `deployer.key` (or `QG_KEY`) for the
funded testnet account.
