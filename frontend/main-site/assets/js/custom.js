document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("courseRegistrationForm");

  // Email validation
  function isValidEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
  }

  // Phone validation
  function isValidPhone(phone) {
    const re = /^\+?\d{7,15}$/;
    return re.test(phone);
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    // Collect fields
    const name = document.getElementById("name").value.trim();
    const email = document.getElementById("email").value.trim().toLowerCase();
    const phone = document.getElementById("phone").value.trim();
    const gender = document.getElementById("gender").value;
    const address = document.getElementById("address").value.trim();
    const occupation = document.getElementById("occupation").value.trim();
    const course = document.getElementById("course").value;
    const message = document.getElementById("message").value.trim();

    // Validate required fields
    if (!name || !email || !phone || !gender || !address || !occupation || !course) {
      Swal.fire({
        icon: "warning",
        title: "Missing Fields",
        text: "Please fill in all required fields!",
        timer: 3000,
        timerProgressBar: true,
        showConfirmButton: false
      });
      return;
    }

    // Validate email
    if (!isValidEmail(email)) {
      Swal.fire({
        icon: "error",
        title: "Invalid Email",
        text: "Please enter a valid email address.",
        timer: 3000,
        timerProgressBar: true,
        showConfirmButton: false
      });
      return;
    }

    // Validate phone
    if (!isValidPhone(phone)) {
      Swal.fire({
        icon: "error",
        title: "Invalid Phone Number",
        text: "Please enter a valid phone number (digits only, min 7 and max 15).",
        timer: 3000,
        timerProgressBar: true,
        showConfirmButton: false
      });
      return;
    }

    // ✅ Step 1: Confirm registration before sending to backend
    const confirmResult = await Swal.fire({
      title: "Confirm Registration",
      html: `
        <p><b>Name:</b> ${name}</p>
        <p><b>Email:</b> ${email}</p>
        <p><b>Course:</b> ${course}</p>
        <p>Do you want to proceed to payment?</p>
      `,
      icon: "question",
      showCancelButton: true,
      confirmButtonText: "Yes, Proceed",
      cancelButtonText: "Cancel",
      confirmButtonColor: "#1d4ed8"
    });

    if (!confirmResult.isConfirmed) return; // Stop if user cancels

    try {
      // Step 2: Check if user already registered
      const checkResponse = await fetch(
        `https://www.services.fixlabtech.com/api/check-user?email=${encodeURIComponent(email)}`
      );
      if (!checkResponse.ok) throw new Error("Failed to check user");
      const checkResult = await checkResponse.json();

      if (checkResult.exists) {
        Swal.fire({
          icon: "info",
          title: "Pending or Existing Registration",
          text: "You already have a registration. Please use the 'Already Registered' option to continue.",
          confirmButtonText: "Go to Already Registered",
          confirmButtonColor: "#1d4ed8"
        }).then(() => {
          window.location.href = "/user"; // Adjust route
        });
        return;
      }

      // Step 3: Send registration to backend
      const backendResponse = await fetch(
        "https://www.services.fixlabtech.com/api/registrations",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            full_name: name,
            email: email,
            phone: phone,
            gender: gender,
            address: address,
            occupation: occupation,
            course: course,
            message: message,
            action: "newRegistration"
          })
        }
      );

      if (!backendResponse.ok) throw new Error("Failed to connect to server");

      const backendResult = await backendResponse.json();

      if (!backendResult.success) {
        Swal.fire({
          icon: "error",
          title: "Registration Failed",
          text: backendResult.message || "Please try again later.",
          confirmButtonColor: "#dc2626"
        });
        return;
      }

      // Step 4: Redirect to Paystack
      const payLink = backendResult.payment_url;
      if (!payLink) throw new Error("Payment link not provided by backend");

      window.location.href = payLink; // Redirect user

    } catch (error) {
      Swal.fire({
        icon: "error",
        title: "Network/Server Error",
        text: error.message || "Unable to complete registration at the moment.",
        confirmButtonColor: "#dc2626"
      });
      console.error("Registration Error:", error);
    }
  });
});
