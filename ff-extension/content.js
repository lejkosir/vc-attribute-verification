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

        var confirmCheck = confirm("This site wants your VC. Allow?");
        if (confirmCheck == true) {
            console.log("User clicked OK");

            var simpleAttributes = {
                attribute: requestDiv.dataset.attribute
            };

            browser.runtime.sendMessage({
                type: "vc_request_detected",
                attributes: simpleAttributes
            });
        } else {
            console.log("User cancelled.");
            alreadyStarted = false;
            requestDiv.remove();
        }
    }
}

setInterval(checkRequest, 250);