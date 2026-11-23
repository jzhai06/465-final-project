const money = value => `$${Number(value || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
let options = null;

async function api(url, optionsRequest) {
  const response = await fetch(url, optionsRequest);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "The operation could not be completed");
  return data;
}

function showToast(message, error = false) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.className = `toast show${error ? " error" : ""}`;
  setTimeout(() => toast.className = "toast", 3200);
}

function switchView(view) {
  document.querySelectorAll(".view").forEach(element => element.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach(element => element.classList.toggle("active", element.dataset.view === view));
  document.getElementById(`${view}View`).classList.add("active");
  const labels = {dashboard: ["Resale operations", "Good morning."], inventory: ["Collection", "Inventory"], report: ["Analytics", "Profit report"]};
  document.getElementById("pageEyebrow").textContent = labels[view][0];
  document.getElementById("pageTitle").textContent = labels[view][1];
  if (view === "inventory") loadInventory();
  if (view === "report") loadReport();
}

async function loadDashboard() {
  const data = await api("/api/dashboard");
  document.getElementById("statInventory").textContent = data.stats.inventory;
  document.getElementById("statListings").textContent = data.stats.active_listings;
  document.getElementById("statSales").textContent = data.stats.sales;
  document.getElementById("statProfit").textContent = money(data.stats.net_profit);
  document.getElementById("recentSales").innerHTML = data.recent.length
    ? data.recent.map(row => `<tr><td><strong>${escapeHtml(row.title)}</strong></td><td>${escapeHtml(row.brand_name)}</td><td>${row.sale_date}</td><td>${money(row.sale_price)}</td><td>${money(row.net_profit)}</td></tr>`).join("")
    : '<tr><td colspan="5">No completed sales yet.</td></tr>';
}

async function loadInventory() {
  const query = document.getElementById("inventorySearch").value.trim();
  const status = document.getElementById("inventoryStatus").value;
  const rows = await api(`/api/items?q=${encodeURIComponent(query)}&status=${encodeURIComponent(status)}`);
  document.getElementById("inventoryTable").innerHTML = rows.length
    ? rows.map(row => `<tr data-item-id="${row.item_id}"><td>#${row.item_id}</td><td><strong>${escapeHtml(row.title)}</strong></td><td>${escapeHtml(row.brand)}</td><td>${escapeHtml(row.category)}</td><td>${escapeHtml(row.condition)}</td><td>${money(row.purchase_cost)}</td><td><span class="status">${row.active_listings} live</span></td></tr>`).join("")
    : '<tr><td colspan="7">No items match this search.</td></tr>';
}

async function loadReport() {
  const data = await api("/api/report");
  const revenue = data.platforms.reduce((sum, row) => sum + Number(row.revenue), 0);
  const profit = data.platforms.reduce((sum, row) => sum + Number(row.net_profit), 0);
  document.getElementById("reportStats").innerHTML =
    `<article class="stat-card"><span class="stat-label">Sales revenue</span><strong>${money(revenue)}</strong></article>
     <article class="stat-card accent"><span class="stat-label">Total net profit</span><strong>${money(profit)}</strong></article>
     <article class="stat-card"><span class="stat-label">Platforms</span><strong>${data.platforms.length}</strong></article>`;
  document.getElementById("platformReport").innerHTML = data.platforms.length
    ? data.platforms.map(row => `<tr><td><strong>${escapeHtml(row.platform_name)}</strong></td><td>${row.sales}</td><td>${money(row.revenue)}</td><td>${money(row.net_profit)}</td><td>${row.average_days_to_sell ?? "-"}</td></tr>`).join("")
    : '<tr><td colspan="5">No completed sales to report.</td></tr>';
  if (data.monthly.length) {
    const max = Math.max(...data.monthly.map(row => Math.abs(Number(row.net_profit))), 1);
    document.getElementById("profitChart").innerHTML = data.monthly.map(row =>
      `<div class="chart-column"><strong>${money(row.net_profit)}</strong><div style="height:${Math.max(8, Math.abs(Number(row.net_profit)) / max * 110)}px"></div><span>${row.month}</span></div>`
    ).join("");
  } else {
    document.getElementById("profitChart").innerHTML = "<p>No monthly data yet.</p>";
  }
}

