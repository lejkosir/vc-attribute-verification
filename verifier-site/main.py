from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import base64
import hashlib
import json
import requests
import jwt
from cryptography.hazmat.primitives import serialization

app = Flask(__name__)
CORS(app, supports_credentials=True)


def b64url_decode(s):
    padding = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + padding)


@app.route("/verify", methods=["POST"])
def verify():
    data = request.json
    hashed_jwt = data["hashed_vc"]
    disclosures = data["disclosed"]

    # get key from our CA
    pub_pem = requests.get("http://ca:8000/public_key").json()["publicKeyPem"]
    public_key = serialization.load_pem_public_key(pub_pem.encode())

    # verify signature
    try:
        payload_json = jwt.decode(
            hashed_jwt,
            public_key,
            algorithms=["ES256"]
        )
    except Exception as e:
        return jsonify({"valid": False, "error": "invalid signature", "detail": str(e)}), 400


    claims = payload_json["vc"]["credentialSubject"]

    # verify each disclosed claim
    for key, value in disclosures.items():
        salt = base64.b64decode(claims[key]["salt"])
        combined = f"{key}:{value}".encode() + salt
        expected_hash = hashlib.sha256(combined).hexdigest()

        if expected_hash != claims[key]["hash"]:
            resp = make_response(jsonify({"valid": False}))
            return resp, 400

    # successful verification -> set cookie
    resp = make_response(jsonify({"valid": True}))
    resp.set_cookie(
        "verified_age",
        "true",
        httponly=False,
        samesite="Lax"
    )
    return resp


@app.route("/")
def home():
    return """
    <form method="POST" action="/verify">
      <textarea name="payload"></textarea>
      <button type="submit">Verify</button>
    </form>
    """


@app.route("/test")
def test():
    return """
    <!DOCTYPE html>
    <html>
    <body>
        <h1>Test page loaded</h1>
        <button id="trigger-vc">Verify Age</button>
        <div id="protected-content" style="display:none;">
            <h2>You are verified. Protected content visible.</h2>
        </div>


        <script>
        function getCookie(name) {
            return document.cookie.split('; ')
                .find(row => row.startsWith(name + '='))?.split('=')[1];
        }

        // If cookie exists → show protected content and hide request div
        document.addEventListener("DOMContentLoaded", function() {
            if (getCookie("verified_age") === "true") {
                console.log("Already verified.");
                
                const vcRequest = document.getElementById("vc-request");
                const protectedContent = document.getElementById("protected-content");
        
                if (vcRequest) vcRequest.style.display = "none";
                if (protectedContent) protectedContent.style.display = "block";
            }
        });

        window.addEventListener("VCResponse", (ev) => {
            console.log("Site received VC response:", ev.detail);

            fetch("http://localhost:5000/verify", {
                method: "POST",
                credentials: "include",   // store cookie
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(ev.detail)
            })
            .then(res => res.json())
            .then(data => {
                console.log("Verification result:", data);

                if (data.valid) {
                    document.getElementById("vc-request").style.display = "none";
                    document.getElementById("protected-content").style.display = "block";
                }
            })
            .catch(err => console.error(err));
        });
        document.getElementById("trigger-vc").addEventListener("click", () => {
            console.log("Adding VC request div...");
            const div = document.createElement("div");
            div.id = "vc-request";
            div.dataset.attribute = "age";
            document.body.appendChild(div);
        });
        </script>
    </body>
    </html>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)