const { buildPoseidon } = require("circomlibjs");

async function hash() {
    const poseidon = await buildPoseidon();
    const val = process.argv[2];
    const salt = process.argv[3];

    const hash = poseidon([val, salt]);
    // toObject converts the field element to a BigInt
    console.log(poseidon.F.toObject(hash).toString());
}

hash();
