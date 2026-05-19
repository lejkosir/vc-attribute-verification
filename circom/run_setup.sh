#!/bin/sh
set -e

RANDOM_HEX=$(node -e "process.stdout.write(require('crypto').randomBytes(32).toString('hex'))")
RANDOM_HEX2=$(node -e "process.stdout.write(require('crypto').randomBytes(32).toString('hex'))")
RANDOM_HEX3=$(node -e "process.stdout.write(require('crypto').randomBytes(32).toString('hex'))")
echo "Starting..."
echo "=== Step 1: Compile circuit ==="
circom /app/age_check_v2.circom \
    --r1cs --wasm --sym \
    -l /app/node_modules/circomlib/circuits \
    -o /output_v2

echo "=== Step 2: Powers of Tau ==="
snarkjs powersoftau new bn128 13 /output_v2/pot13_0.ptau -v
snarkjs powersoftau contribute /output_v2/pot13_0.ptau /output_v2/pot13_1.ptau \
    --name="setup" -e="$RANDOM_HEX"
snarkjs powersoftau prepare phase2 /output_v2/pot13_1.ptau /output_v2/pot13_final.ptau -v

echo "=== Step 3: V2 circuit-specific setup ==="
snarkjs groth16 setup /output_v2/age_check_v2.r1cs /output_v2/pot13_final.ptau /output_v2/age_check_v2_0.zkey
snarkjs zkey contribute /output_v2/age_check_v2_0.zkey /output_v2/age_check_v2_final.zkey \
    --name="setup" -e="$RANDOM_HEX2"
snarkjs zkey export verificationkey /output_v2/age_check_v2_final.zkey /output_v2/verification_key.json

echo "=== Step 4: Copy artifacts to extension assets ==="
cp /output_v2/age_check_v2_js/age_check_v2.wasm /app/ff-extension-wallet/assets/age_check_v2.wasm
cp /output_v2/age_check_v2_final.zkey /app/ff-extension-wallet/assets/age_check_v2_final.zkey

echo "=== Done. Artifacts written to /output_v2 and copied to extension assets ==="
