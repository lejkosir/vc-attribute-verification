# Trusted setup for age_checkV1 circuit.
# Run from the repo root:
#   powershell -ExecutionPolicy Bypass -File circuits/age_checkV1/setup.ps1
#
# Requirements:
#   - circom 2.x on PATH  (https://docs.circom.io/getting-started/installation/)
#   - snarkjs on PATH     (npm install -g snarkjs)
#   - circomlib installed  (npm install  -- at repo root)

$ErrorActionPreference = "Stop"

$CIRCUIT_DIR  = "circuits\age_checkV1"
$CIRCUIT_NAME = "age_check"
$WALLET_DIR   = "$env:USERPROFILE\.vcwallet"

function Random-Hex {
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    return ($bytes | ForEach-Object { $_.ToString("x2") }) -join ""
}

# ── Step 1: Compile ──────────────────────────────────────────────────────────
Write-Host "=== Step 1: Compile circuit ===" -ForegroundColor Cyan
circom "$CIRCUIT_DIR\$CIRCUIT_NAME.circom" `
    --r1cs --wasm --sym `
    -l node_modules\circomlib\circuits `
    -o $CIRCUIT_DIR

# ── Step 2: Powers of Tau (phase 1) ──────────────────────────────────────────
Write-Host "=== Step 2: Powers of Tau (phase 1) ===" -ForegroundColor Cyan
# 2^12 = 4096 capacity — sufficient for Poseidon(2) (~250 constraints)
snarkjs powersoftau new bn128 12 "$CIRCUIT_DIR\pot12_0.ptau" -v
snarkjs powersoftau contribute "$CIRCUIT_DIR\pot12_0.ptau" `
    "$CIRCUIT_DIR\pot12_1.ptau" --name="dev" -e="$(Random-Hex)"
snarkjs powersoftau prepare phase2 "$CIRCUIT_DIR\pot12_1.ptau" `
    "$CIRCUIT_DIR\pot12_final.ptau" -v

# ── Step 3: Circuit-specific setup (phase 2) ─────────────────────────────────
Write-Host "=== Step 3: Circuit-specific setup (phase 2) ===" -ForegroundColor Cyan
snarkjs groth16 setup "$CIRCUIT_DIR\$CIRCUIT_NAME.r1cs" `
    "$CIRCUIT_DIR\pot12_final.ptau" `
    "$CIRCUIT_DIR\${CIRCUIT_NAME}_0.zkey"
snarkjs zkey contribute "$CIRCUIT_DIR\${CIRCUIT_NAME}_0.zkey" `
    "$CIRCUIT_DIR\${CIRCUIT_NAME}_final.zkey" --name="dev" -e="$(Random-Hex)"
snarkjs zkey export verificationkey "$CIRCUIT_DIR\${CIRCUIT_NAME}_final.zkey" `
    "$CIRCUIT_DIR\verification_key.json"

# ── Step 4: Copy proving artifacts to wallet dir ──────────────────────────────
Write-Host "=== Step 4: Copy artifacts to wallet ===" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $WALLET_DIR | Out-Null

$jsDir = "$CIRCUIT_DIR\${CIRCUIT_NAME}_js"
Copy-Item "$jsDir\$CIRCUIT_NAME.wasm"       "$WALLET_DIR\age_check.wasm"        -Force
Copy-Item "$jsDir\generate_witness.js"      "$WALLET_DIR\generate_witness.js"   -Force
Copy-Item "$jsDir\witness_calculator.js"    "$WALLET_DIR\witness_calculator.js" -Force
Copy-Item "$CIRCUIT_DIR\${CIRCUIT_NAME}_final.zkey" "$WALLET_DIR\age_check_final.zkey" -Force

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Rebuild Docker containers to pick up the new verification key:"
Write-Host "  docker compose up --build"
