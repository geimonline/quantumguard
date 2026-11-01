#!/usr/bin/env python3
"""Compile contracts to build/out.json and build/standard-input.json (solc 0.8.26, optimizer 200)."""
import json, pathlib, solcx
ROOT = pathlib.Path(__file__).parent
solcx.set_solc_version("0.8.26")
files = ["WOTSVerifier.sol", "PQAccount.sol"]
src = {f: (ROOT / "contracts" / f).read_text() for f in files}
std = {
    "language": "Solidity",
    "sources": {k: {"content": v} for k, v in src.items()},
    "settings": {
        "optimizer": {"enabled": True, "runs": 200},
        "outputSelection": {"*": {"*": ["abi", "evm.bytecode", "evm.deployedBytecode", "metadata", "methodIdentifiers"]}},
    },
}
out = solcx.compile_standard(std, allow_paths=str(ROOT / "contracts"))
(ROOT / "build").mkdir(exist_ok=True)
(ROOT / "build" / "out.json").write_text(json.dumps(out))
(ROOT / "build" / "standard-input.json").write_text(json.dumps(std))
c = out["contracts"]["PQAccount.sol"]["PQAccount"]
print(f"compiled: init {len(c['evm']['bytecode']['object'])//2} B, runtime {len(c['evm']['deployedBytecode']['object'])//2} B")
