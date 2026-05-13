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
    <head>
        <title>Verifier</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 30px; background: #fafafa; }
            h2 { color: #333; }
            button { background: #5b8dd9; color: white; border: none; padding: 8px 18px; font-size: 14px; cursor: pointer; border-radius: 4px; }
            button:hover { background: #3a6fbf; }
            #log { text-align: left; margin: 16px auto; max-width: 620px; background: white; border: 1px solid #ccc; padding: 10px; font-size: 13px; min-height: 50px; }
            #protected-content { display: none; margin-top: 16px; font-size: 18px; color: green; }
            .section-title { font-weight: bold; color: #555; margin-top: 8px; }
            .field { margin-left: 12px; word-break: break-all; color: #222; font-size: 12px; }
            .label { color: #888; }
        </style>
    </head>
    <body>
        <h2>Age Verifier</h2>
        <button id="trigger-vc-zkp-v2">Verify age</button>

        <div id="log"></div>
        <div id="protected-content">Verified</div>

        <script>
        function log(msg) {
            console.log(msg);
            document.getElementById("log").innerHTML += msg + "<br>";
        }

        function logProof(detail) {
            var p = detail.proof;
            var pub = detail.public;
            var log_div = document.getElementById("log");

            log_div.innerHTML += "<div class='section-title'>Proof (" + p.protocol + " over " + p.curve + ")</div>";
            log_div.innerHTML += "<div class='field'><span class='label'>pi_a: </span>" + p.pi_a[0] + "<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;" + p.pi_a[1] + "</div>";
            log_div.innerHTML += "<div class='field'><span class='label'>pi_b: </span>" + p.pi_b[0][0] + "<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;" + p.pi_b[0][1] + "<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;" + p.pi_b[1][0] + "<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;" + p.pi_b[1][1] + "</div>";
            log_div.innerHTML += "<div class='field'><span class='label'>pi_c: </span>" + p.pi_c[0] + "<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;" + p.pi_c[1] + "</div>";

            log_div.innerHTML += "<div class='section-title'>Public signals</div>";
            log_div.innerHTML += "<div class='field'><span class='label'>CA key Ax: </span>" + pub[0] + "</div>";
            log_div.innerHTML += "<div class='field'><span class='label'>CA key Ay: </span>" + pub[1] + "</div>";
            log_div.innerHTML += "<div class='field'><span class='label'>proof timestamp: </span>" + pub[2] + " (" + new Date(parseInt(pub[2]) * 1000).toLocaleString() + ")</div>";
            log_div.innerHTML += "<div class='field'><span class='label'>min age (seconds): </span>" + pub[3] + " (" + Math.round(parseInt(pub[3]) / 365 / 86400) + " years)</div>";
        }

        function getCookie(name) {
            var cookies = document.cookie.split('; ');
            for (var i = 0; i < cookies.length; i++) {
                if (cookies[i].startsWith(name + '=')) return cookies[i].split('=')[1];
            }
            return null;
        }

        if (getCookie("verified_age") === "true") {
            document.getElementById("protected-content").style.display = "block";
            log("already verified (cookie found)");
        }

        window.addEventListener("VCResponse", function(ev) {
            var detail = ev.detail;
            console.log("VC response:", detail);

            if (detail.error) {
                log("wallet error: " + detail.error);
                return;
            }

            log("received proof from wallet");
            logProof(detail);
            log("sending to verifier...");

            fetch("http://localhost:5000/verify_zkp_v2", {
                method: "POST",
                credentials: "include",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(detail)
            })
            .then(function(res) { return res.json(); })
            .then(function(data) {
                log("server response: " + JSON.stringify(data));
                if (data.valid) {
                    document.getElementById("protected-content").style.display = "block";
                }
            })
            .catch(function(err) {
                log("error: " + err.message);
            });
        });

        document.getElementById("trigger-vc-zkp-v2").addEventListener("click", function() {
            if (document.getElementById("vc-request")) return;
            document.getElementById("log").innerHTML = "";
            log("requesting proof from wallet...");
            var div = document.createElement("div");
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
