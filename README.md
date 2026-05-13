## Verifiable Credentials Attribute Verification Demo

ZK age verification using W3C Verifiable Credentials, BabyJubJub EdDSA signatures, and Groth16 ZK proofs. The user proves they are 18+ without revealing their birthdate.

### Components

**`vc-ca/`** (FastAPI, port 8000) — CA service. Takes a subject ID and birthdate, hashes the birthdate with Poseidon, signs the hash with BabyJubJub, and returns a W3C VC JSON.

**`ff-extension-wallet/`** (Firefox WebExtension MV2) — Browser wallet. Stores credentials in `browser.storage.local`. On a verification request, generates a Groth16 ZK proof in-browser using snarkjs (bundled wasm + zkey). No external wallet process needed.

**`verifier-site/`** (Flask, port 5000) — Demo page and verifier. Checks the proof against the circuit's verification key, validates the CA public key, checks proof freshness (5 min window), and checks the minAge signal. Sets a `verified_age` cookie on success.

**`circuits/age_checkV2/`** — Circom circuit and precompiled artifacts. Proves `currentDate - birthdate >= 18 years` over a CA-signed birthdate without revealing it.

### Credential format

The CA returns a W3C VC with the birthdate hash + EdDSA signature in the proof, plus a separate `private` field (birthdate as Unix timestamp + salt) that only the wallet stores.

### Setup

**1. Start CA and verifier**
```bash
docker compose up
```

**2. Load the extension**

`about:debugging` → Load Temporary Add-on → select `ff-extension-wallet/manifest.json`

**3. Get a VC**

Click the extension icon, enter a subject ID and birthdate, click Request.

**4. Verify**

Go to `http://localhost:5000`, click Verify age, approve in the extension popup.

### Recompiling the circuit

Only needed if you modify `age_check_v2.circom`:
```bash
docker compose --profile setup run --rm --build circom
```

### Dependencies

- Docker and Docker Compose
- Firefox
