console.log("background.js loaded, snarkjs:", typeof snarkjs);

var CA_URL = "http://localhost:8000";

browser.runtime.onMessage.addListener(function(request, sender, sendResponse) {

    if (request.type === "vc_request_detected") {
        console.log("got vc request");
        console.log(request);
        const challenge = request.attributes.challenge;
        const MIN_AGE = request.attributes.min_age;
        console.log(challenge);
        console.log(MIN_AGE);
        browser.storage.local.get("credentials").then(function(result) {
            var creds = result.credentials || [];

            if (creds.length > 0) {
                console.log("VC contents:");
                console.log(JSON.stringify(creds[0].vc, null, 2));
            }

            if (creds.length == 0) {
                browser.tabs.sendMessage(sender.tab.id, {
                    type: "vc_response",
                    payload: { error: "no credentials stored" }
                });
                return;
            }

            var entry = creds[0];
            var vc = entry.vc;
            var priv = entry.private;
            var sig = vc.proof.proofValue;
            var pk = vc.proof.publicKey;

            var currentDate = Math.floor(Date.now() / 1000);

            if (currentDate - parseInt(priv.birthdate_int) < MIN_AGE) {
                browser.tabs.sendMessage(sender.tab.id, {
                    type: "vc_response",
                    payload: { error: "age below minimum" }
                });
                return;
            }

            var inputs = {
                birthdate: priv.birthdate_int.toString(),
                salt: priv.salt.toString(),
                R8x: sig.R8x.toString(),
                R8y: sig.R8y.toString(),
                S: sig.S.toString(),
                Ax: pk.Ax.toString(),
                Ay: pk.Ay.toString(),
                challenge: challenge,
                challenge_pub: challenge,
                Ax_pub: pk.Ax.toString(),
                Ay_pub: pk.Ay.toString(),
                currentDate: currentDate.toString(),
                minAge: MIN_AGE.toString()
            };

            var wasmUrl = browser.runtime.getURL("assets/age_check_v2.wasm");
            var zkeyUrl = browser.runtime.getURL("assets/age_check_v2_final.zkey");

            console.log("generating proof...");

            snarkjs.groth16.fullProve(inputs, wasmUrl, zkeyUrl).then(function(res) {
                console.log("proof done!");
                browser.tabs.sendMessage(sender.tab.id, {
                    type: "vc_response",
                    payload: { proof: res.proof, public: res.publicSignals, method: "zkp_v2" }
                });
            }).catch(function(err) {
                console.log("proof failed", err);
                browser.tabs.sendMessage(sender.tab.id, {
                    type: "vc_response",
                    payload: { error: "proof generation failed" }
                });
            });
        });

        return true;
    }

    if (request.type === "fetch_vc") {
        console.log("fetching vc from ca for", request.subject_id);

        fetch(CA_URL + "/issue_vc", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ subject_id: request.subject_id, birthdate: request.birthdate })
        })
        .then(function(res) { return res.json(); })
        .then(function(data) {
            if (data.error) {
                sendResponse({ error: data.error });
                return;
            }
            browser.storage.local.get("credentials").then(function(result) {
                var creds = result.credentials || [];
                creds.push({ vc: data.vc, private: data.private });
                browser.storage.local.set({ credentials: creds }).then(function() {
                    sendResponse({ ok: true });
                });
            });
        })
        .catch(function(err) {
            console.log("fetch vc error", err);
            sendResponse({ error: err.message });
        });

        return true;
    }

    if (request.type === "list_credentials") {
        browser.storage.local.get("credentials").then(function(result) {
            sendResponse(result.credentials || []);
        });
        return true;
    }

    if (request.type === "remove_credential") {
        browser.storage.local.get("credentials").then(function(result) {
            var creds = result.credentials || [];
            creds.splice(request.index, 1);
            browser.storage.local.set({ credentials: creds }).then(function() {
                sendResponse({ ok: true });
            });
        });
        return true;
    }
});
