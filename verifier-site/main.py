from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
import json
import os
import secrets
import time
import requests
import subprocess

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))
CORS(app, supports_credentials=True)

VERIFICATION_KEY_V2_PATH = "/app/circuits_v2/verification_key.json"

EPOCH_OFFSET = 2208988800

CHALLENGE_TTL = 300
CHALLENGES = {}


def prune_challenges():
    now = time.time()
    for chal in [c for c, rec in CHALLENGES.items() if now - rec["issued"] >= CHALLENGE_TTL]:
        CHALLENGES.pop(chal, None)


# challenge
@app.route("/challenge", methods=["GET"])
def get_challenge():
    prune_challenges()

    if "sid" not in session:
        session["sid"] = secrets.token_hex(16)

    chal = str(secrets.randbits(248))
    CHALLENGES[chal] = {"sid": session["sid"], "issued": time.time()}
    return jsonify({"challenge": chal})


@app.route("/status", methods=["GET"])
def status():
    return jsonify({"verified": bool(session.get("age_verified"))})


@app.route("/verify_zkp_v2", methods=["POST"])
def verify_zkp_v2():
    data = request.json
    proof = data.get("proof")
    public = data.get("public")

    # challenge
    rec = CHALLENGES.pop(str(public[4]), None)
    if rec is None:
        print("unknown or already spent challenge")
        return jsonify({"valid": False}), 400

    if rec["sid"] != session.get("sid"):
        print("challenge issued to a different session")
        return jsonify({"valid": False}), 400

    if time.time() - rec["issued"] >= CHALLENGE_TTL:
        print("challenge expired")
        return jsonify({"valid": False}), 400

    ca_bjj = requests.get("http://ca:8000/public_key_bjj").json()

    if str(public[0]) != str(ca_bjj["Ax"]) or str(public[1]) != str(ca_bjj["Ay"]):
        print("key mismatch")
        return jsonify({"valid": False}), 400

    if abs(time.time() + EPOCH_OFFSET - int(public[2])) >= 300:
        print("proof too old")
        return jsonify({"valid": False}), 400

    if int(public[3]) != 18 * 365 * 86400:
        return jsonify({"valid": False}), 400

    with open("/tmp/proof_v2.json", "w") as f:
        json.dump(proof, f)
    with open("/tmp/public_v2.json", "w") as f:
        json.dump(public, f)
    start = time.time()
    result = subprocess.run(
        ["snarkjs", "groth16", "verify", VERIFICATION_KEY_V2_PATH, "/tmp/public_v2.json", "/tmp/proof_v2.json"],
        capture_output=True, text=True
    )
    elapsed = time.time() - start
    print(f"verify time: {elapsed * 1000:.1f} ms")
    print(result.stdout)

    if result.returncode == 0 and "OK!" in result.stdout:
        session["age_verified"] = True
        return jsonify({"valid": True})
    else:
        return jsonify({"valid": False}), 400


@app.route("/")
def home():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
