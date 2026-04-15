pragma circom 2.0.0;

include "poseidon.circom";
include "eddsaposeidon.circom";
include "comparators.circom";


template AgeCheckV2() {

    // --- Private inputs ---
    signal input val;        // raw attribute integer (e.g. 23 for age)
    signal input salt;       // per-attribute random salt issued by CA
    signal input R8x;        // EdDSA signature component R8 x-coordinate
    signal input R8y;        // EdDSA signature component R8 y-coordinate
    signal input S;          // EdDSA signature scalar S
    signal input Ax;         // CA BabyJubJub public key x (private copy for sig check)
    signal input Ay;         // CA BabyJubJub public key y (private copy for sig check)

    // --- Public inputs ---
    signal input Ax_pub;     // CA BabyJubJub public key x (verifier pins this)
    signal input Ay_pub;     // CA BabyJubJub public key y (verifier pins this)
    signal input threshold;  // minimum value required by the verifier (e.g. 18)

    // Step 1: recompute Poseidon(val, salt) — this is the message the CA signed
    component hasher = Poseidon(2);
    hasher.inputs[0] <== val;
    hasher.inputs[1] <== salt;

    // Step 2: verify the EdDSA signature over Poseidon(val, salt)
    component verifier = EdDSAPoseidonVerifier();
    verifier.enabled <== 1;
    verifier.Ax      <== Ax;
    verifier.Ay      <== Ay;
    verifier.R8x     <== R8x;
    verifier.R8y     <== R8y;
    verifier.S       <== S;
    verifier.M       <== hasher.out;

    // Step 3: bind the private key copy to the verifier-supplied public inputs
    // This prevents the prover from using any key other than the CA's published key
    Ax === Ax_pub;
    Ay === Ay_pub;

    // Step 4: range check — val >= threshold
    // GreaterEqThan(n) supports values in [0, 2^n - 1]
    // 8 bits covers 0–255, sufficient for age
    component gte = GreaterEqThan(8);
    gte.in[0] <== val;
    gte.in[1] <== threshold;
    gte.out   === 1;
}

component main {public [Ax_pub, Ay_pub, threshold]} = AgeCheckV2();
