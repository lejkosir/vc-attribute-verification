import os
import json
import datetime
from fastapi import FastAPI
from pydantic import BaseModel
import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import hashlib, base64


app = FastAPI(title="VC CA Service")

KEYS_DIR = "keys"
PRIVATE_KEY_PATH = os.path.join(KEYS_DIR, "ec_private.pem")
PUBLIC_KEY_PATH = os.path.join(KEYS_DIR, "ec_public.pem")


def ensure_keys():
    os.makedirs(KEYS_DIR, exist_ok=True)

    if not os.path.exists(PRIVATE_KEY_PATH):
        print("Generating EC keypair...")
        private_key = ec.generate_private_key(ec.SECP256R1())

        with open(PRIVATE_KEY_PATH, "wb") as f:
            f.write(
                private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )

        public_key = private_key.public_key()
        with open(PUBLIC_KEY_PATH, "wb") as f:
            f.write(
                public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                )
            )

    print("Keys ready.")


ensure_keys()


def load_private_key():
    with open(PRIVATE_KEY_PATH, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def load_public_key():
    with open(PUBLIC_KEY_PATH, "rb") as f:
        return serialization.load_pem_public_key(f.read())


class VCRequest(BaseModel):
    subject_id: str
    attributes: dict

def hash_claims(attributes):
    hashed = {}
    for key, value in attributes.items():
        salt = os.urandom(16)
        combined = f"{key}:{value}".encode() + salt
        h = hashlib.sha256(combined).hexdigest()

        hashed[key] = {
            "hash": h,
            "salt": base64.b64encode(salt).decode()
        }
    return hashed

@app.post("/issue_vc")
def issue_vc(req: VCRequest):
    private_key = load_private_key()

    vc_payload = {
        "iss": "did:example:ca",
        "sub": req.subject_id,
        "nbf": int(datetime.datetime.utcnow().timestamp()),
        "iat": int(datetime.datetime.utcnow().timestamp()),
        "vc": {
            "type": ["VerifiableCredential"],
            "credentialSubject": req.attributes
        }
    }

    vc_payload_hashed = {
        "iss": "did:example:ca",
        "sub": req.subject_id,
        "nbf": int(datetime.datetime.utcnow().timestamp()),
        "iat": int(datetime.datetime.utcnow().timestamp()),
        "vc": {
            "type": ["VerifiableCredential"],
            "credentialSubject": hash_claims(req.attributes)
        }
    }

    jwt_vc = jwt.encode(
        vc_payload,
        private_key,
        algorithm="ES256"
    )
    jwt_vc_hashed = jwt.encode(
        vc_payload_hashed,
        private_key,
        algorithm="ES256"
    )

    return {
        "credential": (jwt_vc, jwt_vc_hashed)
    }


@app.get("/public_key")
def get_public_key():
    with open(PUBLIC_KEY_PATH, "r") as f:
        pub = f.read()
    return {"publicKeyPem": pub}