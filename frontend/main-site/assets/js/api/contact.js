// contact.js
export function initContactForm() {
    const contactForm = document.getElementById("contactForm");
    if (!contactForm) return;

    const responseMessageId = "responseMessage";
    let responseMessage = document.getElementById(responseMessageId);

    if (!responseMessage) {
        responseMessage = document.createElement("div");
        responseMessage.id = responseMessageId;
        contactForm.parentNode.insertBefore(responseMessage, contactForm.nextSibling);
    }

    contactForm.addEventListener("submit", async function(e) {
        e.preventDefault();

        const data = {
            name: document.getElementById("name").value,
            email: document.getElementById("email").value,
            subject: document.getElementById("subject").value,
            message: document.getElementById("message").value,
        };

        try {
            const response = await fetch("http://127.0.0.1:8000/api/contact/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            });

            if (response.ok) {
                responseMessage.innerHTML = '<div class="alert alert-success mt-3">✅ Message sent successfully!</div>';
                contactForm.reset();
            } else {
                const error = await response.json();
                responseMessage.innerHTML = '<div class="alert alert-danger mt-3">❌ Error: ' + JSON.stringify(error) + '</div>';
            }
        } catch (err) {
            responseMessage.innerHTML = '<div class="alert alert-warning mt-3">⚠️ Failed to connect to server.</div>';
        }
    });
}
