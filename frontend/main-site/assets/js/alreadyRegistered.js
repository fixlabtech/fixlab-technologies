// ✅ Paystack Links
const paystackLinks = {
    installment: "https://paystack.shop/pay/fixlab_install_enroll",
    full: "https://paystack.shop/pay/fixlab_full_enroll",
    newCourseFull: "https://paystack.shop/pay/fixlab_full_enroll",
    newCourseInstallment: "https://paystack.shop/pay/fixlab_install_enroll"
};

// ✅ Toggle new course fields
document.getElementById("actionSelect").addEventListener("change", function () {
    const newCourseFields = document.getElementById("newCourseFields");
    newCourseFields.style.display = this.value === "newCourse" ? "block" : "none";
});

// ✅ Handle form submission
document.getElementById("alreadyRegisteredForm").addEventListener("submit", async function (e) {
    e.preventDefault();

    // ✅ Get values **freshly at submission**
    const email = document.getElementById("existingEmail").value.trim().toLowerCase();
    const action = document.getElementById("actionSelect").value;
    const courseSelect = document.getElementById("newCourse"); // <select> element
    const modeSelect = document.getElementById("newMode"); // <select> element
    const paymentOptionSelect = document.getElementById("newPaymentOption"); // <select> element
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
        // ✅ Check backend for user info
        const checkResponse = await fetch(`https://www.services.fixlabtech.com/api/check-user?email=${encodeURIComponent(email)}`);
        const data = await checkResponse.json();

        if (!data.exists) {
            Swal.fire("Error", "User not found. Please register first.", "error");
            return;
        }

        let courseToUse = course;
        let modeToUse = mode;

        // ✅ Installment: override course/mode from backend
        if (action === "installment") {
            if (!data.course) {
                Swal.fire("Error", "You are not registered for any course. Please register first before paying an installment.", "error");
                return;
            }
            if (data.payment_status === "completed") {
                Swal.fire("Error", "Your payment for this course is already completed.", "error");
                return;
            }
            courseToUse = data.course;
            modeToUse = data.mode_of_learning;
        }

        // ✅ Prevent duplicate new course registration
        if (action === "newCourse" && data.course === course) {
            Swal.fire("Error", "You are already registered for this course. Choose a different course.", "error");
            return;
        }

        // ✅ Save registration data
        localStorage.setItem("registrationData", JSON.stringify({
            email,
            action,
            course: courseToUse,
            mode: modeToUse,
            payment_option: paymentOption,
            message
        }));

        // ✅ Determine Paystack link
        let payLink = "";
        if (mode === "virtual") {
            payLink = paystackLinks.installment;
        } else if (mode === "onsite") {
            payLink = paystackLinks.full;
        } else if (action === "newCourse") {
            payLink = mode === "onsite" ? paystackLinks.newCourseFull : paystackLinks.newCourseInstallment;
        }

        // ✅ Confirmation modal
        Swal.fire({
            title: "Proceed to Payment?",
            html: `
                <p><b>Email:</b> ${email}</p>
                <p><b>Course:</b> ${courseToUse}</p>
                <p><b>Mode:</b> ${modeToUse}</p>
                <p><b>Payment:</b> ${paymentOption}</p>
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
        console.error("API Error:", err);
        Swal.fire("Error", "Something went wrong. Try again later.", "error");
    }
});
