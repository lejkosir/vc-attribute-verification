## Verifiable Credentials Attribute Verification Demo

End-to-end W3C Verifiable Credentials system with three attribute verification methods:

1. **Selective Disclosure (SD)** — discloses attribute value + Poseidon salt so the verifier can recheck the signed hash
2. **ZKP V1** — proves knowledge of a hash preimage without revealing the value or salt
3. **ZKP V2 (unlinkable)** — proves an attribute meets a threshold using an EdDSA signature verified inside the circuit; nothing leaves the wallet

### Components

**`vc-ca/`** (FastAPI, port 8000) — CA service. Issues ES256 JWT-VCs with Poseidon-hashed attributes and an EdDSA-signed credential component (BabyJubJub). Public keys at `/public_key` and `/public_key_bjj`.

**`wallet/wallet.py`** (FastAPI, port 8001 + CLI) — Stores credentials in `~/.vcwallet/credentials.json`. Endpoints: `/disclose`, `/disclose_zkp`, `/disclose_zkp_v2`. Each spawns a native terminal popup for user consent.

**`ff-extension/`** (Firefox WebExtension MV2) — Polls for a `<div id="vc-request">` on the page; `data-method` selects the proof type (`sd`, `zkp`, `zkp_v2`). Calls the appropriate wallet endpoint and dispatches a `VCResponse` event back to the page.

**`verifier-site/`** (Flask, port 5000) — Serves the demo page and verifies all three proof types (`/verify`, `/verify_zkp`, `/verify_zkp_v2`). Sets a `verified_age` session cookie on success.

**`circuits/`** — Circom ZKP circuits and precompiled artifacts for V1 (hash-preimage) and V2 (EdDSA threshold).

### Credential Format

```
credential[0]  plaintext JWT (ES256)  — attribute values + salts, kept local
credential[1]  hashed JWT (ES256)     — Poseidon hashes only, sent to verifier
credential[2]  EdDSA credential       — BabyJubJub signatures per attribute, used by ZKP V2
```

### Setup

**1. Install dependencies**
```bash
npm install           # circomlibjs for local Poseidon hashing
npm install -g snarkjs
pip install -r wallet/requirements.txt
```

`vc-ca` and `verifier-site` run in Docker — no local pip install needed for them.

Both V1 (`circuits/age_checkV1/`) and V2 (`circuits/age_checkV2/`) artifacts are precompiled and read in-place — no copying needed.

**3. Start services**
```bash
docker compose up
```

**4. Load the Firefox extension**

Open `about:debugging#/runtime/this-firefox` → Load Temporary Add-on → select `ff-extension/manifest.json`.

**5. Start the wallet**
```bash
python wallet/wallet.py
```

### Recompiling circuits

Precompiled artifacts are included so you only need to recompile if you modify a `.circom` file.

**V1** — run the setup script from the repo root:
```bash
bash circuits/age_checkV1/setup.sh        # Linux / macOS
powershell -ExecutionPolicy Bypass -File circuits/age_checkV1/setup.ps1  # Windows
```

**V2** — run the Docker-based setup container (no local circom required):
```bash
docker compose --profile setup run circom
```

### Dependencies

- Docker and Docker Compose
- Python 3.11+
- Node.js + `npm install` at repo root
- `snarkjs` globally: `npm install -g snarkjs`
