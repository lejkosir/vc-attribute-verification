import json
import time
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

PROJECT_ROOT = Path(__file__).parent.parent
CIRCUIT_V2_DIR = PROJECT_ROOT / "circuits" / "age_checkV2"
CIRCUIT_V2_JS = CIRCUIT_V2_DIR / "age_check_v2_js"


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

def fetch_vc_from_ca():
    subject_id = input("Enter subject ID: ")
    birthdate = input("Enter birthdate (YYYY-MM-DD): ").strip()

    payload = {"subject_id": subject_id, "birthdate": birthdate}

    print("\nRequesting VC from CA...")
    res = requests.post("http://localhost:8000/issue_vc", json=payload)

    if res.status_code == 200:
        data = res.json()
        creds = load_credentials()
        creds.append({"vc": data["vc"], "private": data["private"]})
        save_credentials(creds)
        print("Saved in wallet.\n")
    else:
        print("Error:", res.text)


def list_credentials():
    creds = load_credentials()
    if not creds:
        print("No credentials stored.\n")
        return

    print("\nStored credentials:")
    for i, c in enumerate(creds):
        vc = c["vc"]
        print(f"[{i}] id:{vc['id']} | validFrom:{vc['validFrom']}")

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

def popup(val_to_show):
    result_path = os.path.join(tempfile.gettempdir(), "wallet_decision.txt")

    if platform.system() == "Windows":
        cmd = f'echo OFF & cls & echo ZKP V2 REQUEST: {val_to_show} & set /p choice="Allow? (y/n): " & echo !choice! > "{result_path}"'
        subprocess.run(f'start /wait cmd /V:ON /C "{cmd}"', shell=True)
    else:
        linux_cmd = f'echo "ZKP V2 REQUEST: {val_to_show}"; read -p "Allow? (y/n): " choice; echo $choice > "{result_path}"'
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
    return decision


# ZKP V2

MIN_AGE_SECONDS = 18 * 365 * 86400

def generate_zkp_v2(birthdate, salt, R8x, R8y, S, Ax, Ay):
    wasm_file = "age_check_v2.wasm"
    zkey_file = str(CIRCUIT_V2_DIR / "age_check_v2_final.zkey")
    input_file = "input_v2.json"
    witness_file = "witness_v2.wtns"
    proof_file = "proof_v2.json"
    public_file = "public_v2.json"

    if not CIRCUIT_V2_JS.exists():
        return {"error": "circuit files not found"}

    current_date = int(time.time())

    if current_date - int(birthdate) < MIN_AGE_SECONDS:
        return {"error": "age below minimum"}

    inputs = {
        "birthdate": str(birthdate),
        "salt": str(salt),
        "R8x": str(R8x),
        "R8y": str(R8y),
        "S": str(S),
        "Ax": str(Ax),
        "Ay": str(Ay),
        "Ax_pub": str(Ax),
        "Ay_pub": str(Ay),
        "currentDate": str(current_date),
        "minAge": str(MIN_AGE_SECONDS)
    }

    with open(CIRCUIT_V2_JS / input_file, "w") as f:
        json.dump(inputs, f)

    subprocess.run(
        ['node', 'generate_witness.js', wasm_file, input_file, witness_file],
        cwd=CIRCUIT_V2_JS,
        check=True
    )

    cmd = f'snarkjs groth16 prove "{zkey_file}" {witness_file} {proof_file} {public_file}'
    subprocess.run(cmd, cwd=CIRCUIT_V2_JS, shell=True, check=True)

    time.sleep(0.2)
    with open(CIRCUIT_V2_JS / proof_file) as f:
        proof = json.load(f)
    with open(CIRCUIT_V2_JS / public_file) as f:
        public = json.load(f)
    return proof, public


def zkp_v2_disclosure_api():
    creds = load_credentials()
    if not creds:
        return {"error": "no_credentials"}

    entry = creds[0]
    vc = entry["vc"]
    private = entry["private"]

    proof_val = vc["proof"]["proofValue"]
    pk = vc["proof"]["publicKey"]

    decision = popup("age verification (birthdate hidden)")

    if decision.startswith('y'):
        print("approved")
        result = generate_zkp_v2(
            birthdate=private["birthdate_int"],
            salt=private["salt"],
            R8x=proof_val["R8x"],
            R8y=proof_val["R8y"],
            S=proof_val["S"],
            Ax=pk["Ax"],
            Ay=pk["Ay"]
        )
        if isinstance(result, dict):
            return result
        proof, public = result
        return {"proof": proof, "public": public}
    else:
        print("denied")
        return {"error": "denied"}


# SERVER
app = FastAPI()

class DisclosureRequest(BaseModel):
    attribute: str

@app.post("/disclose_zkp_v2")
def disclose_zkp_v2(req: DisclosureRequest):
    return zkp_v2_disclosure_api()

def start_server():
    uvicorn.run(app, host="127.0.0.1", port=8501, log_level="info")


def main_menu():
    ensure_storage()

    while True:
        print("\n=== VC Wallet ===")
        print("1. Request VC from CA")
        print("2. List credentials")
        print("3. Remove credentials")
        print("4. ZKP V2 disclosure")
        print("9. Exit")

        choice = input("> ")

        if choice == "1":
            fetch_vc_from_ca()
        elif choice == "2":
            list_credentials()
        elif choice == "3":
            remove_credentials()
        elif choice == "4":
            result = zkp_v2_disclosure_api()
            print("Result:", result)
        elif choice == "9":
            break


if __name__ == "__main__":
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    main_menu()
