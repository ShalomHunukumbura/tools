// Small enhancements on top of a page that works without them: theme switch, copy
// buttons, filters, folding long outputs, and reveal-on-scroll.

const root = document.documentElement;
const announce = document.getElementById("announce");

function say(message) {
  announce.textContent = "";
  requestAnimationFrame(() => { announce.textContent = message; });
}

// Theme: follows the system until the reader picks one, then remembers it.
document.querySelector(".theme-toggle")?.addEventListener("click", () => {
  const current = root.dataset.theme
    || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  const next = current === "dark" ? "light" : "dark";
  root.dataset.theme = next;
  try { localStorage.setItem("theme", next); } catch (e) {}
  say(`${next[0].toUpperCase()}${next.slice(1)} theme`);
});

// Copy install commands.
document.querySelectorAll(".copy").forEach((button) => {
  button.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(button.dataset.copy);
    } catch (e) {
      say("Couldn't copy. Select the command instead.");
      return;
    }
    button.classList.add("is-copied");
    say("Copied");
    setTimeout(() => button.classList.remove("is-copied"), 1600);
  });
});

// Filter by area. Filtering drops the featured layout so the cards sit evenly.
const grid = document.querySelector(".grid");
const filters = document.querySelectorAll(".filter");
filters.forEach((button) => {
  button.addEventListener("click", () => {
    const area = button.dataset.filter;
    filters.forEach((b) => b.setAttribute("aria-pressed", String(b === button)));
    grid.classList.toggle("is-filtered", area !== "all");
    let shown = 0;
    grid.querySelectorAll(".tool").forEach((tool) => {
      const match = area === "all" || tool.dataset.category === area;
      tool.hidden = !match;
      if (match) { tool.classList.add("is-visible"); shown += 1; }
    });
    say(`${shown} tool${shown === 1 ? "" : "s"} shown`);
  });
});

// Long outputs start folded.
document.querySelectorAll(".term-more").forEach((button) => {
  button.addEventListener("click", () => {
    const term = button.closest(".term");
    const folded = term.classList.toggle("is-folded");
    button.setAttribute("aria-expanded", String(!folded));
    button.textContent = folded ? "Show full output" : "Show less";
    if (folded) term.scrollIntoView({ block: "nearest" });
  });
});

// Reveal sections as they enter the viewport.
const revealables = document.querySelectorAll("[data-reveal]");
if ("IntersectionObserver" in window) {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      }
    });
  }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });
  revealables.forEach((el) => observer.observe(el));
} else {
  revealables.forEach((el) => el.classList.add("is-visible"));
}
