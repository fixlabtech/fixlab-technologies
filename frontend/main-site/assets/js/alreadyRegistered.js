document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("alreadyRegisteredForm");
  const newCourseFields = document.getElementById("newCourseFields");
  const courseSelect = document.getElementById("newCourse");

  const toggleNewCourseFields = (show) => {
    newCourseFields.style.display = show ? "block" : "none";
  };

  const isValidEmail = (email) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = document.getElementById("existingEmail").value.trim().toLowerCase();

    if (!email) {
      Swal.fire("Error", "Please enter your email.", "error");
      return;
    }
    if (!isValidEmail(email)) {
      Swal.fire("Error", "Please enter a valid email address.", "error");
      return;
    }

    // Step 1: Check user
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
      }).then(() => window.location.href = "new-registration.html");
      return;
    }

    // Step 2: Check pending payment
    if (userData.payment_status === "pending" && userData.reference_no) {
      const continuePending = await Swal.fire({
        title: "Pending Payment Found",
        text: `You have a pending payment for ${userData.course}.`,
        icon: "question",
        showCancelButton: true,
        confirmButtonText: "Continue Payment",
        cancelButtonText: "Enroll New Course",
      });

      if (continuePending.isConfirmed) {
        window.location.href = `https://paystack.shop/pay/continue?reference=${userData.reference_no}`;
        return;
      }
    }

    // Step 3: Show new course select
    toggleNewCourseFields(true);

    // Step 4: Wait for user to select a course and submit
    form.addEventListener("submit", async (e2) => {
      e2.preventDefault();
      const course = courseSelect.value;

      if (!course) {
        Swal.fire("Error", "Please select a new course to enroll.", "error");
        return;
      }

      if (userData.course === course && userData.payment_status === "completed") {
        Swal.fire("Error", "You are already enrolled in this course.", "error");
        return;
      }

      // Send new course enrollment
      const payload = { email, action: "newCourse", course, message: "" };
      const regResponse = await fetch("https://www.services.fixlabtech.com/api/registrations/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const regResult = await regResponse.json();

      if (!regResponse.ok || !regResult.success) {
        Swal.fire("Error", regResult.message || "Failed to enroll in new course.", "error");
        return;
      }

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
          window.location.href = regResult.payment_url;
        }
      });
    }, { once: true }); // Only attach once
  });
});
