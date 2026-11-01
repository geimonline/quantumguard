#!/usr/bin/env python3
"""Check that account_state.json matches the chain before spending gas.

Exits non-zero when the local key no longer controls the deployed account,
which happens if a rotation was never persisted. In that case the account is
unrecoverable by design (one-time keys) and must be redeployed.
"""
import json
import sys
from pathlib import Path

import qg

ROOT = Path(__file__).parent


def main() -> int:
    if not (ROOT / "account_state.json").exists():
        print("no account_state.json — run: python qg.py deploy")
        return 2
    st = json.loads((ROOT / "account_state.json").read_text())
    w3 = qg.w3conn()
    c = w3.eth.contract(address=qg.Web3.to_checksum_address(st["account"]), abi=qg.ABI)
    on_chain = c.functions.currentKeyHash().call().hex().replace("0x", "")
    local = st["current"]["public_hash"].replace("0x", "")
    nonce = c.functions.nonce().call()
    ok = on_chain == local
    print(f"account : {st['account']}")
    print(f"nonce   : {nonce}")
    print(f"locked  : {c.functions.locked().call()}")
    print(f"chain   : 0x{on_chain}")
    print(f"local   : 0x{local}")
    print("status  :", "OK" if ok else "OUT OF SYNC — redeploy the account")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
