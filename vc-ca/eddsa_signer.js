const { buildEddsa } = require("circomlibjs");
const crypto = require("crypto");

async function main() {
    const eddsa = await buildEddsa();
    const op = process.argv[2];

    if (op === "keygen") {
        const sk = crypto.randomBytes(32);
        const pk = eddsa.prv2pub(sk);
        console.log(JSON.stringify({
            sk:  sk.toString("hex"),
            Ax:  eddsa.F.toString(pk[0]),
            Ay:  eddsa.F.toString(pk[1])
        }));

    } else if (op === "sign") {
        const sk  = Buffer.from(process.argv[3], "hex");
        const msg = eddsa.F.e(BigInt(process.argv[4]));
        const sig = eddsa.signPoseidon(sk, msg);
        console.log(JSON.stringify({
            R8x: eddsa.F.toString(sig.R8[0]),
            R8y: eddsa.F.toString(sig.R8[1]),
            S:   sig.S.toString()
        }));

    } else {
        process.stderr.write("Usage: node eddsa_signer.js <keygen|sign> [sk_hex] [message]\n");
        process.exit(1);
    }
}

main().catch(e => { process.stderr.write(e.toString() + "\n"); process.exit(1); });
