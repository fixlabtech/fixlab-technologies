// main.js
document.addEventListener("DOMContentLoaded", () => {
  // Select all register buttons
  const registerButtons = document.querySelectorAll(".button-header");

  registerButtons.forEach((registerBtn) => {
    registerBtn.addEventListener("click", (e) => {
      e.preventDefault(); // Prevent default link behavior

      // Show SweetAlert2 prompt
      Swal.fire({
        title: "Welcome!",
        text: "Are you a new student or already registered?",
        icon: "question",
        showCancelButton: true,
        showDenyButton: true,
        confirmButtonText: "New Student",
        denyButtonText: "Already Registered",
        cancelButtonText: "Cancel",
      }).then((result) => {
        if (result.isConfirmed) {
          // New User selected
          window.location.href = "new.html";
        } else if (result.isDenied) {
          // Already Registered selected
          window.location.href = "user.html";
        }
        // Cancel does nothing
      });
    });
  });
});
