/* SalesGenie — shared utilities (loaded on every page via base.html) */

/* Announce a message to screen readers via the live region */
function announce(message) {
  const el = document.getElementById("status-message");
  if (!el) return;
  el.textContent = "";
  requestAnimationFrame(() => {
    el.textContent = message;
  });
}

/* Toggle button loading state with spinner */
function setLoading(btn, isLoading, label) {
  const textEl = btn.querySelector(".btn-text");
  btn.disabled = isLoading;
  btn.setAttribute("aria-busy", String(isLoading));
  if (isLoading) {
    btn.setAttribute("aria-label", label + ", please wait");
    if (textEl) textEl.innerHTML = `<span class="spinner" aria-hidden="true"></span>${label}`;
  } else {
    btn.setAttribute("aria-label", label);
    if (textEl) textEl.textContent = label;
  }
}

/* Debounce factory — reduces rapid API calls (e.g. search) */
function debounce(fn, delay) {
  let timer;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), delay);
  };
}

/* Escape HTML to prevent XSS in dynamic content */
function escHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/* Open a modal dialog and trap focus */
function openModal(id) {
  const modal = document.getElementById(id);
  if (!modal) return;
  modal.classList.remove("hidden");
  modal.removeAttribute("aria-hidden");
  trapFocus(modal);
  /* Close on backdrop click */
  modal.addEventListener("click", (e) => {
    if (e.target === modal) closeModal(id);
  });
}

/* Close a modal dialog */
function closeModal(id) {
  const modal = document.getElementById(id);
  if (!modal) return;
  modal.classList.add("hidden");
  modal.setAttribute("aria-hidden", "true");
  /* Return focus to the button that opened it */
  const opener = document.getElementById("open-modal-btn");
  if (opener) opener.focus();
}

/* Trap keyboard focus inside a modal (WCAG 2.1 — 2.1.2) */
function trapFocus(modal) {
  const focusable = modal.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  if (!focusable.length) return;
  const first = focusable[0];
  const last = focusable[focusable.length - 1];

  /* Remove any previous listener to avoid duplicates */
  modal._trapHandler && modal.removeEventListener("keydown", modal._trapHandler);

  modal._trapHandler = (e) => {
    if (e.key === "Escape") {
      closeModal(modal.id);
      return;
    }
    if (e.key !== "Tab") return;
    if (e.shiftKey) {
      if (document.activeElement === first) {
        e.preventDefault();
        last.focus();
      }
    } else {
      if (document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  };

  modal.addEventListener("keydown", modal._trapHandler);
  first.focus();
}
