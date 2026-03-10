## Verifiable Credentials Attribute Verification Demonstration

This project implements a minimal end‑to‑end system for attribute verification using W3C Verifiable Credentials. It demonstrates two methods:

1. Selective Disclosure (SD) using hashed claims  
2. Zero‑Knowledge Proofs (ZKPs) # TODO

The system includes:
- CA service issuing JWT‑VCs with hashed attributes
- Local wallet (CLI + API) for storing VCs and generating disclosures
- Browser extension that mediates between websites and the wallet
- Verifier server validating proofs and establishing a session
- Demo website requesting and verifying attributes

The project shows how a user can prove a specific attribute (e.g. age) without revealing the full credential.

### Setup

1. Clone this repository.
2. Run `docker compose up` to start the CA and verifier services.
3. In Firefox, open `about:debugging#/runtime/this-firefox` and load the temporary extension by selecting `manifest.json`.
4. Start the wallet by running `wallet.py`.
