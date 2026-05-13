function showCredentials() {
    browser.runtime.sendMessage({ type: "list_credentials" }).then(function(creds) {
        var list = document.getElementById("cred-list");
        list.innerHTML = "";

        if (creds.length == 0) {
            list.innerHTML = "<p>No credentials stored.</p>";
            return;
        }

        for (var i = 0; i < creds.length; i++) {
            var vc = creds[i].vc;

            var div = document.createElement("div");
            div.style.border = "1px solid #ccc";
            div.style.padding = "6px";
            div.style.marginBottom = "6px";
            div.style.fontSize = "12px";
            div.style.wordBreak = "break-all";

            div.innerHTML = "<b>ID:</b> " + vc.id + "<br><b>Valid from:</b> " + vc.validFrom;

            var btn = document.createElement("button");
            btn.textContent = "Remove";
            btn.dataset.index = i;
            btn.style.marginTop = "4px";
            btn.addEventListener("click", function() {
                var idx = parseInt(this.dataset.index);
                browser.runtime.sendMessage({ type: "remove_credential", index: idx }).then(function() {
                    showCredentials();
                });
            });

            div.appendChild(document.createElement("br"));
            div.appendChild(btn);
            list.appendChild(div);
        }
    });
}

document.getElementById("fetch-form").addEventListener("submit", function(e) {
    e.preventDefault();

    var subjectId = document.getElementById("subject-id").value;
    var birthdate = document.getElementById("birthdate").value;
    var statusDiv = document.getElementById("status");

    statusDiv.textContent = "Requesting from CA...";
    statusDiv.style.color = "black";

    browser.runtime.sendMessage({ type: "fetch_vc", subject_id: subjectId, birthdate: birthdate }).then(function(resp) {
        if (resp.ok) {
            statusDiv.textContent = "Saved!";
            statusDiv.style.color = "green";
            document.getElementById("fetch-form").reset();
            showCredentials();
        } else {
            statusDiv.textContent = "Error: " + resp.error;
            statusDiv.style.color = "red";
        }
    });
});

showCredentials();
