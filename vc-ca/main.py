from fastapi import FastAPI
from pydantic import BaseModel
import json
import os
import subprocess
import uuid
from datetime import datetime, timezone

app = FastAPI()

KEYS_DIR = "keys"
BJJ_PRIVATE_KEY_PATH = os.path.join(KEYS_DIR, "bjj_secret.json")
BJJ_PUBLIC_KEY_PATH = os.path.join(KEYS_DIR, "bjj_public.json")


def ensure_bjj_keys():
    os.makedirs(KEYS_DIR, exist_ok=True)
    if not os.path.exists(BJJ_PRIVATE_KEY_PATH):
        print("Generating BabyJubJub keypair...")
        result = subprocess.run(
            ['node', '/app/eddsa_signer.js', 'keygen'],
            capture_output=True, text=True, check=True
        )
        data = json.loads(result.stdout.strip())
        with open(BJJ_PRIVATE_KEY_PATH, "w") as f:
            json.dump({"sk": data["sk"]}, f)
        with open(BJJ_PUBLIC_KEY_PATH, "w") as f:
            json.dump({"Ax": data["Ax"], "Ay": data["Ay"]}, f)
    print("BabyJubJub keys ready.")


def load_bjj_public_key():
    with open(BJJ_PUBLIC_KEY_PATH) as f:
        return json.load(f)


def sign_with_bjj(hash_int):
    with open(BJJ_PRIVATE_KEY_PATH) as f:
        sk = json.load(f)["sk"]
    result = subprocess.run(
        ['node', '/app/eddsa_signer.js', 'sign', sk, str(hash_int)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError("sign failed")
    return json.loads(result.stdout.strip())


def get_poseidon_hash(value, salt):
    result = subprocess.run(
        ['node', '/app/poseidon_hasher.js', str(value), str(salt)],
        capture_output=True, text=True
    )
    if result.stderr:
        print("Node Error:", result.stderr)
    return int(result.stdout.strip())


ensure_bjj_keys()


class VCRequest(BaseModel):
    subject_id: str
    birthdate: str  # ISO "2000-01-15"


@app.post("/issue_vc")
def issue_vc(req: VCRequest):
    birthdate_dt = datetime.strptime(req.birthdate, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    birthdate_int = int(birthdate_dt.timestamp())

    salt_int = int.from_bytes(os.urandom(16), byteorder='big')
    h = get_poseidon_hash(birthdate_int, salt_int)
    sig = sign_with_bjj(h)
    bjj_pk = load_bjj_public_key()

    now_iso = datetime.now(timezone.utc).isoformat()
    credential_id = f"urn:uuid:{uuid.uuid4()}"

    vc = {
        "@context": [
            "https://www.w3.org/ns/credentials/v2",
            "https://example.org/contexts/bjj-poseidon/v1"
        ],
        "id": credential_id,
        "type": ["VerifiableCredential", "AgeCredential"],
        "issuer": "did:example:ca",
        "validFrom": now_iso,
        "credentialSubject": {
            "id": f"did:example:{req.subject_id}",
            "birthdate": {
                "hash": str(h)
            }
        },
        "proof": {
            "type": "BabyJubJubPoseidon2024",
            "created": now_iso,
            "verificationMethod": "did:example:ca#bjj-key-1",
            "proofPurpose": "assertionMethod",
            "proofValue": {
                "R8x": sig["R8x"],
                "R8y": sig["R8y"],
                "S": sig["S"]
            },
            "publicKey": {
                "Ax": bjj_pk["Ax"],
                "Ay": bjj_pk["Ay"]
            }
        }
    }

    return {
        "vc": vc,
        "private": {
            "birthdate_int": birthdate_int,
            "salt": str(salt_int)
        }
    }


@app.get("/public_key_bjj")
def get_public_key_bjj():
    return load_bjj_public_key()
