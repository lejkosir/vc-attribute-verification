from flask import Flask, request, jsonify, make_response, render_template
from flask_cors import CORS
import json
import time
import requests
import subprocess

app = Flask(__name__)
CORS(app, supports_credentials=True)

VERIFICATION_KEY_V2_PATH = "/app/circuits_v2/verification_key.json"


@app.route("/verify_zkp_v2", methods=["POST"])
def verify_zkp_v2():
    data = request.json
    proof = data.get("proof")
    public = data.get("public")

    ca_bjj = requests.get("http://ca:8000/public_key_bjj").json()

    if str(public[0]) != str(ca_bjj["Ax"]) or str(public[1]) != str(ca_bjj["Ay"]):
        print("key mismatch")
        return jsonify({"valid": False}), 400

    if abs(time.time() - int(public[2])) >= 300:
        print("proof too old")
        return jsonify({"valid": False}), 400

    if int(public[3]) != 18 * 365 * 86400:
        return jsonify({"valid": False}), 400

    with open("/tmp/proof_v2.json", "w") as f:
        json.dump(proof, f)
    with open("/tmp/public_v2.json", "w") as f:
        json.dump(public, f)

    result = subprocess.run(
        ["snarkjs", "groth16", "verify", VERIFICATION_KEY_V2_PATH, "/tmp/public_v2.json", "/tmp/proof_v2.json"],
        capture_output=True, text=True
    )
    print(result.stdout)

    if result.returncode == 0 and "OK!" in result.stdout:
        resp = make_response(jsonify({"valid": True}))
        resp.set_cookie("verified_age", "true", samesite="Lax")
        return resp
    else:
        return jsonify({"valid": False}), 400


@app.route("/")
def home():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
