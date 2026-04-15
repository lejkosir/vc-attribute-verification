pragma circom 2.0.0;

include "poseidon.circom";

// Proves knowledge of (val, salt) such that Poseidon(val, salt) == expectedHash.
// The verifier pins expectedHash to the CA-signed value, so the prover cannot
// substitute a hash from a different credential.
template AgeCheck() {
    // Private inputs
    signal input val;           // raw attribute integer (e.g. 23 for age)
    signal input salt;          // per-attribute random salt issued by CA

    // Public input — verifier checks this matches the CA-signed hash
    signal input expectedHash;

    component hasher = Poseidon(2);
    hasher.inputs[0] <== val;
    hasher.inputs[1] <== salt;

    hasher.out === expectedHash;
}

component main {public [expectedHash]} = AgeCheck();
