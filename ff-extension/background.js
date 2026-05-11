console.log("Background.js loaded");

browser.runtime.onMessage.addListener(function(request, sender, sendResponse) {
    console.log("Background received message:", request);

    if (request.type === "vc_request_detected") {
        fetch("http://localhost:8501/disclose_zkp_v2", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ attribute: request.attributes.attribute })
        })
        .then(function(res) { return res.json(); })
        .then(function(data) {
            console.log("Wallet responded:", data);
            data.method = "zkp_v2";

            if (sender.tab && sender.tab.id) {
                browser.tabs.sendMessage(sender.tab.id, {
                    type: "vc_response",
                    payload: data
                });
            }
        })
        .catch(function(err) { console.error("wallet error", err); });

        return true;
    }
});
