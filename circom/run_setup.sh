#!/bin/sh
set -e

RANDOM_HEX=$(node -e "process.stdout.write(require('crypto').randomBytes(32).toString('hex'))")
RANDOM_HEX2=$(node -e "process.stdout.write(require('crypto').randomBytes(32).toString('hex'))")

echo "=== Diagnostic: circomlib circuits ==="
ls /app/node_modules/circomlib/circuits/ 2>/dev/null || echo "ERROR: circomlib circuits dir not found"
echo "--- EdDSA templates ---"
grep "^template" /app/node_modules/circomlib/circuits/eddsa.circom 2>/dev/null || echo "ERROR: eddsa.circom not found"

echo "=== Step 1: Compile circuit ==="
circom /app/age_check_v2.circom \
    --r1cs --wasm --sym \
    -l /app/node_modules/circomlib/circuits \
    -o /output

echo "=== Step 2: Powers of Tau (phase 1) ==="
snarkjs powersoftau new bn128 13 /output/pot13_0.ptau -v
snarkjs powersoftau contribute /output/pot13_0.ptau /output/pot13_1.ptau \
    --name="setup" -e="$RANDOM_HEX"
snarkjs powersoftau prepare phase2 /output/pot13_1.ptau /output/pot13_final.ptau -v

echo "=== Step 3: Circuit-specific setup (phase 2) ==="
snarkjs groth16 setup /output/age_check_v2.r1cs /output/pot13_final.ptau /output/age_check_v2_0.zkey
snarkjs zkey contribute /output/age_check_v2_0.zkey /output/age_check_v2_final.zkey \
    --name="setup" -e="$RANDOM_HEX2"
snarkjs zkey export verificationkey /output/age_check_v2_final.zkey /output/verification_key.json

echo "=== Done. Artifacts written to /output ==="
