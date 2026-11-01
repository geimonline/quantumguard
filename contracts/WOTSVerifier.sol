// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

/**
 * @title WOTSVerifier
 * @notice On-chain verification of Winternitz one-time signatures (WOTS, w = 8)
 *         built only on keccak256.
 *
 * Why hash-based: QMS Testnet (v0.1) rejects type-3 blob transactions, so the
 * KZG point-evaluation precompile is inactive and lattice schemes that depend
 * on polynomial commitments cannot be verified on-chain. Hash-based signatures
 * need nothing beyond keccak256 and rest on preimage resistance, which Shor's
 * algorithm does not break.
 *
 * Canonical hash chain (must match the off-chain signer exactly):
 *
 *     chain_0(i) = keccak256(seed ‖ i)
 *     chain_k(i) = keccak256(seed ‖ i ‖ chain_{k-1}(i))   for k >= 1
 *
 * where `seed` is the public 32-byte WOTS seed, `i` is a single byte chain
 * index, and every intermediate value is 32 bytes. Prefixing every step with
 * `seed` gives domain separation between chains and prevents the
 * "collide an intermediate value with a first step" attack.
 *
 * Parameter set: n = 32, w = 8, len_1 = 32, len_2 = 2, len = 34.
 * Public key = 34 chain endpoints (1088 bytes). Signature = 34 chain values.
 *
 * One-time use: a WOTS key pair signs at most one digest. PQAccount rotates
 * keys after each use; nothing here can enforce that on its own.
 */
library WOTSVerifier {
    uint256 internal constant N = 32;
    uint256 internal constant LEN1 = 32;
    uint256 internal constant LEN2 = 2;
    uint256 internal constant LEN = 34;
    uint256 internal constant MAX_DIGIT = 255;

    error BadLength();

    /// @notice Serialized length of a public key or signature, in bytes.
    function packedLength() internal pure returns (uint256) {
        return LEN * N;
    }

    /**
     * @notice Decompose a digest into 34 base-256 digits plus a checksum.
     * @dev The checksum prevents an attacker from raising a digit (fewer hash
     *      steps are needed to reach the public key endpoint).
     */
    function digits(bytes32 digest) internal pure returns (uint8[LEN] memory d) {
        uint256 csum;
        for (uint256 i = 0; i < LEN1; i++) {
            uint8 v = uint8(digest[i]);
            d[i] = v;
            csum += MAX_DIGIT - v;
        }
        uint256 c = csum << 3;
        d[LEN1] = uint8(c >> 8);
        d[LEN1 + 1] = uint8(c);
    }

    /// @notice One step of the canonical hash chain for element `index`.
    function step(bytes32 seed, uint8 index, bytes32 prev) internal pure returns (bytes32) {
        return keccak256(abi.encodePacked(seed, index, prev));
    }

    /// @notice Compute chain_k(index), starting from the secret base value.
    function chainFrom(bytes32 seed, uint8 index, uint256 k) internal pure returns (bytes32 v) {
        v = keccak256(abi.encodePacked(seed, index));
        for (uint256 s = 0; s < k; s++) {
            v = step(seed, index, v);
        }
    }

    /**
     * @notice Verify a WOTS signature over `digest`.
     * @param digest    32-byte digest produced by the calling account
     * @param signature 34 chained values, 32 bytes each
     * @param publicKey 34 chain endpoints, 32 bytes each
     * @param seed      public WOTS seed (32 bytes) committed with the key
     */
    function verify(bytes32 digest, bytes calldata signature, bytes calldata publicKey, bytes32 seed)
        internal
        pure
        returns (bool)
    {
        if (signature.length != LEN * N || publicKey.length != LEN * N) revert BadLength();

        uint8[LEN] memory d = digits(digest);

        for (uint256 i = 0; i < LEN; i++) {
            bytes32 sigElem;
            bytes32 pkElem;
            assembly {
                sigElem := calldataload(add(signature.offset, mul(i, N)))
                pkElem := calldataload(add(publicKey.offset, mul(i, N)))
            }
            bytes32 v = sigElem;
            uint256 remaining = MAX_DIGIT - d[i];
            for (uint256 s = 0; s < remaining; s++) {
                v = step(seed, uint8(i), v);
            }
            if (v != pkElem) return false;
        }
        return true;
    }
}
