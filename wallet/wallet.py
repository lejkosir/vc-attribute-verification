import json
import time
import base64
import hashlib
import threading
from pathlib import Path
import subprocess
import tempfile
import os
import requests
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import platform
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

# CLI

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
    unhashed = json.loads(base64.b64decode(payload_part.split(".")[1] + "===").decode("utf-8"))["vc"][
        "credentialSubject"]

    print("\nSelect attribute:")
    kv_keys = list(unhashed.keys())
    for i, k in enumerate(kv_keys):
        print(f"[{i}] {k}: {unhashed[k]['val']}")

    idx2 = int(input("Choose: "))
    key = kv_keys[idx2]
    info = unhashed[key]

    payload = {
        "timestamp": int(time.time()),
        "hashed_vc": vc_jwt["credential"][1],
        "disclosed": {
            key: {
                "val": str(info["val"]),
                "salt": str(info["salt"])
            }
        }
    }
    res = requests.post("http://localhost:5000/verify", json=payload)
    print("Result:", res.json())


# API
def selective_disclosure_api(attribute):
    creds = load_credentials()
    if not creds: return {"error": "no_credentials"}

    vc_jwt = creds[0]["vc_jwt"]
    payload_part = vc_jwt["credential"][0]

    try:
        body_json = base64.b64decode(payload_part.split(".")[1] + "===").decode("utf-8")
        unhashed = json.loads(body_json)["vc"]["credentialSubject"]
    except Exception as e:
        return {"error": f"decode_failed: {e}"}

    if attribute not in unhashed: return {"error": "attribute_not_found"}

    info = unhashed[attribute]
    val_to_show = info["val"]

    result_path = os.path.join(tempfile.gettempdir(), "wallet_decision.txt")

    if platform.system() == "Windows":
        cmd = f'echo OFF & cls & echo VC REQUEST: {attribute} ({val_to_show}) & set /p choice="Allow? (y/n): " & echo !choice! > "{result_path}"'
        subprocess.run(f'start /wait cmd /V:ON /C "{cmd}"', shell=True)
    else:
        linux_cmd = f'echo "VC REQUEST: {attribute} ({val_to_show})"; read -p "Allow? (y/n): " choice; echo $choice > "{result_path}"'
        subprocess.run(['xterm', '-e', 'bash', '-c', linux_cmd])

    time.sleep(0.2)
    decision = "n"
    if os.path.exists(result_path):
        with open(result_path, "r") as f:
            decision = f.read().strip().lower()
        try:
            os.remove(result_path)
        except:
            pass

    if decision.startswith('y'):
        print(f"APPROVED: Shared {attribute}")
        return {
            "timestamp": int(time.time()),
            "hashed_vc": vc_jwt["credential"][1],
            "disclosed": {
                attribute: {
                    "val": str(info["val"]),
                    "salt": str(info["salt"])  # Ensure this is a string
                }
            }
        }
    else:
        print(f"DENIED: User typed '{decision}'")
        return {"error": "denied"}

# ZKP

def generate_zkp(val, salt, expected_hash):
    witness_js = "generate_witness.js"
    wasm_file = "age_check.wasm"
    zkey_file = "age_check_final.zkey"
    input_file = "input.json"
    witness_file = "witness.wtns"
    proof_file = "proof.json"
    public_file = "public.json"




    creds = load_credentials()
    if not creds: return {"error": "no_credentials"}

    vc_jwt = creds[0]["vc_jwt"]
    payload_part = vc_jwt["credential"][0]

    try:
        body_json = base64.b64decode(payload_part.split(".")[1] + "===").decode("utf-8")
        unhashed = json.loads(body_json)["vc"]["credentialSubject"]
    except Exception as e:
        return {"error": f"decode_failed: {e}"}


    print(body_json)

    inputs = {
        "val": int(val),
        "salt": str(salt),
        "expectedHash": str(expected_hash)
    }

    with open(WALLET_DIR / input_file, "w") as f:
        json.dump(inputs, f)

    subprocess.run(
        ['node', witness_js, wasm_file, input_file, witness_file],
        cwd=WALLET_DIR,
        check=True
    )

    cmd = f'snarkjs groth16 prove {zkey_file} {witness_file} {proof_file} {public_file}'
    subprocess.run(
        cmd,
        cwd=WALLET_DIR,
        shell=True,
        check=True
    )
    time.sleep(0.2)
    with open(WALLET_DIR / "proof.json", "r") as f:
        proof = json.load(f)
    with open(WALLET_DIR / "public.json", "r") as f:
        public = json.load(f)
    print(proof, public)
    return proof, public


