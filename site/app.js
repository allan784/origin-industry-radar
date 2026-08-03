const CATEGORY_LABELS = {
  consumer_fitness_trends: "Consumer fitness",
  consumer_equipment_trends: "Consumer equipment",
  gym_trends: "Gym trends",
  gym_equipment_trends: "Gym equipment",
  industry_voices: "Industry voices (LinkedIn)",
};

let state = { data: null, cat: "all", region: "all", q: "" };

async function load() {
  const res = await fetch("data.json", { cache: "no-store" });
  state.data = await res.json();
  render();
}

function fmtDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d)) return "";
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

function matches(item) {
  if (state.cat !== "all" && item.category !== state.cat) return false;
  if (state.region === "foresight" && !item.foresight) return false;
  if (["uk", "us", "au"].includes(state.region) && item.region !== state.region) return false;
  if (state.q) {
    const hay = (item.title + " " + (item.summary || "")).toLowerCase();
    if (!hay.includes(state.q.toLowerCase())) return false;
  }
  return true;
}

function render() {
  const feed = document.getElementById("feed");
  const lastRun = document.getElementById("lastRun");
  if (!state.data) return;

  const runDate = new Date(state.data.last_run);
  lastRun.textContent = isNaN(runDate)
    ? "Never run yet"
    : `Last scan: ${runDate.toLocaleString("en-GB")} · ${state.data.item_count} items tracked`;

  const items = state.data.items.filter(matches);
  feed.innerHTML = "";

  if (items.length === 0) {
    feed.innerHTML = `<div class="empty">No items match these filters yet. Either narrow filters or wait for the next scan.</div>`;
    return;
  }

  for (const item of items) {
    const card = document.createElement("div");
    card.className = "card";
    const sectorTags = (item.sectors || [])
      .filter((s) => s !== "unclassified")
      .map((s) => `<span class="tag">${s.replace(/_/g, " ")}</span>`)
      .join("");
    const foresightTag = item.foresight ? `<span class="tag foresight">foresight — not yet UK</span>` : "";
    const manualTag = item.source_type === "linkedin_manual" ? `<span class="tag manual">manual snapshot</span>` : "";

    card.innerHTML = `
      <a href="${item.url}" target="_blank" rel="noopener">${item.title}</a>
      <div class="summary">${(item.summary || "").replace(/<[^>]+>/g, "").slice(0, 180)}</div>
      <div class="tags">
        <span class="tag">${CATEGORY_LABELS[item.category] || item.category}</span>
        <span class="tag">${(item.region || "").toUpperCase()}</span>
        ${sectorTags}
        ${foresightTag}
        ${manualTag}
      </div>
      <div class="rowmeta">
        <span>${item.source}</span>
        <span>${fmtDate(item.fetched_at)}</span>
      </div>
    `;
    feed.appendChild(card);
  }
}

function wireFilters() {
  document.querySelectorAll("#categoryFilters .chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#categoryFilters .chip").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.cat = btn.dataset.cat;
      render();
    });
  });
  document.querySelectorAll("#regionFilters .chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#regionFilters .chip").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.region = btn.dataset.region;
      render();
    });
  });
  document.getElementById("searchBox").addEventListener("input", (e) => {
    state.q = e.target.value;
    render();
  });
}

wireFilters();
load();
