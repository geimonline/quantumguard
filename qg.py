#!/usr/bin/env python3
"""QuantumGuard — off-chain WOTS signer and QMS testnet end-to-end runner.

Implements the exact hash chain the on-chain verifier expects:

    chain_0(i) = keccak256(seed || i)
    chain_k(i) = keccak256(seed || i || chain_{k-1}(i))

with n = 32 bytes, w = 8, len_1 = 32, len_2 = 2, len = 34.

Usage:
    python qg.py keys                 # generate one WOTS key pair
    python qg.py selftest             # verify sign/verify locally (no chain)
    python qg.py deploy               # deploy PQAccount to QMS testnet
    python qg.py execute --to 0x.. --data 0x..   # send one authorised call
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
from pathlib import Path

from eth_account import Account
from web3 import Web3

ROOT = Path(__file__).parent
RPC = os.environ.get("QMS_RPC", "https://rpc.testnet.qms.finance")
CHAIN_ID = 19480

N = 32
LEN1 = 32
LEN2 = 2
LEN = LEN1 + LEN2  # 34
MAX_DIGIT = 255


# ---------------------------------------------------------------- hash chain
def keccak(data: bytes) -> bytes:
    return Web3.keccak(data)


def step(seed: bytes, index: int, prev: bytes) -> bytes:
    """One canonical chain step: keccak256(seed || index || prev)."""
    return keccak(seed + bytes([index]) + prev)


def chain_from(seed: bytes, index: int, k: int) -> bytes:
    """chain_k(i) = keccak(seed||i) advanced k times via keccak(seed||i||prev)."""
    v = keccak(seed + bytes([index]))
    for _ in range(k):
        v = step(seed, index, v)
    return v


# ------------------------------------------------------------------- key gen
def keygen(seed: bytes | None = None) -> dict:
    """Generate a WOTS key pair.

    Private key = the 34 chain starting values (one message signature reveals
    the used positions; a second signature with the same key is unsafe).
    """
    seed = seed or secrets.token_bytes(N)
    priv = [chain_from(seed, i, 0) for i in range(LEN)]
    pub = [chain_from(seed, i, MAX_DIGIT) for i in range(LEN)]
    pub_bytes = b"".join(pub)
    return {
        "seed": seed.hex(),
        "private": [p.hex() for p in priv],
        "public": pub_bytes.hex(),
        "public_hash": keccak(pub_bytes).hex(),
    }


# -------------------------------------------------------------------- digits
def digits(digest: bytes) -> list[int]:
    d = list(digest[:LEN1])
    csum = sum(MAX_DIGIT - v for v in d)
    c = csum << 3
    d.append((c >> 8) & 0xFF)
    d.append(c & 0xFF)
    return d


# ---------------------------------------------------------------------- sign
def sign(key: dict, digest: bytes) -> bytes:
    seed = bytes.fromhex(key["seed"])
    priv = [bytes.fromhex(p) for p in key["private"]]
    d = digits(digest)
    out = []
    for i in range(LEN):
        # advance the chain starting value d[i] steps
        v = priv[i]
        for _ in range(d[i]):
            v = step(seed, i, v)
        out.append(v)
    return b"".join(out)


def verify(public: bytes, seed: bytes, digest: bytes, signature: bytes) -> bool:
    d = digits(digest)
    for i in range(LEN):
        sig_elem = signature[i * N : (i + 1) * N]
        pk_elem = public[i * N : (i + 1) * N]
        v = sig_elem
        for _ in range(MAX_DIGIT - d[i]):
            v = step(seed, i, v)
        if v != pk_elem:
            return False
    return True


# ---------------------------------------------------------------------- abi
ABI = [
    {
        "type": "constructor",
        "inputs": [
            {"name": "currentHash", "type": "bytes32"},
            {"name": "currentSeed", "type": "bytes32"},
            {"name": "nextHash", "type": "bytes32"},
            {"name": "nextSeed_", "type": "bytes32"},
        ],
        "stateMutability": "nonpayable",
    },
    {
        "type": "function",
        "name": "execute",
        "inputs": [
            {"name": "target", "type": "address"},
            {"name": "value", "type": "uint256"},
            {"name": "data", "type": "bytes"},
            {"name": "n", "type": "uint256"},
            {"name": "signature", "type": "bytes"},
            {"name": "publicKey", "type": "bytes"},
            {"name": "newNextHash", "type": "bytes32"},
            {"name": "newNextSeed", "type": "bytes32"},
        ],
        "outputs": [],
        "stateMutability": "nonpayable",
    },
    {
        "type": "function",
        "name": "actionDigest",
        "inputs": [
            {"name": "target", "type": "address"},
            {"name": "value", "type": "uint256"},
            {"name": "data", "type": "bytes"},
            {"name": "n", "type": "uint256"},
        ],
        "outputs": [{"name": "", "type": "bytes32"}],
        "stateMutability": "view",
    },
    {
        "type": "function",
        "name": "nonce",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
    },
    {
        "type": "function",
        "name": "currentKeyHash",
        "inputs": [],
        "outputs": [{"name": "", "type": "bytes32"}],
        "stateMutability": "view",
    },
    {
        "type": "function",
        "name": "seed",
        "inputs": [],
        "outputs": [{"name": "", "type": "bytes32"}],
        "stateMutability": "view",
    },
    {
        "type": "function",
        "name": "locked",
        "inputs": [],
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
    },
    {"type": "receive", "stateMutability": "payable"},
]


def load_artifact() -> tuple[str, list]:
    out = json.loads((ROOT / "build" / "out.json").read_text())
    acct = out["contracts"]["PQAccount.sol"]["PQAccount"]
    return "0x" + acct["evm"]["bytecode"]["object"], acct["abi"]


def action_digest(chain_id: int, account: str, target: str, value: int, data: bytes, n: int) -> bytes:
    """Matches PQAccount.actionDigest: keccak256(abi.encode(uint256,address,address,uint256,bytes32,uint256)).

    abi.encode of these static types is a fixed 6*32 byte layout, so it is built
    explicitly instead of using solidity_keccak (which is abi.encodePacked).
    """
    def w32(x: int) -> bytes:
        return x.to_bytes(32, "big")

    def waddr(a: str) -> bytes:
        return bytes(12) + bytes.fromhex(Web3.to_checksum_address(a)[2:])

    encoded = (
        w32(chain_id)
        + waddr(account)
        + waddr(target)
        + w32(value)
        + keccak(data)
        + w32(n)
    )
    return keccak(encoded)


def w3conn(proxy: str | None = None) -> Web3:
    kw = {"timeout": 30}
    if proxy:
        kw["proxies"] = {"http": proxy, "https": proxy}
    w3 = Web3(Web3.HTTPProvider(RPC, request_kwargs=kw))
    assert w3.is_connected(), "RPC unreachable"
    assert w3.eth.chain_id == CHAIN_ID, f"wrong chain {w3.eth.chain_id}"
    return w3


def send(w3: Web3, tx: dict, key: str) -> dict:
    tx.setdefault("chainId", CHAIN_ID)
    tx.setdefault("nonce", w3.eth.get_transaction_count(tx["from"], "pending"))
    blk = w3.eth.get_block("latest")
    base = blk.get("baseFeePerGas")
    if base:
        pri = w3.to_wei(2, "gwei")
        tx.setdefault("maxPriorityFeePerGas", pri)
        tx.setdefault("maxFeePerGas", base * 2 + pri)
    if "gas" not in tx:
        tx["gas"] = w3.eth.estimate_gas(tx)
    signed = Account.sign_transaction(tx, key)
    h = w3.eth.send_raw_transaction(signed.raw_transaction)
    rcpt = w3.eth.wait_for_transaction_receipt(h, timeout=180)
    return {
        "hash": h.hex(),
        "status": rcpt.status,
        "gasUsed": rcpt.gasUsed,
        "block": rcpt.blockNumber,
        "contract": rcpt.contractAddress,
        "_rcpt": rcpt,
    }


# -------------------------------------------------------------------- cmds
def cmd_selftest(_args):
    k = keygen()
    pub = bytes.fromhex(k["public"])
    seed = bytes.fromhex(k["seed"])
    ok = True
    for _ in range(20):
        digest = keccak(secrets.token_bytes(40))
        sig = sign(k, digest)
        assert verify(pub, seed, digest, sig), "signature did not verify"
        # tamper check
        bad = bytearray(sig)
        bad[0] ^= 0x01
        assert not verify(pub, seed, digest, bytes(bad)), "tampered signature verified"
    print(f"selftest OK: 20/20 signatures verified, tampering rejected | pk {len(pub)} bytes, sig {len(sig)} bytes")
    return ok


def cmd_keys(_args):
    k = keygen()
    print(json.dumps({kk: v[:64] if isinstance(v, str) else v for kk, v in k.items()}, indent=2))
    (ROOT / "wots_key.json").write_text(json.dumps(k, indent=2))
    print("written -> wots_key.json")


def cmd_deploy(args):
    key = os.environ.get("QG_KEY") or Path(args.keyfile).read_text().strip()
    w3 = w3conn(args.proxy)
    acct = Account.from_key(key)
    bc, _ = load_artifact()
    cur = keygen()
    nxt = keygen()
    factory = w3.eth.contract(abi=ABI, bytecode=bc)
    tx = factory.constructor(
        bytes.fromhex(cur["public_hash"]),
        bytes.fromhex(cur["seed"]),
        bytes.fromhex(nxt["public_hash"]),
        bytes.fromhex(nxt["seed"]),
    ).build_transaction({
        "from": acct.address, "nonce": w3.eth.get_transaction_count(acct.address), "gas": 3_000_000,
        "chainId": CHAIN_ID,
    })
    res = send(w3, tx, key)
    addr = res["contract"]
    if not addr:
        raise SystemExit(f"deploy succeeded but no contract address (hash {res['hash']})")
    print(json.dumps({k: v for k, v in {"account": addr, **res}.items() if k != "_rcpt"}, indent=2))
    state = {
        "account": addr,
        "deployer": acct.address,
        "current": cur,
        "next": nxt,
        "deploy_hash": res["hash"],
    }
    (ROOT / "account_state.json").write_text(json.dumps(state, indent=2))
    print("state -> account_state.json")


def cmd_execute(args):
    key = os.environ.get("QG_KEY") or Path(args.keyfile).read_text().strip()
    state = json.loads((ROOT / "account_state.json").read_text())
    w3 = w3conn(args.proxy)
    acct = Account.from_key(key)
    c = w3.eth.contract(address=Web3.to_checksum_address(state["account"]), abi=ABI)
    n = c.functions.nonce().call()
    target = Web3.to_checksum_address(args.to)
    data = bytes.fromhex(args.data.replace("0x", ""))
    digest = action_digest(CHAIN_ID, state["account"], target, args.value, data, n)

    cur, nxt = state["current"], state["next"]
    sig = sign(cur, digest)
    new_next = keygen()

    tx = c.functions.execute(
        target, args.value, data, n, sig, bytes.fromhex(cur["public"]),
        bytes.fromhex(new_next["public_hash"]), bytes.fromhex(new_next["seed"]),
    ).build_transaction({
        "from": acct.address, "nonce": w3.eth.get_transaction_count(acct.address),
        "chainId": CHAIN_ID, "value": 0,
    })
    tx["gas"] = args.gas or 1_200_000
    res = send(w3, tx, key)
    if res["status"] == 1:
        # persist before anything else: the signing key is now burned on-chain
        state["current"] = nxt
        state["next"] = new_next
        (ROOT / "account_state.json").write_text(json.dumps(state, indent=2))
    print(json.dumps({k: v for k, v in {"digest": digest.hex(), "nonce_used": n, **res}.items() if k != "_rcpt"}, indent=2))
    if res["status"] != 1:
        raise SystemExit("execute reverted; account_state.json left untouched")
    print("keys rotated -> account_state.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["keys", "selftest", "deploy", "execute"])
    ap.add_argument("--keyfile", default="deployer.key")
    ap.add_argument("--proxy", default=None)
    ap.add_argument("--to", default="0x000000000000000000000000000000000000dEaD")
    ap.add_argument("--data", default="0x")
    ap.add_argument("--value", type=int, default=0)
    ap.add_argument("--gas", type=int, default=0)
    args = ap.parse_args()
    {"keys": cmd_keys, "selftest": cmd_selftest, "deploy": cmd_deploy, "execute": cmd_execute}[args.cmd](args)


if __name__ == "__main__":
    main()