function escapeHtml(value) {
  const element = document.createElement("span");
  element.textContent = value ?? "";
  return element.innerHTML;
}

async function ensureOptions() {
  if (!options) options = await api("/api/options");
  return options;
}

function openModal(title, fields, submitText, handler) {
  document.getElementById("modalTitle").textContent = title;
  document.getElementById("modalForm").innerHTML =
    fields.join("") + '<div class="form-actions"><button type="button" id="cancelModal">Cancel</button><button type="submit">' + submitText + '</button></div>';
  document.getElementById("modalBackdrop").hidden = false;
  document.getElementById("cancelModal").onclick = closeModal;
  document.getElementById("modalForm").onsubmit = async event => {
    event.preventDefault();
    const formData = Object.fromEntries(new FormData(event.currentTarget).entries());
    try {
      await handler(formData);
      closeModal();
      await refreshAll();
    } catch (error) {
      showToast(error.message, true);
    }
  };
}

function closeModal() {
  document.getElementById("modalBackdrop").hidden = true;
}

async function openAddItem() {
  const data = await ensureOptions();
  const select = (name, label, rows, idKey, textKey) =>
    `<label>${label}<select name="${name}" required>${rows.map(row => `<option value="${row[idKey]}">${escapeHtml(row[textKey])}</option>`).join("")}</select></label>`;
  openModal("Add inventory item", [
    select("brand_id", "Brand", data.brands, "brand_id", "brand_name"),
    select("category_id", "Category", data.categories, "category_id", "category_name"),
    `<label class="full">Title<input name="title" required maxlength="120" placeholder="Item title"></label>`,
    `<label>Condition<select name="condition">${data.conditions.map(value => `<option>${value}</option>`).join("")}</select></label>`,
    `<label>Purchase cost<input name="purchase_cost" type="number" min="0" step=".01" required></label>`,
    `<label>Acquired date<input name="acquired_date" type="date" value="${new Date().toISOString().slice(0,10)}" required></label>`,
    select("location_id", "Sourcing location (optional)", [{location_id:"", location_name:"No location / online"}, ...data.locations], "location_id", "location_name")
  ], "Add item", async formData => {
    await api("/api/items", {method:"POST", headers:{'Content-Type':'application/json'}, body:JSON.stringify(formData)});
    showToast("Item added successfully");
  });
}

async function openAddListing() {
  const data = await ensureOptions();
  openModal("Create listing", [
    `<label>Item ID<input name="item_id" type="number" min="1" required></label>`,
    `<label>Platform<select name="platform_id">${data.platforms.map(row => `<option value="${row.platform_id}">${escapeHtml(row.platform_name)}</option>`).join("")}</select></label>`,
    `<label>List price<input name="list_price" type="number" min=".01" step=".01" required></label>`,
    `<label>Listed date<input name="listed_date" type="date" value="${new Date().toISOString().slice(0,10)}" required></label>`
  ], "Create listing", async formData => {
    await api("/api/listings", {method:"POST", headers:{'Content-Type':'application/json'}, body:JSON.stringify(formData)});
    showToast("Listing created");
  });
}

