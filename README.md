## Verifiable Credentials Attribute Verification Demonstration

This project implements a minimal end‑to‑end system for attribute verification using W3C Verifiable Credentials. It demonstrates three methods:

1. Selective Disclosure (SD) — discloses an attribute value and its Poseidon salt so the verifier can recompute the signed hash
2. Zero‑Knowledge Proof (ZKP) — proves knowledge of a hash preimage without revealing the value or salt
3. Zero‑Knowledge Proof V2 (ZKP unlinkable) — proves an attribute satisfies a threshold using an EdDSA signature verified inside the circuit; no plaintext or salt leaves the wallet

The system includes:
- CA service issuing JWT‑VCs with Poseidon‑hashed attributes, plus a BabyJubJub EdDSA‑signed credential component for ZKP V2
- Local wallet (CLI + API) for storing VCs and generating disclosures or ZK proofs
- Browser extension that mediates between websites and the wallet
- Verifier server validating all three proof types and setting a session cookie
- Demo website with buttons for each verification method

The project shows how a user can prove a specific attribute (e.g. age) without revealing the full credential.

### Components

**`vc-ca/`** (FastAPI, port 8000) — Certificate Authority. On `/issue_vc` it hashes each attribute with a random salt using Poseidon, issues two ES256 JWT‑VCs (one with plaintext + salt, one with hashes only), and also produces an EdDSA‑signed credential using a BabyJubJub keypair (`eddsa_signer.js`). All three are returned together. The EC public key is served at `/public_key`; the BabyJubJub public key at `/public_key_bjj`.

**`wallet/wallet.py`** (FastAPI, port 8001 + CLI) — Stores credentials in `~/.vcwallet/credentials.json`. Exposes three endpoints:
- `/disclose` — selective disclosure (SD)
- `/disclose_zkp` — ZKP hash‑preimage proof (V1 circuit)
- `/disclose_zkp_v2` — ZKP unlinkable proof (V2 circuit, EdDSA in‑circuit)

Each endpoint spawns a native terminal popup for user consent before releasing any data. The CLI menu also provides manual SD and ZKP V2 disclosure options.

**`ff-extension/`** (Firefox WebExtension MV2) — `content.js` polls for a `<div id="vc-request">` element; its `data-method` attribute selects the proof type (`sd`, `zkp`, or `zkp_v2`). After user confirmation via `confirm()`, `background.js` calls the appropriate wallet endpoint and dispatches a `VCResponse` custom event on the page.

**`verifier-site/`** (Flask, port 5000) — Serves the demo page and three verification routes:
- `/verify` — recomputes Poseidon hash of disclosed value and salt, checks against CA‑signed hash
- `/verify_zkp` — runs `snarkjs groth16 verify` against V1 `verification_key.json`, pins the proof's public hash signal to the CA‑signed value
- `/verify_zkp_v2` — runs `snarkjs groth16 verify` against V2 `verification_key.json`, pins public inputs to the CA's BabyJubJub public key and the required threshold (18)

All verification routes set a `verified_age` session cookie on success.

**`circuits/age_checkV1/`** — Circom circuit and compiled artifacts (WASM + zkey + verification key) for the hash‑preimage ZKP. The circuit takes `val` and `salt` as private inputs and `expectedHash` as a public input, and constrains `Poseidon(val, salt) == expectedHash`. Precompiled artifacts are included in the repository. To regenerate them from `age_check.circom`, run the setup script from the repo root:

```bash
# Linux / macOS
bash circuits/age_checkV1/setup.sh

# Windows
powershell -ExecutionPolicy Bypass -File circuits/age_checkV1/setup.ps1
```

The scripts compile the circuit, run a local Powers of Tau ceremony (2^12), produce `age_check_final.zkey` and `verification_key.json`, and copy the proving artifacts to `~/.vcwallet/` where the wallet expects them.

**`circuits/age_checkV2/`** — Circom circuit and compiled artifacts (WASM + zkey + verification key) for the unlinkable ZKP. The circuit verifies an EdDSA‑Poseidon signature over the attribute hash and checks `val >= threshold` in one proof. Precompiled artifacts are included in the repository. To regenerate them, either run the Docker‑based setup container or the setup script directly from the repo root:

```bash
# Via Docker (no local circom required)
docker compose --profile setup run circom

# Linux / macOS (requires circom 2.x installed locally)
bash circuits/age_checkV2/setup.sh

# Windows
powershell -ExecutionPolicy Bypass -File circuits/age_checkV2/setup.ps1
```

**`circom/`** — Docker‑based setup container that compiles `age_check_v2.circom`, runs the Powers of Tau ceremony, and writes all artifacts to `circuits/age_checkV2/`.

### Setup

1. Clone this repository.
2. Run `npm install` at the repo root (provides `circomlibjs` for local use).
3. Copy the precompiled V1 proving artifacts to the wallet directory:
   ```bash
   # Linux / macOS
   mkdir -p ~/.vcwallet
   cp circuits/age_checkV1/age_check_js/age_check.wasm ~/.vcwallet/age_check.wasm
   cp circuits/age_checkV1/age_check_js/generate_witness.js ~/.vcwallet/generate_witness.js
   cp circuits/age_checkV1/age_check_js/witness_calculator.js ~/.vcwallet/witness_calculator.js
   cp circuits/age_checkV1/age_check_final.zkey ~/.vcwallet/age_check_final.zkey
   ```
   On Windows, run `powershell -ExecutionPolicy Bypass -File circuits/age_checkV1/setup.ps1` which handles this automatically (it also recompiles, but the output is deterministic given the same entropy).
4. Run `docker compose up` to start the CA and verifier services.
5. In Firefox, open `about:debugging#/runtime/this-firefox` and load the temporary extension by selecting `ff-extension/manifest.json`.
6. Start the wallet by running `python wallet/wallet.py`.

### Dependencies

- Docker and Docker Compose
- Python 3.11+ with packages from each service's `requirements.txt`
- Node.js with `circomlibjs` (`npm install` at repo root)
- `snarkjs` CLI available globally (`npm install -g snarkjs`) — required by the wallet for local proof generation

### Credential Format

Each stored credential contains three components:

```
credential[0]  plaintext JWT (ES256) — attribute values + salts, kept local
credential[1]  hashed JWT (ES256)    — Poseidon hashes only, sent to verifier
credential[2]  EdDSA credential      — BabyJubJub signatures per attribute, used by ZKP V2
```
