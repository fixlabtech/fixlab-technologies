// Already Registered Form
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("alreadyRegisteredForm");
  const actionSelect = document.getElementById("actionSelect");
  const newCourseFields = document.getElementById("newCourseFields");

  // ✅ Toggle extra fields when action is "newCourse"
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
    const mode = document.getElementById("newMode")?.value || "";
    const paymentOption = document.getElementById("newPaymentOption")?.value || "";
    const message = document.getElementById("message").value.trim();

    if (!email || !action) {
      Swal.fire("Error", "Please fill all required fields.", "error");
      return;
    }

    if (action === "newCourse" && (!course || !mode || !paymentOption)) {
      Swal.fire("Error", "Please fill all new course fields.", "error");
      return;
    }

    try {
      // ✅ Check if user exists
      const checkResponse = await fetch(
        `https://www.services.fixlabtech.com/api/check-user?email=${encodeURIComponent(email)}`
      );
      const data = await checkResponse.json();

      // ❌ User not found
      if (!data.exists) {
        Swal.fire("Error", "No user found with this email. Please register first.", "error");
        return;
      }

      // ✅ Action-specific checks
      if (action === "installment") {
        if (data.payment_status === "completed") {
          Swal.fire("Info", "You have already completed payment for your course.", "info");
          return;
        }
      }

      if (action === "newCourse") {
        if (data.course === course && data.mode_of_learning === mode) {
          Swal.fire("Error", "You are already enrolled in this course & mode. Choose a different one.", "error");
          return;
        }
      }

      // ✅ Prepare registrationData for success.js
      localStorage.setItem(
        "registrationData",
        JSON.stringify({
          email,
          action,
          course,
          mode,
          payment_option: paymentOption,
          message
        })
      );

      // ✅ Payment link by mode
      const paystackLinks = {
        onsite: "https://paystack.shop/pay/fixlab_onsite_enroll",
        virtual: "https://paystack.shop/pay/fixlab_virtual_enroll"
      };
      const payLink = paystackLinks[mode] || "";

      if (!payLink && action === "newCourse") {
        Swal.fire("Error", "Invalid mode selected. Please try again.", "error");
        return;
      }

      // ✅ Confirmation modal (fix: show selected course if newCourse, otherwise current one)
      Swal.fire({
        title: "Confirm Action",
        html: `
          <p><b>Name:</b> ${data.full_name}</p>
          <p><b>Email:</b> ${data.email}</p>
          <p><b>Course:</b> ${action === "newCourse" ? course : data.course}</p>
          <p><b>Selected Action:</b> ${action}</p>
          ${action === "newCourse" ? `
            <p><b>Mode:</b> ${mode}</p>
            <p><b>Payment:</b> ${paymentOption}</p>` : ""}
        `,
        icon: "question",
        showCancelButton: true,
        confirmButtonText: "Proceed",
        cancelButtonText: "Cancel",
        confirmButtonColor: "#1d4ed8"
      }).then((result) => {
        if (result.isConfirmed) {
          if (action === "newCourse") {
            window.location.href = payLink; // Redirect to Paystack
          } else {
            window.location.href = "payment-success.html"; // Go to success page for non-payment actions
          }
        }
      });
    } catch (err) {
      Swal.fire("Error", "Could not connect to server. Try again later.", "error");
    }
  });
});          }
        }
      });
    } catch (err) {
      Swal.fire("Error", "Could not connect to server. Try again later.", "error");
    }
  });
});
