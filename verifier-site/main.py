from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import json
import requests
import jwt
from cryptography.hazmat.primitives import serialization
import subprocess

app = Flask(__name__)
CORS(app, supports_credentials=True)



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


@app.route("/verify", methods=["POST"])
def verify():
    data = request.json
    hashed_jwt = data["hashed_vc"]
    disclosures = data["disclosed"]

    # CA key
    pub_pem = requests.get("http://ca:8000/public_key").json()["publicKeyPem"]
    public_key = serialization.load_pem_public_key(pub_pem.encode())

    # verify signature
    try:
        payload_json = jwt.decode(hashed_jwt, public_key, algorithms=["ES256"])
    except Exception as e:
        print("jwt error")
        return jsonify({"valid": False}), 400


    ca_signed_claims = payload_json["vc"]["credentialSubject"]

    for key, info in disclosures.items():
        salt = int(info["salt"])
        raw_val = info["val"]
        val_int = normalize_and_convert(raw_val)

        calculated_hash = get_poseidon_hash(val_int, salt)
        expected_hash = int(ca_signed_claims[key]["hash"])

        if calculated_hash != expected_hash:
            return jsonify({"valid": False}), 400

    resp = make_response(jsonify({"valid": True}))
    resp.set_cookie("verified_age", "true", samesite="Lax")
    return resp


VERIFICATION_KEY_PATH    = "/app/verification_key.json"
VERIFICATION_KEY_V2_PATH = "/app/circuits_v2/verification_key.json"

@app.route("/verify_zkp", methods=["POST"])
def verify_zkp():
    data = request.json
    proof = data.get("proof")
    public = data.get("public")
    hashed_jwt = data.get("hashed_vc")
    attribute = data.get("attribute")

    pub_pem = requests.get("http://ca:8000/public_key").json()["publicKeyPem"]
    public_key = serialization.load_pem_public_key(pub_pem.encode())
    try:
        payload_json = jwt.decode(hashed_jwt, public_key, algorithms=["ES256"])
    except Exception as e:
        print("jwt error")
        return jsonify({"valid": False}), 400

    ca_signed_claims = payload_json["vc"]["credentialSubject"]

    ca_hash = str(ca_signed_claims[attribute]["hash"])
    proof_hash = str(public[0])
    if proof_hash != ca_hash:
        print("hash mismatch")
        return jsonify({"valid": False}), 400

    with open("/tmp/proof.json", "w") as f:
        json.dump(proof, f)
    with open("/tmp/public.json", "w") as f:
        json.dump(public, f)

    result = subprocess.run(
        ["snarkjs", "groth16", "verify", VERIFICATION_KEY_PATH, "/tmp/public.json", "/tmp/proof.json"],
        capture_output=True, text=True
    )
    print(result.stdout)

    if result.returncode == 0 and "OK!" in result.stdout:
        resp = make_response(jsonify({"valid": True}))
        resp.set_cookie("verified_age", "true", samesite="Lax")
        return resp
    else:
        return jsonify({"valid": False}), 400


@app.route("/verify_zkp_v2", methods=["POST"])
def verify_zkp_v2():
    data = request.json
    proof = data.get("proof")
    public = data.get("public")

    ca_bjj = requests.get("http://ca:8000/public_key_bjj").json()

    if str(public[0]) != str(ca_bjj["Ax"]) or str(public[1]) != str(ca_bjj["Ay"]):
        print("key mismatch")
        return jsonify({"valid": False}), 400

    required_threshold = 18
    if int(public[2]) != required_threshold:
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
    return """
    <!DOCTYPE html>
    <html>
    <body>
        <h1>Test page loaded</h1>
        <button id="trigger-vc-sd">Verify Age (Selective Disclosure)</button>
        <button id="trigger-vc-zkp">Verify Age (ZKP — hash preimage)</button>
        <button id="trigger-vc-zkp-v2">Verify Age (ZKP — unlinkable)</button>
        <div id="protected-content" style="display:none;">
            <h2>You are verified. Protected content visible.</h2>
        </div>


        <script>
        function getCookie(name) {
            return document.cookie.split('; ')
                .find(row => row.startsWith(name + '='))?.split('=')[1];
        }

        document.addEventListener("DOMContentLoaded", function() {
            if (getCookie("verified_age") === "true") {
                console.log("Already verified.");
                const protectedContent = document.getElementById("protected-content");
                if (protectedContent) protectedContent.style.display = "block";
            }
        });

        window.addEventListener("VCResponse", (ev) => {
            console.log("Site received VC response:", ev.detail);

            var method = ev.detail.method || "sd";
            var verifyEndpoint =
                method === "zkp_v2" ? "http://localhost:5000/verify_zkp_v2" :
                method === "zkp"    ? "http://localhost:5000/verify_zkp"    :
                                      "http://localhost:5000/verify";

            fetch(verifyEndpoint, {
                method: "POST",
                credentials: "include",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(ev.detail)
            })
            .then(res => res.json())
            .then(data => {
                console.log("Verification result:", data);
                if (data.valid) {
                    document.getElementById("protected-content").style.display = "block";
                }
            })
            .catch(err => console.error(err));
        });

        function triggerVC(method) {
            if (document.getElementById("vc-request")) return;
            const div = document.createElement("div");
            div.id = "vc-request";
            div.dataset.attribute = "age";
            div.dataset.method = method;
            document.body.appendChild(div);
        }

        document.getElementById("trigger-vc-sd").addEventListener("click", () => triggerVC("sd"));
        document.getElementById("trigger-vc-zkp").addEventListener("click", () => triggerVC("zkp"));
        document.getElementById("trigger-vc-zkp-v2").addEventListener("click", () => triggerVC("zkp_v2"));
        </script>
    </body>
    </html>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)