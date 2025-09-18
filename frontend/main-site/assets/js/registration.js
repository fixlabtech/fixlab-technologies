document.getElementById("courseRegistrationForm").addEventListener("submit", function(e){
  e.preventDefault();

  const data = {
    full_name: document.getElementById("name").value.trim(),
    email: document.getElementById("email").value.trim(),
    phone: document.getElementById("phone").value.trim(),
    course: document.getElementById("course").value,
    mode_of_learning: document.getElementById("mode").value,
    payment_option: document.getElementById("paymentOption").value
  };

  // Save registration data temporarily
  localStorage.setItem("registrationData", JSON.stringify(data));

  // Redirect user to your Paystack hosted payment page
  // Replace with your Paystack link
  window.location.href = "https://paystack.com/pay/YOUR-PAYMENT-LINK";
});
