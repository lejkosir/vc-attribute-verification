from flask import Flask, request, jsonify, make_response
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
    return """
    <!DOCTYPE html>
    <html>
    <body>
        <h1>LOADED</h1>
        <button id="trigger-vc-zkp-v2">Verify Age (ZKPv2)</button>
        <div id="protected-content" style="display:none;">
            <h2>VERIFIED</h2>
        </div>

        <script>
        function getCookie(name) {
            return document.cookie.split('; ')
                .find(row => row.startsWith(name + '='))?.split('=')[1];
        }

        document.addEventListener("DOMContentLoaded", function() {
            if (getCookie("verified_age") === "true") {
                document.getElementById("protected-content").style.display = "block";
            }
        });

        window.addEventListener("VCResponse", (ev) => {
            console.log("VC response:", ev.detail);

            fetch("http://localhost:5000/verify_zkp_v2", {
                method: "POST",
                credentials: "include",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(ev.detail)
            })
            .then(res => res.json())
            .then(data => {
                if (data.valid) {
                    document.getElementById("protected-content").style.display = "block";
                }
            })
            .catch(err => console.error(err));
        });

        function triggerVC() {
            if (document.getElementById("vc-request")) return;
            const div = document.createElement("div");
            div.id = "vc-request";
            div.dataset.attribute = "age";
            div.dataset.method = "zkp_v2";
            document.body.appendChild(div);
        }

        document.getElementById("trigger-vc-zkp-v2").addEventListener("click", triggerVC);
        </script>
    </body>
    </html>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
