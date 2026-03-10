console.log("[EXT] content.js loaded");

let requestSent = false;

// Fired when backend sends response back to content-script
browser.runtime.onMessage.addListener((msg) => {
    if (msg.type === "vc_response") {
        // Convert payload to JSON string so it can cross into page context
        const safe = JSON.stringify(msg.payload);

        const script = document.createElement("script");
        script.textContent = `
            window.dispatchEvent(new CustomEvent("VCResponse", { detail: ${safe} }));
        `;
        document.documentElement.appendChild(script);
        script.remove();
    }
});

function tryTriggerOnce() {
    if (requestSent) return;

    const div = document.getElementById("vc-request");
    if (!div) return;  // Nothing to do yet

    requestSent = true;  // Prevent double triggers

    console.log("[EXT] Triggering SD / ZKP request…");
    console.log("[EXT] Detected div with data:", div.dataset);
    // Send request to background (wallet request)
    browser.runtime.sendMessage({
        type: "vc_request_detected",
        attributes: { ...div.dataset }   // optional: <div data-*>
    });
    console.log("[EXT] Message sent to background, waiting for response…");
}

// Try immediately
tryTriggerOnce();

// Also try after DOM is ready
document.addEventListener("DOMContentLoaded", tryTriggerOnce);

// Final safety: observe dynamic pages
const observer = new MutationObserver(tryTriggerOnce);
observer.observe(document.body, { childList: true, subtree: true });