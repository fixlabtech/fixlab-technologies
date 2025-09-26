document.addEventListener("DOMContentLoaded", async () => {
  const urlParams = new URLSearchParams(window.location.search);
  const reference = urlParams.get("reference");

  if (!reference) {
    Swal.fire("Error", "No payment reference found.", "error").then(() => {
      window.location.href = "register.html";
    });
    return;
  }

  const registrationData = JSON.parse(localStorage.getItem("registrationData"));
  if (!registrationData) {
    Swal.fire("Error", "No registration found.", "error").then(() => {
      window.location.href = "register.html";
    });
    return;
  }

  // Add reference before sending
  registrationData.reference = reference;

  try {
    const response = await fetch("https://services.fixlabtech.com/api/verify-register/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(registrationData)
    });

    const result = await response.json();

    if (response.ok && result.success) {
      Swal.fire({
        icon: "success",
        title: "Registration Successful 🎉",
        text: result.message || "Your payment was verified and registration is complete!",
        confirmButtonText: "Return Home",
        confirmButtonColor: "#1d4ed8"
      }).then(() => {
        localStorage.removeItem("registrationData");
        window.location.href = "index.html";
      });
    } else {
      Swal.fire("Failed", result.message || "Payment verification failed.", "error");
    }
  } catch (err) {
    Swal.fire("Server Error", "Could not connect to server. Try again later.", "error");
  }
});