# ZKP API
def zkp_disclosure_api(attribute):
    creds = load_credentials()
    if not creds: return {"error": "no_credentials"}

    vc_jwt = creds[0]["vc_jwt"]

    # Decode plaintext JWT for val and salt
    plaintext_part = vc_jwt["credential"][0]
    try:
        body_json = base64.b64decode(plaintext_part.split(".")[1] + "===").decode("utf-8")
        unhashed = json.loads(body_json)["vc"]["credentialSubject"]
    except Exception as e:
        return {"error": f"decode_failed: {e}"}

    if attribute not in unhashed: return {"error": "attribute_not_found"}
    info = unhashed[attribute]

    # Decode hashed JWT for expected hash
    hashed_part = vc_jwt["credential"][1]
    try:
        hashed_body = base64.b64decode(hashed_part.split(".")[1] + "===").decode("utf-8")
        hashed_claims = json.loads(hashed_body)["vc"]["credentialSubject"]
    except Exception as e:
        return {"error": f"decode_hashed_failed: {e}"}

    expected_hash = hashed_claims[attribute]["hash"]
    val_to_show = info["val"]

    result_path = os.path.join(tempfile.gettempdir(), "wallet_decision.txt")

    if platform.system() == "Windows":
        cmd = f'echo OFF & cls & echo ZKP REQUEST: {attribute} ({val_to_show}) & set /p choice="Allow? (y/n): " & echo !choice! > "{result_path}"'
        subprocess.run(f'start /wait cmd /V:ON /C "{cmd}"', shell=True)
    else:
        linux_cmd = f'echo "ZKP REQUEST: {attribute} ({val_to_show})"; read -p "Allow? (y/n): " choice; echo $choice > "{result_path}"'
        subprocess.run(['xterm', '-e', 'bash', '-c', linux_cmd])

    time.sleep(0.2)
    decision = "n"
    if os.path.exists(result_path):
        with open(result_path, "r") as f:
            decision = f.read().strip().lower()
        try:
            os.remove(result_path)
        except:
            pass

    if decision.startswith('y'):
        print(f"APPROVED: ZKP for {attribute}")
        result = generate_zkp(info["val_int"], info["salt"], expected_hash)
        if isinstance(result, dict):  # error from generate_zkp
            return result
        proof, public = result
        return {
            "proof": proof,
            "public": public,
            "hashed_vc": vc_jwt["credential"][1],
            "attribute": attribute
        }
    else:
        print(f"DENIED: User typed '{decision}'")
        return {"error": "denied"}


# SERVER
app = FastAPI()

class DisclosureRequest(BaseModel):
    attribute: str

@app.post("/disclose")
def disclose(req: DisclosureRequest):
    return selective_disclosure_api(req.attribute)

@app.post("/disclose_zkp")
def disclose_zkp(req: DisclosureRequest):
    return zkp_disclosure_api(req.attribute)

def start_server():
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")


def main_menu():
    ensure_storage()

    while True:
        print("\n=== VC Wallet ===")
        print("1. Request VC from CA")
        print("2. List credentials")
        print("3. Selective disclosure (manual)")
        print("4. Remove credentials")
        print("5. DEBUG ZKP")
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
        elif choice == "5":
            generate_zkp(val="23", salt="55139075980980285140718201367886350513", expected_hash="15656714370521641343762386545036458095253698961471300526207916569789931879587")
        elif choice == "9":
            break


if __name__ == "__main__":
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    main_menu()