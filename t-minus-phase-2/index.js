// Target date: August 31, 2025, 00:00:00 UTC
const targetDate = new Date("2025-09-08T00:00:00Z");

// DOM Elements
const daysElement = document.getElementById("days");
const hoursElement = document.getElementById("hours");
const minutesElement = document.getElementById("minutes");
const secondsElement = document.getElementById("seconds");
const countdownElement = document.getElementById("countdown");

// Previous values for change detection
let prevDays = -1;
let prevHours = -1;
let prevMinutes = -1;
let prevSeconds = -1;

// Update countdown function
function updateCountdown() {
  const now = new Date();
  const difference = targetDate - now;

  if (difference > 0) {
    // Calculate time units
    const days = Math.floor(difference / (1000 * 60 * 60 * 24));
    const hours = Math.floor(
      (difference % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60)
    );
    const minutes = Math.floor((difference % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((difference % (1000 * 60)) / 1000);

    // Update display with animation on change
    if (days !== prevDays) {
      updateTimeUnit(daysElement, days);
      prevDays = days;
    }
    if (hours !== prevHours) {
      updateTimeUnit(hoursElement, hours);
      prevHours = hours;
    }
    if (minutes !== prevMinutes) {
      updateTimeUnit(minutesElement, minutes);
      prevMinutes = minutes;
    }
    if (seconds !== prevSeconds) {
      updateTimeUnit(secondsElement, seconds);
      prevSeconds = seconds;
    }
  } else {
    // Countdown reached zero
    clearInterval(countdownInterval);
    countdownElement.innerHTML =
      '<div class="countdown-complete">SEQUENCE COMPLETE</div>';
  }
}

// Update individual time unit with animation
function updateTimeUnit(element, value) {
  const formattedValue = String(value).padStart(2, "0");
  element.classList.add("glitch");
  element.textContent = formattedValue;

  setTimeout(() => {
    element.classList.remove("glitch");
  }, 300);
}

// Random glitch effect
function randomGlitch() {
  const elements = [daysElement, hoursElement, minutesElement, secondsElement];
  const randomElement = elements[Math.floor(Math.random() * elements.length)];

  randomElement.classList.add("glitch");
  setTimeout(() => {
    randomElement.classList.remove("glitch");
  }, 300);
}

// Initialize particles.js
function initParticles() {
  particlesJS("particles-js", {
    particles: {
      number: {
        value: 50,
        density: {
          enable: true,
          value_area: 800,
        },
      },
      color: {
        value: "#00ff00",
      },
      shape: {
        type: "circle",
      },
      opacity: {
        value: 0.3,
        random: true,
        anim: {
          enable: true,
          speed: 1,
          opacity_min: 0.1,
          sync: false,
        },
      },
      size: {
        value: 2,
        random: true,
        anim: {
          enable: true,
          speed: 2,
          size_min: 0.1,
          sync: false,
        },
      },
      line_linked: {
        enable: false,
      },
      move: {
        enable: true,
        speed: 1,
        direction: "bottom",
        random: true,
        straight: false,
        out_mode: "out",
        bounce: false,
        attract: {
          enable: false,
          rotateX: 600,
          rotateY: 1200,
        },
      },
    },
    interactivity: {
      detect_on: "canvas",
      events: {
        onhover: {
          enable: true,
          mode: "grab",
        },
        onclick: {
          enable: false,
        },
        resize: true,
      },
      modes: {
        grab: {
          distance: 150,
          line_linked: {
            opacity: 0.5,
          },
        },
      },
    },
    retina_detect: true,
  });
}

// Typing effect for status line
function typeStatusMessage() {
  const statusLine = document.querySelector(".status-line");
  const originalText = statusLine.textContent;
  let index = 0;

  statusLine.textContent = "";
  statusLine.style.opacity = "1";

  const typeInterval = setInterval(() => {
    if (index < originalText.length) {
      statusLine.textContent += originalText[index];
      index++;
    } else {
      clearInterval(typeInterval);
    }
  }, 50);
}

// Navigation functionality
function initNavigation() {
  const sidebar = document.getElementById("sidebar");
  const sidebarToggle = document.getElementById("sidebar-toggle");
  const mobileNavToggle = document.getElementById("mobile-nav-toggle");
  const sidebarOverlay = document.getElementById("sidebar-overlay");
  const phaseToggles = document.querySelectorAll(".phase-toggle");

  // Desktop sidebar toggle
  if (sidebarToggle) {
    sidebarToggle.addEventListener("click", () => {
      sidebar.classList.toggle("active");
    });
  }

  // Mobile hamburger menu toggle
  if (mobileNavToggle) {
    mobileNavToggle.addEventListener("click", () => {
      mobileNavToggle.classList.toggle("active");
      sidebar.classList.toggle("active");
      if (sidebarOverlay) {
        sidebarOverlay.classList.toggle("active");
      }
    });
  }

  // Close sidebar when clicking overlay
  if (sidebarOverlay) {
    sidebarOverlay.addEventListener("click", () => {
      sidebar.classList.remove("active");
      sidebarOverlay.classList.remove("active");
      if (mobileNavToggle) {
        mobileNavToggle.classList.remove("active");
      }
    });
  }

  // Phase section toggles
  phaseToggles.forEach((toggle) => {
    toggle.addEventListener("click", () => {
      const phase = toggle.getAttribute("data-phase");
      const content = document.getElementById(`phase${phase}-content`);

      toggle.classList.toggle("expanded");
      content.classList.toggle("expanded");
    });
  });

  // Close mobile menu when clicking outside
  document.addEventListener("click", (e) => {
    if (window.innerWidth <= 500) {
      if (
        !sidebar.contains(e.target) &&
        !mobileNavToggle.contains(e.target) &&
        sidebar.classList.contains("active")
      ) {
        sidebar.classList.remove("active");
        mobileNavToggle.classList.remove("active");
        if (sidebarOverlay) {
          sidebarOverlay.classList.remove("active");
        }
      }
    } else if (window.innerWidth <= 1024) {
      if (
        !sidebar.contains(e.target) &&
        !sidebarToggle.contains(e.target) &&
        sidebar.classList.contains("active")
      ) {
        sidebar.classList.remove("active");
      }
    }
  });

  // Handle window resize
  window.addEventListener("resize", () => {
    if (window.innerWidth > 1024) {
      sidebar.classList.remove("active");
      if (mobileNavToggle) {
        mobileNavToggle.classList.remove("active");
      }
      if (sidebarOverlay) {
        sidebarOverlay.classList.remove("active");
      }
    }
  });
}

// Initialize everything
document.addEventListener("DOMContentLoaded", () => {
  // Initialize navigation
  initNavigation();

  // Initialize particles
  if (typeof particlesJS !== "undefined") {
    initParticles();
  }

  // Start typing effect after a short delay
  setTimeout(typeStatusMessage, 500);

  // Initial countdown update
  updateCountdown();

  // Update countdown every second
  const countdownInterval = setInterval(updateCountdown, 1000);

  // Random glitch every 30-60 seconds
  setInterval(() => {
    randomGlitch();
  }, Math.random() * 30000 + 30000);

  // Add subtle screen flicker occasionally
  setInterval(() => {
    document.querySelector(".terminal-container").style.animation = "none";
    setTimeout(() => {
      document.querySelector(".terminal-container").style.animation =
        "terminal-flicker 0.15s infinite alternate";
    }, 100);
  }, Math.random() * 60000 + 60000);
});

// Store interval ID globally for cleanup
let countdownInterval;
