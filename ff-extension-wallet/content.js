var started = false;

browser.runtime.onMessage.addListener(function(message) {
    if (message.type === "vc_response") {
        if (message.payload.error) {
            alert("Wallet error: " + message.payload.error);
            started = false;
            return;
        }

        var s = document.createElement("script");
        s.text = "window.dispatchEvent(new CustomEvent('VCResponse', { detail: " + JSON.stringify(message.payload) + " }));";
        document.head.appendChild(s);
    }
});

function checkForRequest() {
    if (started) return;

    var div = document.getElementById("vc-request");
    if (div == null) return;

    started = true;

    var ok = confirm("This site is requesting age verification. Generate a ZK proof?");

    if (ok) {
        browser.runtime.sendMessage({
            type: "vc_request_detected",
            attributes: { attribute: div.dataset.attribute }
        });
    } else {
        started = false;
        div.remove();
    }
}

setInterval(checkForRequest, 250);
