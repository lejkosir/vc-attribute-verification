import json
import time
import base64
import hashlib
import threading
from pathlib import Path

import requests
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

# STORAGE

WALLET_DIR = Path.home() / ".vcwallet"
VC_STORE = WALLET_DIR / "credentials.json"

def ensure_storage():
    WALLET_DIR.mkdir(parents=True, exist_ok=True)
    if not VC_STORE.exists():
        VC_STORE.write_text(json.dumps({"credentials": []}, indent=2))

def load_credentials():
    with open(VC_STORE, "r") as f:
        data = json.load(f)
    return data["credentials"]

def save_credentials(creds):
    with open(VC_STORE, "w") as f:
        json.dump({"credentials": creds}, f, indent=2)

# padding for base64
def b64url_decode(s):
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)

# get a signed VC from CA
def fetch_vc_from_ca():
    subject_id = input("Enter subject ID: ")
    attr_json = input(
        "Enter attributes JSON (example: {\"age\":23,\"country\":\"SI\"}):\n> "
    )

    try:
        attributes = json.loads(attr_json)
    except:
        print("Invalid JSON.")
        return

    payload = {
        "subject_id": subject_id,
        "attributes": attributes
    }

    print("\nRequesting VC from CA...")
    res = requests.post("http://localhost:8000/issue_vc", json=payload)

    if res.status_code == 200:
        credential = res.json()["credential"]
        creds = load_credentials()
        creds.append(
            {"vc_jwt": {
                "id": subject_id,
                "attributes": attributes,
                "credential": credential
            }}
        )
        save_credentials(creds)
        print("Saved in wallet.\n")
    else:
        print("Error:", res.text)

# -------------------- CLI Functions -----------------------

def list_credentials():
    creds = load_credentials()
    if not creds:
        print("No credentials stored.\n")
        return

    print("\nStored credentials:")
    for i, c in enumerate(creds):
        cr = c["vc_jwt"]
        print(f"[{i}] user:{cr['id']} | attributes:{cr['attributes']} | jwt:{cr['credential'][:50]}...")

def remove_credentials():
    list_credentials()
    creds = load_credentials()
    if not creds:
        return

    idx = int(input("Select index to remove: "))
    if 0 <= idx < len(creds):
        del creds[idx]
        save_credentials(creds)
        print("Removed.\n")

def selective_disclosure_cli():
    creds = load_credentials()
    if not creds:
        print("No credentials.\n")
        return

    list_credentials()
    idx = int(input("Select credential: "))
    vc_jwt = creds[idx]["vc_jwt"]

    payload_part = vc_jwt["credential"][0]
    unhashed = json.loads(
        base64.b64decode(payload_part.split(".")[1]).decode("utf-8")
    )["vc"]["credentialSubject"]

    print("\nSelect attribute:")
    kv_pairs = []
    for i, (k, v) in enumerate(unhashed.items()):
        print(f"[{i}] {k}: {v}")
        kv_pairs.append({k: v})

    idx2 = int(input("Choose: "))
    disclosed = kv_pairs[idx2]
    key = list(disclosed.keys())[0]

    payload = {
        "timestamp": int(time.time()),
        "hashed_vc": vc_jwt["credential"][1],
        "disclosed": disclosed
    }

    res = requests.post("http://localhost:5000/verify", json=payload)
    print("Result:", res.json())

# -------------------- API Selective Disclosure -----------------------

def selective_disclosure_api(attribute):
    creds = load_credentials()
    if not creds:
        return {"error": "no_credentials"}

    vc_jwt = creds[0]["vc_jwt"]

    payload_part = vc_jwt["credential"][0]
    unhashed = json.loads(
        base64.b64decode(payload_part.split(".")[1]).decode("utf-8")
    )["vc"]["credentialSubject"]

    if attribute not in unhashed:
        return {"error": "attribute_not_found"}

    value = unhashed[attribute]
    yn = input(f"Do you want to disclose {attribute}? (y/n): ")
    if yn == "y":
        return {
            "timestamp": int(time.time()),
            "hashed_vc": vc_jwt["credential"][1],
            "disclosed": {attribute: value}
        }
    else:
        return None

# -------------------- FastAPI Server -----------------------

app = FastAPI()

class DisclosureRequest(BaseModel):
    attribute: str

@app.post("/disclose")
def disclose(req: DisclosureRequest):
    return selective_disclosure_api(req.attribute)

def start_server():
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")

# -------------------- CLI -----------------------

def main_menu():
    ensure_storage()

    while True:
        print("\n=== VC Wallet ===")
        print("1. Request VC from CA")
        print("2. List credentials")
        print("3. Selective disclosure (manual)")
        print("4. Remove credentials")
        print("9. Exit")

        choice = input("> ")

        if choice == "1":
            fetch_vc_from_ca()
        elif choice == "2":
            list_credentials()
        elif choice == "3":
            selective_disclosure_cli()
        elif choice == "4":
            remove_credentials()
        elif choice == "9":
            break

# -------------------- Main -----------------------

if __name__ == "__main__":
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    main_menu()