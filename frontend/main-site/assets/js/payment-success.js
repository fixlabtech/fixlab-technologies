document.addEventListener("DOMContentLoaded", async () => {
  const urlParams = new URLSearchParams(window.location.search);

  // ✅ Accept either 'reference' or 'trxref' from Paystack
  const reference = urlParams.get("reference") || urlParams.get("trxref");

  if (!reference) {
    Swal.fire("Error", "Missing payment reference.", "error").then(() => {
      window.location.href = "register.html";
    });
    return;
  }

  try {
    const response = await fetch("https://www.services.fixlabtech.com/api/verify-payment/", {
      method: "GET", // Use GET since your Django API expects reference in query params
      headers: { "Content-Type": "application/json" },
      // Send reference as query param
    });

    // Append reference as query string
    const verifyUrl = `https://www.services.fixlabtech.com/api/verify-payment/?reference=${reference}`;
    const verifyResponse = await fetch(verifyUrl);
    const result = await verifyResponse.json();

    if (verifyResponse.ok && result.success) {
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
