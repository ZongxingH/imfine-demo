(function () {
  "use strict";

  const DEFAULT_API_BASE = "http://localhost:8000/api";
  const API_BASE_KEY = "imfine_api_base";
  const ADMIN_TOKEN_KEY = "imfine_admin_token";
  const PAGE_SIZE = 10;

  const state = {
    apiBase: localStorage.getItem(API_BASE_KEY) || DEFAULT_API_BASE,
    token: localStorage.getItem(ADMIN_TOKEN_KEY) || "",
    activeView: "resources",
    seatsPage: 1,
    reportsPage: 1
  };

  const titles = {
    resources: "Resource Management",
    reports: "Report Review",
    stats: "Utilization Statistics"
  };

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  function showToast(message) {
    const toast = $("#toast");
    toast.textContent = message;
    toast.classList.add("show");
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(() => toast.classList.remove("show"), 2600);
  }

  async function apiFetch(path, options = {}) {
    const headers = new Headers(options.headers || {});
    if (!headers.has("Content-Type") && options.body) {
      headers.set("Content-Type", "application/json");
    }
    if (state.token) {
      headers.set("Authorization", `Bearer ${state.token}`);
    }

    const response = await fetch(`${state.apiBase}${path}`, {
      ...options,
      headers
    });

    let data = null;
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      data = await response.json();
    }

    if (!response.ok) {
      throw new Error((data && (data.message || data.error)) || `Request failed: ${response.status}`);
    }
    return data;
  }

  function normalizeList(data) {
    if (Array.isArray(data)) return data;
    if (data && Array.isArray(data.items)) return data.items;
    if (data && Array.isArray(data.data)) return data.data;
    return [];
  }

  function hasNextPage(data, list, page) {
    if (data && typeof data.hasNext === "boolean") return data.hasNext;
    if (data && data.total && data.pageSize) return page * data.pageSize < data.total;
    return list.length === PAGE_SIZE;
  }

  function formToJson(form) {
    return Object.fromEntries(new FormData(form).entries());
  }

  function requireForm(form) {
    if (!form.checkValidity()) {
      form.reportValidity();
      return false;
    }
    return true;
  }

  function setView(viewId) {
    state.activeView = viewId;
    $$(".nav-link").forEach((link) => link.classList.toggle("active", link.dataset.view === viewId));
    $$(".view").forEach((view) => view.classList.toggle("active", view.id === viewId));
    $("#pageTitle").textContent = titles[viewId] || "Admin";
    refreshCurrent();
  }

  function badge(status) {
    const value = status || "unknown";
    return `<span class="badge ${value}">${value}</span>`;
  }

  function renderSeatTable(data) {
    const list = normalizeList(data);
    $("#seatTable").innerHTML = list.length ? list.map((seat) => `
      <tr>
        <td>${seat.code || seat.name || seat.id || "-"}</td>
        <td>${seat.roomName || seat.roomId || "-"}</td>
        <td>${seat.floorName || seat.floorId || "-"}</td>
        <td>${badge(seat.status || (seat.available ? "available" : "reserved"))}</td>
      </tr>
    `).join("") : `<tr><td colspan="4">No seats found.</td></tr>`;

    $("#seatPageInfo").textContent = `Page ${state.seatsPage}`;
    $("[data-pager='seats'] [data-page-action='prev']").disabled = state.seatsPage <= 1;
    $("[data-pager='seats'] [data-page-action='next']").disabled = !hasNextPage(data, list, state.seatsPage);
  }

  async function loadSeats() {
    const params = new URLSearchParams({
      page: String(state.seatsPage),
      pageSize: String(PAGE_SIZE)
    });
    const keyword = $("#seatSearch").value.trim();
    if (keyword) params.set("keyword", keyword);
    const data = await apiFetch(`/admin/seats?${params.toString()}`);
    renderSeatTable(data);
  }

  function renderReportTable(data) {
    const list = normalizeList(data);
    $("#reportTable").innerHTML = list.length ? list.map((report) => `
      <tr>
        <td>${report.seatCode || report.seatId || "-"}</td>
        <td>${report.type || "-"}</td>
        <td>${report.description || ""}</td>
        <td>${badge(report.status || "pending")}</td>
        <td>
          <div class="row-actions">
            <button type="button" data-report-id="${report.id}" data-report-action="approved">Approve</button>
            <button type="button" class="secondary" data-report-id="${report.id}" data-report-action="rejected">Reject</button>
          </div>
        </td>
      </tr>
    `).join("") : `<tr><td colspan="5">No reports found.</td></tr>`;

    $("#reportPageInfo").textContent = `Page ${state.reportsPage}`;
    $("[data-pager='reports'] [data-page-action='prev']").disabled = state.reportsPage <= 1;
    $("[data-pager='reports'] [data-page-action='next']").disabled = !hasNextPage(data, list, state.reportsPage);
  }

  async function loadReports() {
    const params = new URLSearchParams({
      page: String(state.reportsPage),
      pageSize: String(PAGE_SIZE)
    });
    const status = $("#reportStatusFilter").value;
    if (status) params.set("status", status);
    const data = await apiFetch(`/admin/reports?${params.toString()}`);
    renderReportTable(data);
  }

  function renderStats(data) {
    const total = Number(data.totalSeats || 0);
    const reserved = Number(data.reservedSeats || 0);
    const utilization = Number(data.utilizationRate || 0);
    $("#totalSeats").textContent = String(total);
    $("#reservedSeats").textContent = String(reserved);
    $("#utilizationRate").textContent = `${Math.round(utilization)}%`;

    const rooms = normalizeList(data.rooms || data.roomStats || []);
    $("#roomStats").innerHTML = rooms.length ? rooms.map((room) => {
      const rate = Math.max(0, Math.min(100, Number(room.utilizationRate || room.rate || 0)));
      return `
        <div class="bar-row">
          <strong>${room.name || room.roomName || room.id || "Room"}</strong>
          <div class="bar-track"><div class="bar-fill" style="width: ${rate}%"></div></div>
          <span>${rate}%</span>
        </div>
      `;
    }).join("") : `<div>No utilization data.</div>`;
  }

  async function loadStats() {
    const data = await apiFetch("/admin/stats/utilization");
    renderStats(data || {});
  }

  async function refreshCurrent() {
    try {
      if (state.activeView === "reports") {
        await loadReports();
      } else if (state.activeView === "stats") {
        await loadStats();
      } else {
        await loadSeats();
      }
    } catch (error) {
      showToast(error.message);
    }
  }

  async function createResource(resource, form) {
    if (!requireForm(form)) return;
    const payload = formToJson(form);
    await apiFetch(`/admin/${resource}`, {
      method: "POST",
      body: JSON.stringify(payload)
    });
    form.reset();
    showToast(`${resource.slice(0, -1)} created.`);
    await loadSeats();
  }

  function bindEvents() {
    $("#apiBase").value = state.apiBase;
    $("#adminToken").value = state.token;

    $("#saveSettings").addEventListener("click", () => {
      state.apiBase = $("#apiBase").value.trim() || DEFAULT_API_BASE;
      state.token = $("#adminToken").value.trim();
      localStorage.setItem(API_BASE_KEY, state.apiBase);
      localStorage.setItem(ADMIN_TOKEN_KEY, state.token);
      showToast("Settings saved.");
      refreshCurrent();
    });

    $$(".nav-link").forEach((link) => {
      link.addEventListener("click", () => setView(link.dataset.view));
    });

    $("#refreshCurrent").addEventListener("click", refreshCurrent);
    $("#searchSeats").addEventListener("click", () => {
      state.seatsPage = 1;
      loadSeats().catch((error) => showToast(error.message));
    });
    $("#seatSearch").addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        state.seatsPage = 1;
        loadSeats().catch((error) => showToast(error.message));
      }
    });
    $("#reportStatusFilter").addEventListener("change", () => {
      state.reportsPage = 1;
      loadReports().catch((error) => showToast(error.message));
    });

    $("#floorForm").addEventListener("submit", (event) => {
      event.preventDefault();
      createResource("floors", event.currentTarget).catch((error) => showToast(error.message));
    });
    $("#roomForm").addEventListener("submit", (event) => {
      event.preventDefault();
      createResource("rooms", event.currentTarget).catch((error) => showToast(error.message));
    });
    $("#seatForm").addEventListener("submit", (event) => {
      event.preventDefault();
      createResource("seats", event.currentTarget).catch((error) => showToast(error.message));
    });

    $$(".pagination").forEach((pager) => {
      pager.addEventListener("click", (event) => {
        const action = event.target.dataset.pageAction;
        if (!action) return;
        const isSeatPager = pager.dataset.pager === "seats";
        const key = isSeatPager ? "seatsPage" : "reportsPage";
        state[key] += action === "next" ? 1 : -1;
        state[key] = Math.max(1, state[key]);
        (isSeatPager ? loadSeats : loadReports)().catch((error) => showToast(error.message));
      });
    });

    $("#reportTable").addEventListener("click", async (event) => {
      const id = event.target.dataset.reportId;
      const status = event.target.dataset.reportAction;
      if (!id || !status) return;
      try {
        await apiFetch(`/admin/reports/${encodeURIComponent(id)}`, {
          method: "PATCH",
          body: JSON.stringify({ status })
        });
        showToast("Report updated.");
        await loadReports();
      } catch (error) {
        showToast(error.message);
      }
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    bindEvents();
    refreshCurrent();
  });
})();
