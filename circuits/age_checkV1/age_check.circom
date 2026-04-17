pragma circom 2.0.0;

include "poseidon.circom";

template AgeCheck() {
    signal input val;
    signal input salt;
    signal input expectedHash;

    component hasher = Poseidon(2);
    hasher.inputs[0] <== val;
    hasher.inputs[1] <== salt;

    hasher.out === expectedHash;
}

component main {public [expectedHash]} = AgeCheck();
