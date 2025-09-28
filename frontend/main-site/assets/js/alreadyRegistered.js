// ✅ Paystack Links (based only on mode)
const paystackLinks = {
    onsite: "https://paystack.shop/pay/fixlab_onsite_enroll",
    virtual: "https://paystack.shop/pay/fixlab_virtual_enroll"
};

// ✅ Toggle new course fields
document.getElementById("actionSelect").addEventListener("change", function () {
    const newCourseFields = document.getElementById("newCourseFields");
    newCourseFields.style.display = this.value === "newCourse" ? "block" : "none";
});

// ✅ Handle form submission
document.getElementById("alreadyRegisteredForm").addEventListener("submit", async function (e) {
    e.preventDefault();

    // ✅ Get values freshly at submission
    const email = document.getElementById("existingEmail").value.trim().toLowerCase();
    const action = document.getElementById("actionSelect").value;
    const courseSelect = document.getElementById("newCourse");
    const modeSelect = document.getElementById("newMode");
    const paymentOptionSelect = document.getElementById("newPaymentOption");
    const message = document.getElementById("message").value.trim();

    const course = courseSelect ? courseSelect.value : "";
    const mode = modeSelect ? modeSelect.value : "";
    const paymentOption = paymentOptionSelect ? paymentOptionSelect.value : "";

    // ✅ Validate required fields
    if (!email || !action) {
        Swal.fire("Error", "Please fill all required fields.", "error");
        return;
    }

    if (action === "newCourse" && (!course || !mode || !paymentOption)) {
        Swal.fire("Error", "Please fill all new course fields.", "error");
        return;
    }

    try {
        // ✅ Check backend for user existence (use encodeURIComponent for mobile too)
        const checkResponse = await fetch(
            `https://www.services.fixlabtech.com/api/check-user?email=${encodeURIComponent(email)}`
        );
        const data = await checkResponse.json();

        if (!data.exists && action !== "newCourse") {
            Swal.fire("Error", "User not found. Please register first.", "error");
            return;
        }

        // ✅ Save for payment-success.js (so success page can complete registration)
        localStorage.setItem("registrationData", JSON.stringify({
            email,
            action,
            course,
            mode,
            payment_option: paymentOption,
            message
        }));

        // ✅ Determine Paystack link based on mode
        const payLink = paystackLinks[mode] || "";

        if (!payLink) {
            Swal.fire("Error", "Invalid mode selected. Please try again.", "error");
            return;
        }

        // ✅ Confirmation modal
        Swal.fire({
            title: "Proceed to Payment?",
            html: `
                <p><b>Email:</b> ${email}</p>
                <p><b>Course:</b> ${course || "N/A"}</p>
                <p><b>Mode:</b> ${mode || "N/A"}</p>
                <p><b>Payment:</b> ${paymentOption || "N/A"}</p>
                <p>You will be redirected to Paystack.</p>
            `,
            icon: "info",
            showCancelButton: true,
            confirmButtonText: "Proceed",
            cancelButtonText: "Cancel",
            confirmButtonColor: "#1d4ed8"
        }).then(result => {
            if (result.isConfirmed) {
                window.location.href = payLink;
            }
        });

    } catch (err) {
        Swal.fire("Error", "Something went wrong. Try again later.", "error");
    }
});
