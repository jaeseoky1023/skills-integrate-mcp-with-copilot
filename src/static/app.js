document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const loginForm = document.getElementById("login-form");
  const loginEmail = document.getElementById("login-email");
  const loginPassword = document.getElementById("login-password");
  const authStatus = document.getElementById("auth-status");
  const logoutButton = document.getElementById("logout-button");
  const signupControls = document.getElementById("signup-controls");
  const adminEmailGroup = document.getElementById("admin-email-group");
  const adminEmail = document.getElementById("admin-email");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");
  let credentials = null;
  let currentUser = null;

  function authorizationHeader(userCredentials = credentials) {
    if (!userCredentials) {
      return {};
    }
    const bytes = new TextEncoder().encode(`${userCredentials.email}:${userCredentials.password}`);
    const binary = Array.from(bytes, (byte) => String.fromCharCode(byte)).join("");
    return { Authorization: `Basic ${btoa(binary)}` };
  }

  function updateAuthView() {
    const isSignedIn = currentUser !== null;
    authStatus.className = "";
    loginForm.classList.toggle("hidden", isSignedIn);
    authStatus.classList.toggle("hidden", !isSignedIn);
    logoutButton.classList.toggle("hidden", !isSignedIn);
    signupControls.classList.toggle("hidden", !isSignedIn);
    adminEmailGroup.classList.toggle("hidden", !isSignedIn || currentUser.role !== "admin");
    adminEmail.required = isSignedIn && currentUser.role === "admin";
    if (isSignedIn) {
      authStatus.textContent = `Signed in as ${currentUser.email} (${currentUser.role})`;
    }
  }

  function showMessage(text, isError) {
    messageDiv.textContent = text;
    messageDiv.className = isError ? "error" : "success";
    messageDiv.classList.remove("hidden");
    setTimeout(() => messageDiv.classList.add("hidden"), 5000);
  }

  // Function to fetch activities from API
  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      const activities = await response.json();

      // Clear loading message
      activitiesList.innerHTML = "";
      activitySelect.querySelectorAll("option:not(:first-child)").forEach((option) => option.remove());

      // Populate activities list
      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft =
          details.max_participants - details.participants.length;

        // Create participants HTML with delete icons instead of bullet points
        const participantsHTML =
          details.participants.length > 0
            ? `<div class="participants-section">
              <h5>Participants:</h5>
              <ul class="participants-list">
                ${details.participants
                  .map((email) => {
                    const canUnregister = currentUser &&
                      (currentUser.role === "admin" || currentUser.email === email.toLowerCase());
                    const action = canUnregister
                      ? `<button class="delete-btn" data-activity="${name}" data-email="${email}">Remove</button>`
                      : "";
                    return `<li><span class="participant-email">${email}</span>${action}</li>`;
                  })
                  .join("")}
              </ul>
            </div>`
            : `<p><em>No participants yet</em></p>`;

        activityCard.innerHTML = `
          <h4>${name}</h4>
          <p>${details.description}</p>
          <p><strong>Schedule:</strong> ${details.schedule}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          <div class="participants-container">
            ${participantsHTML}
          </div>
        `;

        activitiesList.appendChild(activityCard);

        // Add option to select dropdown
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });

      // Add event listeners to delete buttons
      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  // Handle unregister functionality
  async function handleUnregister(event) {
    const button = event.target;
    const activity = button.getAttribute("data-activity");
    const email = button.getAttribute("data-email");

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/unregister?email=${encodeURIComponent(email)}`,
        {
          method: "DELETE",
          headers: authorizationHeader(),
        }
      );

      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, false);

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        showMessage(result.detail || "An error occurred", true);
      }
    } catch (error) {
      showMessage("Failed to unregister. Please try again.", true);
      console.error("Error unregistering:", error);
    }
  }

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const attemptedCredentials = {
      email: loginEmail.value.trim(),
      password: loginPassword.value,
    };

    try {
      const response = await fetch("/auth/me", {
        headers: authorizationHeader(attemptedCredentials),
      });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail || "Sign in failed");
      }

      credentials = attemptedCredentials;
      currentUser = result;
      loginForm.reset();
      updateAuthView();
      fetchActivities();
    } catch (error) {
      authStatus.textContent = error.message;
      authStatus.className = "error";
      console.error("Error signing in:", error);
    }
  });

  logoutButton.addEventListener("click", () => {
    credentials = null;
    currentUser = null;
    updateAuthView();
    fetchActivities();
  });

  // Handle form submission
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const activity = document.getElementById("activity").value;
    const signupUrl = new URL(
      `/activities/${encodeURIComponent(activity)}/signup`,
      window.location.origin
    );
    if (currentUser.role === "admin") {
      signupUrl.searchParams.set("email", adminEmail.value.trim());
    }

    try {
      const response = await fetch(signupUrl, {
        method: "POST",
        headers: authorizationHeader(),
      });

      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, false);
        signupForm.reset();

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        showMessage(result.detail || "An error occurred", true);
      }
    } catch (error) {
      showMessage("Failed to sign up. Please try again.", true);
      console.error("Error signing up:", error);
    }
  });

  // Initialize app
  updateAuthView();
  fetchActivities();
});
