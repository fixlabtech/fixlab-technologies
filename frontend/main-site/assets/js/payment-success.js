document.addEventListener("DOMContentLoaded", async () => {
  const urlParams = new URLSearchParams(window.location.search);
  const reference = urlParams.get("reference");
  const registrationId = urlParams.get("registration_id"); // ✅ Backend ID passed in URL

  if (!reference || !registrationId) {
    Swal.fire("Error", "Missing payment reference or registration ID.", "error").then(() => {
      window.location.href = "register.html";
    });
    return;
  }

  try {
    const response = await fetch("https://www.services.fixlabtech.com/api/verify-payment/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        reference: reference,
        registration_id: registrationId
      })
    });

    const result = await response.json();

    if (response.ok && result.success) {
      Swal.fire({
        icon: "success",
        title: "Payment Verified & Registration Complete 🎉",
        text: result.message || "Thank you! Your registration is now complete.",
        confirmButtonText: "Return Home",
        confirmButtonColor: "#1d4ed8"
      }).then(() => {
        window.location.href = "index.html";
      });
    } else {
      Swal.fire("Payment Failed", result.message || "Payment verification failed.", "error");
    }
  } catch (err) {
    Swal.fire("Server Error", "Could not connect to server. Try again later.", "error");
  }
});
