pragma circom 2.0.0;

include "poseidon.circom";
include "eddsaposeidon.circom";
include "comparators.circom";


template AgeCheckV2() {

    // private inputs
    signal input val;
    signal input salt;
    signal input R8x;
    signal input R8y;
    signal input S;
    signal input Ax;
    signal input Ay;

    // public inputs
    signal input Ax_pub;
    signal input Ay_pub;
    signal input threshold;

    // hash the attribute value
    component hasher = Poseidon(2);
    hasher.inputs[0] <== val;
    hasher.inputs[1] <== salt;

    // verify CA signature over the hash
    component verifier = EdDSAPoseidonVerifier();
    verifier.enabled <== 1;
    verifier.Ax <== Ax;
    verifier.Ay <== Ay;
    verifier.R8x <== R8x;
    verifier.R8y <== R8y;
    verifier.S <== S;
    verifier.M <== hasher.out;

    // bind private key copy to public input so prover cant use a different key
    Ax === Ax_pub;
    Ay === Ay_pub;

    // check val >= threshold (8 bits is enough for age)
    component gte = GreaterEqThan(8);
    gte.in[0] <== val;
    gte.in[1] <== threshold;
    gte.out === 1;
}

component main {public [Ax_pub, Ay_pub, threshold]} = AgeCheckV2();
