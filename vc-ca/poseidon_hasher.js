// poseidon_hasher.js
const { buildPoseidon } = require("circomlibjs");

async function hash() {
    const poseidon = await buildPoseidon();
    const val = process.argv[2];
    const salt = process.argv[3];

    // Calculate hash
    const hash = poseidon([val, salt]);

    // Poseidon returns a Uint8Array, convert to BigInt string
    console.log(poseidon.F.toObject(hash).toString());
}

hash();