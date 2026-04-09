import datetime
from fastapi import FastAPI
from pydantic import BaseModel
import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import hashlib, base64
import os
import subprocess


app = FastAPI(title="VC CA Service")

KEYS_DIR = "keys"
PRIVATE_KEY_PATH = os.path.join(KEYS_DIR, "ec_private.pem")
PUBLIC_KEY_PATH = os.path.join(KEYS_DIR, "ec_public.pem")

# TODO: SALT V NON-HASHED VC!!!!!!!
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


def get_poseidon_hash(value, salt):
    result = subprocess.run(
        ['node', '/app/poseidon_hasher.js', str(value), str(salt)],
        capture_output=True, text=True
    )
    if result.stderr:
        print("Node Error:", result.stderr)
    return int(result.stdout.strip())


def normalize_and_convert(v):
    if isinstance(v, int):
        return v
    if str(v).isdigit():
        return int(v)

    s = str(v)
    mapping = {"č": "c", "š": "s", "ž": "z", "ć": "c", "đ": "d", "Č": "C", "Š": "S", "Ž": "Z", "Ć": "C", "Đ": "D"}
    for char, replacement in mapping.items():
        s = s.replace(char, replacement)

    b = s[:31].encode('utf-8')
    return int.from_bytes(b, byteorder='big')


def hash_claims(attributes):
    hashed = {}
    for key, value in attributes.items():
        salt_bytes = os.urandom(16)
        salt_int = int.from_bytes(salt_bytes, byteorder='big')

        val_int = normalize_and_convert(value)

        h = get_poseidon_hash(val_int, salt_int)

        hashed[key] = {
            "hash": h,
            "salt": salt_int,
            "raw_value": val_int
        }
    return hashed


def process_claims(attributes):
    public_subject = {}
    private_subject = {}
    for key, value in attributes.items():
        salt_int = int.from_bytes(os.urandom(16), byteorder='big')
        val_int = normalize_and_convert(value)
        h = get_poseidon_hash(val_int, salt_int)

        public_subject[key] = {"hash": str(h)}  # STORE AS STRING
        private_subject[key] = {
            "val": value,
            "val_int": val_int,
            "salt": str(salt_int),  # STORE AS STRING
            "hash": str(h)  # STORE AS STRING
        }
    return public_subject, private_subject

@app.post("/issue_vc")
def issue_vc(req: VCRequest):
    private_key = load_private_key()

    public_claims, private_secrets = process_claims(req.attributes)

    now = int(datetime.datetime.utcnow().timestamp())

    # plaintext with salt
    vc_payload = {
        "iss": "did:example:ca",
        "sub": req.subject_id,
        "nbf": now,
        "iat": now,
        "vc": {
            "type": ["VerifiableCredential", "PrivateSecrets"],
            "credentialSubject": private_secrets
        }
    }

    # hashed
    vc_payload_hashed = {
        "iss": "did:example:ca",
        "sub": req.subject_id,
        "nbf": now,
        "iat": now,
        "vc": {
            "type": ["VerifiableCredential", "HashedClaims"],
            "credentialSubject": public_claims
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