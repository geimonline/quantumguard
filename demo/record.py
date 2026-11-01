#!/usr/bin/env python3
"""Record the QuantumGuard demo video.

Drives demo/index.html in a real Chromium viewport while executing a live
WOTS-authorised transaction on QMS Testnet, and captures the whole run to
demo/quantumguard-demo.webm.

    python demo/record.py [--execute]

--execute   send a real transaction (needs QG_KEY or deployer.key); without it
            the recording reuses the last known state and labels it as cached.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import qg  # noqa: E402

DEMO = Path(__file__).parent / "index.html"
OUT_DIR = Path(__file__).parent / "video"


def short(h: str, n: int = 20) -> str:
    h = h.replace("0x", "")
    return f"0x{h[:n]}…"


def read_state() -> dict:
    acct = json.loads((ROOT / "account_state.json").read_text())
    w3 = qg.w3conn()
    c = w3.eth.contract(address=qg.Web3.to_checksum_address(acct["account"]), abi=qg.ABI)
    acct["_nonce"] = c.functions.nonce().call()
    acct["_keyhash"] = c.functions.currentKeyHash().call().hex()
    acct["_locked"] = c.functions.locked().call()
    return acct


def assert_state_synced(state: dict) -> None:
    """Fail fast when the local key does not match the chain.

    A local/chain mismatch means a previous run broadcast a transaction whose
    result was never written back (the rotated key is then unrecoverable), so
    the account must be redeployed before recording again.
    """
    on_chain = state["_keyhash"].replace("0x", "")
    current = state["current"]["public_hash"].replace("0x", "")
    if on_chain != current:
        raise SystemExit(
            "account_state.json is out of sync with the chain:\n"
            f"  chain currentKeyHash : 0x{on_chain}\n"
            f"  local current key    : 0x{current}\n"
            "The rotated key from the last run was not persisted. Redeploy with\n"
            "  rm account_state.json && python qg.py deploy\n"
            "and verify the new address before recording."
        )


def run(execute: bool):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    state = read_state()
    if execute:
        assert_state_synced(state)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--hide-scrollbars"])
        ctx = browser.new_context(
            viewport={"width": 1600, "height": 900},
            device_scale_factor=1.5,
            record_video_dir=str(OUT_DIR),
            record_video_size={"width": 1600, "height": 900},
        )
        page = ctx.new_page()
        page.goto(DEMO.as_uri())
        page.wait_for_timeout(1200)
        hold = 3400

        # 1 — title
        page.wait_for_timeout(hold)

        # 2 — problem
        page.evaluate("window.slide(2)")
        page.wait_for_timeout(hold)

        # 3 — design constraint
        page.evaluate("window.slide(3)")
        page.wait_for_timeout(hold + 800)

        # 4 — live contract, fill real values
        page.evaluate("window.slide(4)")
        page.evaluate(
            """([n, k]) => {
                document.getElementById('nonce').textContent = n;
                document.getElementById('keyhash').textContent = k;
            }""",
            [state["_nonce"], "0x" + state["_keyhash"]],
        )
        page.wait_for_timeout(hold)

        # 5 — execute flow
        page.evaluate("window.slide(5)")
        keyhash_before = "0x" + state["_keyhash"]

        def mark(step: str, done: bool = False):
            page.evaluate(
                """([id, cls]) => {
                    const el = document.getElementById(id);
                    el.classList.add(cls);
                }""",
                [step, "done" if done else "active"],
            )

        mark("f1")
        page.wait_for_timeout(900)
        mark("f1", True)
        mark("f2")
        page.wait_for_timeout(1100)
        mark("f2", True)

        if execute:
            key = os.environ.get("QG_KEY") or (ROOT / "deployer.key").read_text().strip()
            w3 = qg.w3conn()
            c = w3.eth.contract(
                address=qg.Web3.to_checksum_address(state["account"]), abi=qg.ABI
            )
            target = qg.Web3.to_checksum_address("0x000000000000000000000000000000000000dEaD")
            n = c.functions.nonce().call()
            digest = qg.action_digest(qg.CHAIN_ID, state["account"], target, 0, b"", n)
            sig = qg.sign(state["current"], digest)
            nxt = qg.keygen()
            tx = c.functions.execute(
                target, 0, b"", n, sig,
                bytes.fromhex(state["current"]["public"]),
                bytes.fromhex(nxt["public_hash"]),
                bytes.fromhex(nxt["seed"]),
            ).build_transaction({
                "from": state["deployer"],
                "nonce": w3.eth.get_transaction_count(state["deployer"]),
                "chainId": qg.CHAIN_ID,
                "gas": 2_200_000,
            })

            # Broadcast, but keep rendering while the receipt is pending so the
            # recording shows progress instead of a frozen frame.
            from eth_account import Account as _Acct
            tx["maxPriorityFeePerGas"] = w3.to_wei(2, "gwei")
            base = w3.eth.get_block("latest").get("baseFeePerGas") or 0
            tx["maxFeePerGas"] = base * 2 + w3.to_wei(2, "gwei")
            signed = _Acct.sign_transaction(tx, key)
            txh = w3.eth.send_raw_transaction(signed.raw_transaction)
            page.evaluate(
                "([h]) => { document.getElementById('tx').textContent = h; }",
                [short(txh.hex(), 24)],
            )

            seen = 0
            deadline = time.time() + 150
            rcpt = None
            while time.time() < deadline:
                try:
                    rcpt = w3.eth.get_transaction_receipt(txh)
                except Exception:
                    rcpt = None
                if rcpt:
                    break
                dots = "." * (seen % 4)
                page.evaluate(
                    "(d) => document.getElementById('exec-note').textContent = d",
                    f"waiting for inclusion{dots}"
                )
                seen += 1
                page.wait_for_timeout(700)

            gas = rcpt.gasUsed if rcpt else 0
            page.evaluate(
                "([g]) => { document.getElementById('gas').textContent = g.toLocaleString('en-US'); }",
                [gas],
            )
            if rcpt and rcpt.status == 1:
                # Persist the rotation immediately: the key that just signed is
                # burned on-chain, so losing this state makes the account
                # unusable (the pre-committed next key cannot be recovered).
                state["current"] = nxt
                state["next"] = qg.keygen()
                state["_nonce"] = n + 1
                state["_keyhash"] = nxt["public_hash"]
                (ROOT / "account_state.json").write_text(json.dumps(state, indent=2))
                page.evaluate(
                    "() => document.getElementById('exec-note').textContent ="
                    " 'Status 1 — verified on-chain, key rotated.'"
                )
            else:
                page.evaluate(
                    "() => document.getElementById('exec-note').textContent = 'reverted — see log'"
                )
        else:
            page.evaluate(
                "() => { document.getElementById('tx').textContent = 'cached run';"
                " document.getElementById('gas').textContent = '1,553,485'; }"
            )

        mark("f3")
        page.wait_for_timeout(1100)
        mark("f3", True)
        mark("f4")
        page.wait_for_timeout(1200)
        mark("f4", True)
        page.wait_for_timeout(2200)

        # 6 — rotation proof
        after = read_state()
        page.evaluate("window.slide(6)")
        page.evaluate(
            """([b, a]) => {
                document.getElementById('kb').textContent = b;
                document.getElementById('ka').textContent = a;
            }""",
            [keyhash_before, "0x" + after["_keyhash"]],
        )
        page.wait_for_timeout(hold + 600)

        # 7 — roadmap
        page.evaluate("window.slide(7)")
        page.wait_for_timeout(hold + 1200)

        page.evaluate("window.slide(1)")
        page.wait_for_timeout(1400)

        video = page.video
        ctx.close()
        path = video.path() if video else None
        browser.close()

    if not path:
        print("no video produced")
        return
    src = Path(path)
    final = OUT_DIR / "quantumguard-demo.webm"
    if final.exists():
        final.unlink()
    src.rename(final)
    print(f"video -> {final} ({final.stat().st_size/1024/1024:.1f} MB)")
    print(f"nonce {state['_nonce']} -> {after['_nonce']}")
    print(f"key   {keyhash_before[:18]}… -> 0x{after['_keyhash'][:16]}…")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true", help="send a real testnet transaction")
    run(ap.parse_args().execute)