async function openRecordSale() {
  const listings = await api("/api/listings");
  if (!listings.length) throw new Error("There are no active listings");
  openModal("Record a sale", [
    `<label class="full">Active listing<select name="listing_id">${listings.map(row => `<option value="${row.listing_id}">#${row.listing_id} - ${escapeHtml(row.title)} (${escapeHtml(row.platform_name)}) - ${money(row.list_price)}</option>`).join("")}</select></label>`,
    `<label>Sale price<input name="sale_price" type="number" min=".01" step=".01" required></label>`,
    `<label>Platform fee<input name="platform_fee" type="number" min="0" step=".01" value="0" required></label>`,
    `<label>Shipping cost<input name="shipping_cost" type="number" min="0" step=".01" value="0" required></label>`,
    `<label>Sale date<input name="sale_date" type="date" value="${new Date().toISOString().slice(0,10)}" required></label>`
  ], "Record sale", async formData => {
    await api("/api/sales", {method:"POST", headers:{'Content-Type':'application/json'}, body:JSON.stringify(formData)});
    showToast("Sale recorded and listings updated");
  });
}

async function openItemDetail(itemId) {
  const data = await api(`/api/items/${itemId}`);
  const item = data.item;
  const listingRows = data.listings.map(row => `<tr><td>#${row.listing_id}</td><td>${escapeHtml(row.platform_name)}</td><td>${money(row.list_price)}</td><td>${row.status}</td><td><button type="button" data-price-listing="${row.listing_id}" ${row.status !== "active" ? "disabled" : ""}>Update price</button></td></tr>`).join("") || "<tr><td colspan='5'>No listings.</td></tr>";
  openModal(item.title, [
    `<div class="full" style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px"><div><span class="eyebrow">Brand</span><p>${escapeHtml(item.brand)}</p></div><div><span class="eyebrow">Category</span><p>${escapeHtml(item.category)}</p></div><div><span class="eyebrow">Condition</span><p>${escapeHtml(item.condition)}</p></div></div>`,
    `<div class="full table-wrap"><table><thead><tr><th>ID</th><th>Platform</th><th>Price</th><th>Status</th><th></th></tr></thead><tbody>${listingRows}</tbody></table></div>`
  ], "Close", async () => closeModal());
  document.getElementById("modalForm").onsubmit = event => { event.preventDefault(); closeModal(); };
  document.querySelectorAll("[data-price-listing]").forEach(button => button.onclick = async () => {
    const price = prompt("Enter the new list price:");
    if (price === null) return;
    try {
      await api(`/api/listings/${button.dataset.priceListing}`, {method:"PATCH", headers:{'Content-Type':'application/json'}, body:JSON.stringify({list_price:price})});
      showToast("Listing price updated");
      closeModal();
      await refreshAll();
    } catch (error) {
      showToast(error.message, true);
    }
  });
}

async function refreshAll() {
  await Promise.all([loadDashboard(), loadInventory()]);
  const activeView = document.querySelector(".view.active").id;
  if (activeView === "reportView") await loadReport();
}

document.querySelectorAll(".nav-item").forEach(button => button.addEventListener("click", () => switchView(button.dataset.view)));
document.querySelectorAll("[data-action]").forEach(button => button.addEventListener("click", async () => {
  try {
    if (button.dataset.action === "add-item") await openAddItem();
    if (button.dataset.action === "add-listing") await openAddListing();
    if (button.dataset.action === "record-sale") await openRecordSale();
  } catch (error) {
    showToast(error.message, true);
  }
}));
document.getElementById("openAddItem").addEventListener("click", openAddItem);
document.getElementById("closeModal").addEventListener("click", closeModal);
document.getElementById("modalBackdrop").addEventListener("click", event => { if (event.target.id === "modalBackdrop") closeModal(); });
document.getElementById("inventorySearch").addEventListener("input", () => loadInventory());
document.getElementById("inventoryStatus").addEventListener("change", loadInventory);
document.getElementById("inventoryTable").addEventListener("click", event => {
  const row = event.target.closest("[data-item-id]");
  if (row) openItemDetail(row.dataset.itemId).catch(error => showToast(error.message, true));
});
document.getElementById("refreshButton").addEventListener("click", () => refreshAll().then(() => showToast("Dashboard refreshed")));

loadDashboard().catch(error => showToast(error.message, true));
