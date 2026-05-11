pragma circom 2.0.0;

include "poseidon.circom";
include "eddsaposeidon.circom";
include "comparators.circom";


template AgeCheckV2() {

    // private
    signal input birthdate;
    signal input salt;
    signal input R8x;
    signal input R8y;
    signal input S;
    signal input Ax;
    signal input Ay;

    // public
    signal input Ax_pub;
    signal input Ay_pub;
    signal input currentDate;
    signal input minAge;

    // hash
    component hasher = Poseidon(2);
    hasher.inputs[0] <== birthdate;
    hasher.inputs[1] <== salt;

    // verify CA sig
    component verifier = EdDSAPoseidonVerifier();
    verifier.enabled <== 1;
    verifier.Ax <== Ax;
    verifier.Ay <== Ay;
    verifier.R8x <== R8x;
    verifier.R8y <== R8y;
    verifier.S <== S;
    verifier.M <== hasher.out;

    // bind private key to public input
    Ax === Ax_pub;
    Ay === Ay_pub;

    // check age >= minAge
    signal age;
    age <== currentDate - birthdate;

    component gte = GreaterEqThan(32);
    gte.in[0] <== age;
    gte.in[1] <== minAge;
    gte.out === 1;
}

component main {public [Ax_pub, Ay_pub, currentDate, minAge]} = AgeCheckV2();
