console.log("VC Extension Loaded");

var alreadyStarted = false;

browser.runtime.onMessage.addListener(function(message) {
    if (message.type === "vc_response") {
        console.log("Got response from wallet!");

        var responseData = JSON.stringify(message.payload);
        var scriptTag = document.createElement("script");
        scriptTag.text = "window.dispatchEvent(new CustomEvent('VCResponse', { detail: " + responseData + " }));";
        document.head.appendChild(scriptTag);
    }
});

function checkRequest() {
    if (alreadyStarted === true) {
        return;
    }

    var requestDiv = document.getElementById("vc-request");

    if (requestDiv != null) {
        alreadyStarted = true;

        var method = requestDiv.dataset.method || "sd";
        var methodLabel =
            method === "zkp_v2" ? "Zero-Knowledge Proof (Unlinkable)" :
            method === "zkp"    ? "Zero-Knowledge Proof" :
                                  "Selective Disclosure";
        var confirmCheck = confirm("This site wants your VC (" + methodLabel + "). Allow?");

        if (confirmCheck == true) {
            console.log("User clicked OK, method:", method);

            browser.runtime.sendMessage({
                type: "vc_request_detected",
                attributes: {
                    attribute: requestDiv.dataset.attribute,
                    method: method
                }
            });
        } else {
            console.log("User cancelled.");
            alreadyStarted = false;
            requestDiv.remove();
        }
    }
}

setInterval(checkRequest, 250);