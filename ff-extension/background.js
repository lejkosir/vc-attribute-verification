console.log("[EXT] background.js loaded");

browser.runtime.onMessage.addListener(async (msg, sender) => {
    console.log("[EXT] Background received message:", msg, "from sender:", sender);
    if (msg.type === "vc_request_detected") {
        console.log("[EXT] Background received VC request:", msg);

        // Call the wallet
        const response = await fetch("http://localhost:8001/disclose", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(msg.attributes || {})
        });

        const payload = await response.json();

        console.log("[EXT] Background sending VC response back to content-script:", payload);

        browser.tabs.sendMessage(sender.tab.id, {
            type: "vc_response",
            payload: payload
        });
    }
});