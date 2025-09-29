document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("alreadyRegisteredForm");
  const newCourseFields = document.getElementById("newCourseFields");

  const toggleNewCourseFields = (show) => {
    newCourseFields.style.display = show ? "block" : "none";
  };

  const isValidEmail = (email) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = document.getElementById("existingEmail").value.trim().toLowerCase();
    const course = document.getElementById("newCourse")?.value || "";

    if (!email) {
      Swal.fire("Error", "Please enter your email.", "error");
      return;
    }
    if (!isValidEmail(email)) {
      Swal.fire("Error", "Please enter a valid email address.", "error");
      return;
    }

    try {
      // Step 1: Check if user exists
      const checkResponse = await fetch(
        `https://www.services.fixlabtech.com/api/check-user?email=${encodeURIComponent(email)}`
      );
      const userData = await checkResponse.json();

      if (!userData.exists) {
        Swal.fire({
          icon: "info",
          title: "Not Registered",
          text: "No user found with this email. You need to register first.",
          confirmButtonText: "Register Now",
          confirmButtonColor: "#1d4ed8",
        }).then(() => {
          window.location.href = "new-registration.html"; 
        });
        return;
      }

      // Step 2: Check pending payment
      if (userData.payment_status === "pending" && userData.reference_no) {
        const continuePending = await Swal.fire({
          title: "Pending Payment Found",
          text: `You have a pending payment for ${userData.course}. Do you want to continue it?`,
          icon: "question",
          showCancelButton: true,
          confirmButtonText: "Continue Payment",
          cancelButtonText: "Enroll New Course",
        });

        if (continuePending.isConfirmed) {
          // Continue pending payment using reference_no
          const payLink = `https://paystack.shop/pay/continue?reference=${userData.reference_no}`;
          window.location.href = payLink;
          return;
        }
      }

      // Step 3: Show new course fields
      toggleNewCourseFields(true);

      if (!course) {
        Swal.fire("Error", "Please select a new course to enroll.", "error");
        return;
      }

      // Step 4: Prevent duplicate enrollment
      if (userData.course === course && userData.payment_status === "completed") {
        Swal.fire(
          "Error",
          "You are already enrolled in this course. Choose a different course.",
          "error"
        );
        return;
      }

      // Step 5: Send enrollment request to backend
      const payload = {
        email,
        action: "newCourse",
        course,
        message: "",
      };

      const regResponse = await fetch(
        "https://www.services.fixlabtech.com/api/registrations/",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }
      );

      const regResult = await regResponse.json();

      if (!regResponse.ok || !regResult.success) {
        Swal.fire(
          "Error",
          regResult.message || "Failed to enroll in new course.",
          "error"
        );
        return;
      }

      // Step 6: Redirect to backend-provided payment URL for new course
      if (regResult.payment_url) {
        Swal.fire({
          title: "Confirm Enrollment",
          html: `<p><b>Name:</b> ${userData.full_name}</p>
                 <p><b>Email:</b> ${userData.email}</p>
                 <p><b>New Course:</b> ${course}</p>
                 <p>Do you want to proceed to payment?</p>`,
          icon: "question",
          showCancelButton: true,
          confirmButtonText: "Proceed to Payment",
          cancelButtonText: "Cancel",
          confirmButtonColor: "#1d4ed8",
        }).then((result) => {
          if (result.isConfirmed) {
            window.location.href = regResult.payment_url; // backend URL
          }
        });
      } else {
        Swal.fire(
          "Error",
          "No payment link received. Please try again.",
          "error"
        );
      }
    } catch (err) {
      Swal.fire(
        "Server Error",
        "Could not connect to server. Try again later.",
        "error"
      );
      console.error(err);
    }
  });
});
