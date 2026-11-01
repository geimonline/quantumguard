// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

import {WOTSVerifier} from "./WOTSVerifier.sol";

/**
 * @title PQAccount
 * @notice A post-quantum authorised account for QMS Testnet.
 *
 * Control of the account follows a hash-based (WOTS) one-time key instead of
 * an ECDSA private key. Because WOTS keys are single-use, the contract stores
 * the hash of the *current* public key and rotates to a pre-committed next key
 * on every successful action.
 *
 * Key rotation model:
 *   - owner registers `pkHash(current)` and `pkHash(next)` at deployment.
 *   - to act, the owner submits (signature over the action, current pk).
 *   - on success the contract promotes `next` to `current` and requires the
 *     owner to commit a fresh `next` in the same call (or the account locks).
 *
 * This is a preview of what QMS describes for v1 ("accounts can be upgraded to
 * PQ signatures"); it runs entirely inside the EVM of v0.1.
 */
contract PQAccount {
    using WOTSVerifier for bytes32;

    /// @notice Address allowed to deploy/upgrade recovery keys (usually the deployer).
    /// @dev Stored in storage (not `immutable`) so deployed bytecode is identical
    ///      across deployments and can be verified against the shared source.
    address public deployer;

    bytes32 public currentKeyHash;
    bytes32 public nextKeyHash;
    /// @notice Public WOTS seed for the *current* key (committed with its hash).
    bytes32 public seed;
    uint256 public nonce;
    bool public locked;

    event ActionExecuted(address indexed target, uint256 value, bytes data, uint256 nonce);
    event KeyRotated(bytes32 newCurrentHash, bytes32 newNextHash, bytes32 newNextSeed);

    /// @dev Seed committed alongside the *next* key hash, promoted on rotation.
    bytes32 public nextSeed;

    error NotDeployer();
    error AccountLocked();
    error BadSignature();
    error BadNonce();
    error TargetReverted();
    error NextKeyNotSet();

    constructor(bytes32 currentHash, bytes32 currentSeed, bytes32 nextHash, bytes32 nextSeed_) {
        deployer = msg.sender;
        currentKeyHash = currentHash;
        seed = currentSeed;
        nextKeyHash = nextHash;
        nextSeed = nextSeed_;
    }

    /**
     * @notice Execute a call authorised by a WOTS signature.
     * @param target     contract or EOA to call
     * @param value      native QMS to forward
     * @param data       calldata
     * @param n          expected nonce (replay protection)
     * @param signature  1088-byte WOTS signature over the action digest
     * @param publicKey  1088-byte WOTS public key matching currentKeyHash
     * @param newNextHash hash of the public key to use for the *next* action
     * @param newNextSeed seed committed with newNextHash
     */
    function execute(
        address target,
        uint256 value,
        bytes calldata data,
        uint256 n,
        bytes calldata signature,
        bytes calldata publicKey,
        bytes32 newNextHash,
        bytes32 newNextSeed
    ) external {
        if (locked) revert AccountLocked();
        if (n != nonce) revert BadNonce();
        if (newNextHash == bytes32(0)) revert NextKeyNotSet();
        if (keccak256(publicKey) != currentKeyHash) revert BadSignature();

        bytes32 digest = actionDigest(target, value, data, n);
        if (!WOTSVerifier.verify(digest, signature, publicKey, seed)) revert BadSignature();

        // One-time key is now burned: rotate before the call so a reentrant
        // target cannot replay the same signature.
        currentKeyHash = nextKeyHash;
        seed = nextSeed;
        nextKeyHash = newNextHash;
        nextSeed = newNextSeed;
        nonce = n + 1;

        emit KeyRotated(currentKeyHash, nextKeyHash, nextSeed);

        (bool ok,) = target.call{value: value}(data);
        if (!ok) revert TargetReverted();

        emit ActionExecuted(target, value, data, n);
    }

    /**
     * @notice Canonical digest signed by the WOTS key.
     * @dev Domain-separated by chain id and this account's address.
     */
    function actionDigest(address target, uint256 value, bytes calldata data, uint256 n)
        public
        view
        returns (bytes32)
    {
        return keccak256(
            abi.encode(
                block.chainid,
                address(this),
                target,
                value,
                keccak256(data),
                n
            )
        );
    }

    /// @notice Deployer can freeze the account (e.g. if a one-time key leaked).
    function lock() external {
        if (msg.sender != deployer) revert NotDeployer();
        locked = true;
    }

    receive() external payable {}
}
