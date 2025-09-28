document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("alreadyRegisteredForm");
  const actionSelect = document.getElementById("actionSelect");
  const newCourseFields = document.getElementById("newCourseFields");

  // Toggle extra fields when action is "newCourse"
  actionSelect.addEventListener("change", () => {
    if (actionSelect.value === "newCourse") {
      newCourseFields.style.display = "block";
    } else {
      newCourseFields.style.display = "none";
    }
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = document.getElementById("existingEmail").value.trim().toLowerCase();
    const action = actionSelect.value;
    const course = document.getElementById("newCourse")?.value || "";
    const mode_of_learning = document.getElementById("newMode")?.value || "";
    const payment_option = document.getElementById("newPaymentOption")?.value || "";
    const message = document.getElementById("message").value.trim();

    if (!email || !action) {
      Swal.fire("Error", "Please fill all required fields.", "error");
      return;
    }

    if (action === "newCourse" && (!course || !mode_of_learning || !payment_option)) {
      Swal.fire("Error", "Please fill all new course fields.", "error");
      return;
    }

    try {
      // Check if user exists
      const checkResponse = await fetch(
        `https://www.services.fixlabtech.com/api/check-user?email=${encodeURIComponent(email)}`
      );
      const userData = await checkResponse.json();

      if (!userData.exists) {
        Swal.fire("Error", "No user found with this email. Please register first.", "error");
        return;
      }

      // Action-specific checks
      if (action === "installment" && userData.payment_status === "completed") {
        Swal.fire("Info", "You have already completed payment for your course.", "info");
        return;
      }

      if (action === "newCourse" && userData.course === course && userData.mode_of_learning === mode_of_learning) {
        Swal.fire("Error", "You are already enrolled in this course & mode. Choose a different one.", "error");
        return;
      }

      // Prepare payload to send directly to backend
      const payload = {
        email,
        action,
        course,
        mode_of_learning,
        payment_option,
        message
      };

      const regResponse = await fetch("https://www.services.fixlabtech.com/api/registrations/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const regResult = await regResponse.json();

      if (!regResponse.ok || !regResult.success) {
        Swal.fire("Error", regResult.message || "Failed to register action.", "error");
        return;
      }

      // If newCourse, redirect to Paystack with registration_id and mode
      if (action === "newCourse") {
        const paystackLinks = {
          onsite: "https://paystack.shop/pay/fixlab_onsite_enroll",
          virtual: "https://paystack.shop/pay/fixlab_virtual_enroll"
        };

        const payLink = `${paystackLinks[mode_of_learning]}?registration_id=${regResult.registration_id}`;
        if (!payLink) {
          Swal.fire("Error", "Invalid mode selected. Please try again.", "error");
          return;
        }

        Swal.fire({
          title: "Confirm New Course Enrollment",
          html: `
            <p><b>Name:</b> ${userData.full_name}</p>
            <p><b>Email:</b> ${userData.email}</p>
            <p><b>New Course:</b> ${course}</p>
            <p><b>Mode:</b> ${mode_of_learning}</p>
            <p><b>Payment Option:</b> ${payment_option}</p>
            <p>Do you want to proceed to payment?</p>
          `,
          icon: "question",
          showCancelButton: true,
          confirmButtonText: "Yes, Proceed",
          cancelButtonText: "Cancel",
          confirmButtonColor: "#1d4ed8"
        }).then((result) => {
          if (result.isConfirmed) {
            window.location.href = payLink;
          }
        });
      } else {
        // Non-payment actions (installment) — payment_success page
        Swal.fire({
          icon: "success",
          title: "Action Recorded",
          text: regResult.message || "Your request has been processed.",
          confirmButtonText: "Return Home",
          confirmButtonColor: "#1d4ed8"
        }).then(() => {
          window.location.href = "index.html";
        });
      }

    } catch (err) {
      Swal.fire("Server Error", "Could not connect to server. Try again later.", "error");
    }
  });
});            window.location.href = "payment-success.html"; // Go to success page for non-payment actions
          }
        }
      });
    } catch (err) {
      Swal.fire("Error", "Could not connect to server. Try again later.", "error");
    }

  });
});
