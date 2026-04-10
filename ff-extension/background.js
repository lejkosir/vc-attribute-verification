console.log("Background.js loaded");

browser.runtime.onMessage.addListener(function(request, sender, sendResponse) {
    console.log("Background received message:", request);

    if (request.type === "vc_request_detected") {
        var method = request.attributes.method || "sd";
        var endpoint = method === "zkp"
            ? "http://localhost:8001/disclose_zkp"
            : "http://localhost:8001/disclose";

        console.log("Contacting Python Wallet at", endpoint);

        fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                attribute: request.attributes.attribute
            })
        })
        .then(function(res) {
            return res.json();
        })
        .then(function(data) {
            console.log("Wallet responded with:", data);
            data.method = method;

            if (sender.tab && sender.tab.id) {
                browser.tabs.sendMessage(sender.tab.id, {
                    type: "vc_response",
                    payload: data
                });
            }
        })
        .catch(function(err) {
            console.error("Fetch failed. Is the Python Wallet running?", err);
        });

        return true;
    }
});