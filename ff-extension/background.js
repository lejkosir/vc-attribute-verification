console.log("Background.js loaded");

browser.runtime.onMessage.addListener(function(request, sender, sendResponse) {
    console.log("Background received message:", request);

    if (request.type === "vc_request_detected") {
        console.log("Contacting Python Wallet at localhost:8001...");

        fetch("http://localhost:8001/disclose", {
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