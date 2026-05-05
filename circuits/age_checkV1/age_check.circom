pragma circom 2.0.0;

include "poseidon.circom";
include "comparators.circom";

template AgeCheck() {
    signal input val;
    signal input salt;
    signal input expectedHash;
    signal input threshold;

    component hasher = Poseidon(2);
    hasher.inputs[0] <== val;
    hasher.inputs[1] <== salt;

    hasher.out === expectedHash;

    component gte = GreaterEqThan(8);
    gte.in[0] <== val;
    gte.in[1] <== threshold;
    gte.out === 1;
}

component main {public [expectedHash, threshold]} = AgeCheck();
