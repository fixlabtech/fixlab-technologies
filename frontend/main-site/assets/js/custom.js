document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("courseRegistrationForm");

  // Paystack Links
  const paystackLinks = {
    onsite: "https://paystack.shop/pay/fixlab_onsite_enroll",
    virtual: "https://paystack.shop/pay/fixlab_virtual_enroll"
  };

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const name = document.getElementById("name").value.trim();
    const email = document.getElementById("email").value.trim().toLowerCase();
    const phone = document.getElementById("phone").value.trim();
    const mode = document.getElementById("mode").value;
    const course = document.getElementById("course").value;
    const payment = document.getElementById("paymentOption").value;

    if (!name || !email || !phone || !mode || !course || !payment) {
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

    try {
      // Check if email already exists
      const checkResponse = await fetch(
        `https://www.services.fixlabtech.com/api/check-user?email=${encodeURIComponent(email)}`
      );
      const checkResult = await checkResponse.json();

      if (checkResult.exists) {
        Swal.fire({
          icon: "error",
          title: "Email Already Exists",
          text: "This email is already registered. Please use the 'Already Registered' option.",
          timer: 3000,
          timerProgressBar: true,
          showConfirmButton: false
        });
        return;
      }

      // ✅ Send registration data to backend
      const backendResponse = await fetch(
        "https://www.services.fixlabtech.com/api/register",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            full_name: name,
            email: email,
            phone: phone,
            course: course,
            mode_of_learning: mode,
            payment_option: payment,
            action: "newRegistration"
          })
        }
      );

      const backendResult = await backendResponse.json();

      if (!backendResult.success) {
        Swal.fire({
          icon: "error",
          title: "Registration Failed",
          text: backendResult.message || "Please try again later.",
          timer: 3000,
          timerProgressBar: true,
          showConfirmButton: false
        });
        return;
      }

      // ✅ Proceed to payment after backend registration
      Swal.fire({
        title: "Confirm Registration",
        html: `
          <p><b>Name:</b> ${name}</p>
          <p><b>Email:</b> ${email}</p>
          <p><b>Course:</b> ${course}</p>
          <p><b>Mode:</b> ${mode}</p>
          <p><b>Payment:</b> ${payment}</p>
          <p>Do you want to proceed to payment?</p>
        `,
        icon: "question",
        showCancelButton: true,
        confirmButtonText: "Yes, Proceed",
        cancelButtonText: "Cancel",
        confirmButtonColor: "#1d4ed8"
      }).then((result) => {
        if (result.isConfirmed) {
          const payLink = paystackLinks[mode] || "";
          if (!payLink) {
            Swal.fire("Error", "Invalid mode selected. Please try again.", "error");
            return;
          }
          window.location.href = payLink;
        }
      });

    } catch (error) {
      Swal.fire({
        icon: "error",
        title: "Server Error",
        text: "Unable to complete registration at the moment. Please try again later.",
        timer: 3000,
        timerProgressBar: true,
        showConfirmButton: false
      });
      console.error(error);
    }
  });
});
