#!/bin/bash
# Trusted setup for age_checkV2 circuit.
# Run from the repo root: bash circuits/age_checkV2/setup.sh
#
# Requirements:
#   - circom 2.x installed (https://docs.circom.io/getting-started/installation/)
#   - snarkjs installed globally: npm install -g snarkjs
#   - circomlib installed locally: npm install circomlib (at repo root)

set -e

CIRCUIT_DIR="circuits/age_checkV2"
CIRCUIT_NAME="age_check_v2"
WALLET_DIR="$HOME/.vcwallet"

echo "=== Step 1: Compile circuit ==="
circom "$CIRCUIT_DIR/$CIRCUIT_NAME.circom" \
    --r1cs --wasm --sym \
    -l node_modules/circomlib/circuits \
    -o "$CIRCUIT_DIR"

echo "=== Step 2: Powers of Tau (phase 1) ==="
# 2^13 = 8192 capacity — sufficient for ~4300 constraints
snarkjs powersoftau new bn128 13 "$CIRCUIT_DIR/pot13_0.ptau" -v
snarkjs powersoftau contribute "$CIRCUIT_DIR/pot13_0.ptau" \
    "$CIRCUIT_DIR/pot13_1.ptau" --name="dev" -e="$(openssl rand -hex 32)"
snarkjs powersoftau prepare phase2 "$CIRCUIT_DIR/pot13_1.ptau" \
    "$CIRCUIT_DIR/pot13_final.ptau" -v

echo "=== Step 3: Circuit-specific setup (phase 2) ==="
snarkjs groth16 setup "$CIRCUIT_DIR/$CIRCUIT_NAME.r1cs" \
    "$CIRCUIT_DIR/pot13_final.ptau" \
    "$CIRCUIT_DIR/${CIRCUIT_NAME}_0.zkey"
snarkjs zkey contribute "$CIRCUIT_DIR/${CIRCUIT_NAME}_0.zkey" \
    "$CIRCUIT_DIR/${CIRCUIT_NAME}_final.zkey" --name="dev" -e="$(openssl rand -hex 32)"
snarkjs zkey export verificationkey "$CIRCUIT_DIR/${CIRCUIT_NAME}_final.zkey" \
    "$CIRCUIT_DIR/verification_key.json"

echo "=== Step 4: Copy proving artifacts to wallet dir ==="
mkdir -p "$WALLET_DIR"
cp "$CIRCUIT_DIR/${CIRCUIT_NAME}_js/$CIRCUIT_NAME.wasm"   "$WALLET_DIR/age_check_v2.wasm"
cp "$CIRCUIT_DIR/${CIRCUIT_NAME}_js/generate_witness.js"  "$WALLET_DIR/generate_witness_v2.js"
cp "$CIRCUIT_DIR/${CIRCUIT_NAME}_js/witness_calculator.js" "$WALLET_DIR/witness_calculator_v2.js"
cp "$CIRCUIT_DIR/${CIRCUIT_NAME}_final.zkey"              "$WALLET_DIR/age_check_v2_final.zkey"

echo "=== Step 5: Copy verification key to verifier-site ==="
cp "$CIRCUIT_DIR/verification_key.json" "verifier-site/verification_key_v2.json"

echo ""
echo "Setup complete. Rebuild Docker containers to pick up the new verification key:"
echo "  docker compose up --build"
