document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("courseRegistrationForm");
    const modeSelect = document.getElementById("mode");
    const courseSelect = document.getElementById("course");
    const paymentSelect = document.getElementById("paymentOption");

    const courses = {
        online: [
            { name: "Cybersecurity Online", fullPrice: "₦50,000", installmentPrice: "₦20,000" },
            { name: "Python Programming Online", fullPrice: "₦40,000", installmentPrice: "₦15,000" },
            { name: "Hardware Engineering Online", fullPrice: "₦60,000", installmentPrice: "₦25,000" },
            { name: "Multimedia Technology Online", fullPrice: "₦45,000", installmentPrice: "₦18,000" }
        ],
        offline: [
            { name: "Cybersecurity Offline", fullPrice: "₦70,000", installmentPrice: "₦30,000" },
            { name: "Python Programming Offline", fullPrice: "₦60,000", installmentPrice: "₦25,000" },
            { name: "Hardware Engineering Offline", fullPrice: "₦80,000", installmentPrice: "₦35,000" },
            { name: "Multimedia Technology Offline", fullPrice: "₦65,000", installmentPrice: "₦28,000" }
        ]
    };

    // Update courses when mode changes
    modeSelect.addEventListener("change", () => {
        const selectedMode = modeSelect.value;
        courseSelect.innerHTML = '<option value="">-- Choose a Course --</option>';

        if (courses[selectedMode]) {
            courses[selectedMode].forEach(c => {
                const option = document.createElement("option");
                option.value = c.name;
                option.textContent = `${c.name} - Full: ${c.fullPrice} | Installment: ${c.installmentPrice}`;
                courseSelect.appendChild(option);
            });
        }
    });

    // Add focus effect
    document.querySelectorAll("input, select, textarea").forEach(el => {
        el.addEventListener("focus", () => {
            el.style.borderColor = "#007bff";
            el.style.boxShadow = "0 0 5px rgba(0,123,255,0.5)";
        });
        el.addEventListener("blur", () => {
            el.style.borderColor = "#ccc";
            el.style.boxShadow = "none";
        });
    });

    // Handle form submit
    form.addEventListener("submit", e => {
        e.preventDefault();

        const data = {
            name: document.getElementById("name").value.trim(),
            dob: document.getElementById("dob") ? document.getElementById("dob").value : "",
            email: document.getElementById("email").value.trim(),
            phone: document.getElementById("phone").value.trim(),
            mode: modeSelect.value,
            course: courseSelect.value,
            paymentOption: paymentSelect.value,
            message: document.getElementById("message").value.trim()
        };

        // Validation
        if (!data.name || !data.email || !data.phone || !data.mode || !data.course || !data.paymentOption) {
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

            // Save registration data temporarily
            localStorage.setItem("registrationData", JSON.stringify(data));

            // Redirect user to your Paystack hosted payment page
            // Replace with your Paystack link
            window.location.href = "https://paystack.shop/pay/fixlab-enroll";
        // Send to backend
        // fetch("http://127.0.0.1:8000/api/register/", {
        //     method: "POST",
        //     headers: { "Content-Type": "application/json" },
        //     body: JSON.stringify(data)
        // })
        // .then(res => res.json())
        // .then(response => {
        //     Swal.fire({
        //         icon: "success",
        //         title: "Registration Successful!",
        //         text: "Redirecting to payment...",
        //         timer: 2000,
        //         showConfirmButton: false
        //     });
        //     form.reset();
        //     setTimeout(() => {
        //         window.open(paymentLink, "_blank");
        //     }, 2000);
        // })
        // .catch(error => {
        //     Swal.fire({
        //         icon: "error",
        //         title: "Registration Failed",
        //         text: "Could not connect to backend or an error occurred."
        //     });
        //     console.error("Registration error:", error);
        // });
    });
});