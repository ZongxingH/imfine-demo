(function () {
  "use strict";

  const DEFAULT_API_BASE = "http://localhost:8000/api";
  const TOKEN_KEY = "imfine_user_token";
  const API_BASE_KEY = "imfine_api_base";
  const PAGE_SIZE = 8;

  const state = {
    token: localStorage.getItem(TOKEN_KEY) || "",
    apiBase: localStorage.getItem(API_BASE_KEY) || DEFAULT_API_BASE,
    seatsPage: 1,
    reservationsPage: 1,
    floors: [],
    rooms: []
  };

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  function setToken(token) {
    state.token = token || "";
    if (state.token) {
      localStorage.setItem(TOKEN_KEY, state.token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
    updateAuthStatus();
  }

  function updateAuthStatus() {
    $("#authStatus").textContent = state.token ? "Signed in" : "Signed out";
  }

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

  function setActiveTab(tabId) {
    $$(".tab").forEach((tab) => tab.classList.toggle("active", tab.dataset.tab === tabId));
    $$(".view").forEach((view) => view.classList.toggle("active", view.id === tabId));
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

  function optionHtml(value, label) {
    return `<option value="${String(value || "")}">${String(label || value || "Unnamed")}</option>`;
  }

  async function loadFloors() {
    const data = await apiFetch("/floors?page=1&pageSize=100");
    state.floors = normalizeList(data);
    $("#floorFilter").innerHTML = optionHtml("", "All floors") + state.floors
      .map((floor) => optionHtml(floor.id, floor.name || `Floor ${floor.number || floor.id}`))
      .join("");
  }

  async function loadRooms() {
    const floorId = $("#floorFilter").value;
    const query = floorId ? `?floorId=${encodeURIComponent(floorId)}&pageSize=100` : "?pageSize=100";
    const data = await apiFetch(`/rooms${query}`);
    state.rooms = normalizeList(data);
    $("#roomFilter").innerHTML = optionHtml("", "All rooms") + state.rooms
      .map((room) => optionHtml(room.id, room.name || `Room ${room.id}`))
      .join("");
  }

  function renderSeats(data) {
    const list = normalizeList(data);
    const target = $("#seatList");
    target.innerHTML = list.length ? list.map((seat) => {
      const status = seat.status || (seat.available ? "available" : "reserved");
      return `
        <article class="item">
          <div class="item-title">
            <span>${seat.code || seat.name || `Seat ${seat.id}`}</span>
            <span class="badge ${status}">${status}</span>
          </div>
          <div class="item-meta">${seat.roomName || "Room"} · ${seat.floorName || "Floor"} · ID: ${seat.id || "-"}</div>
        </article>
      `;
    }).join("") : `<div class="item">No seats found.</div>`;

    $("#seatPageInfo").textContent = `Page ${state.seatsPage}`;
    $("[data-pager='seats'] [data-page-action='prev']").disabled = state.seatsPage <= 1;
    $("[data-pager='seats'] [data-page-action='next']").disabled = !hasNextPage(data, list, state.seatsPage);
  }

  async function loadSeats() {
    const params = new URLSearchParams({
      page: String(state.seatsPage),
      pageSize: String(PAGE_SIZE)
    });
    const floorId = $("#floorFilter").value;
    const roomId = $("#roomFilter").value;
    const status = $("#seatStatusFilter").value;
    if (floorId) params.set("floorId", floorId);
    if (roomId) params.set("roomId", roomId);
    if (status) params.set("status", status);
    const data = await apiFetch(`/seats?${params.toString()}`);
    renderSeats(data);
  }

  function renderReservations(data) {
    const list = normalizeList(data);
    $("#reservationList").innerHTML = list.length ? list.map((item) => `
      <article class="item">
        <div class="item-title">
          <span>${item.seatCode || item.seatId || "Seat"}</span>
          <span class="badge ${item.status || "active"}">${item.status || "active"}</span>
        </div>
        <div class="item-meta">${item.startTime || "-"} to ${item.endTime || "-"}</div>
        <div>${item.purpose || ""}</div>
      </article>
    `).join("") : `<div class="item">No active reservations.</div>`;

    $("#reservationPageInfo").textContent = `Page ${state.reservationsPage}`;
    $("[data-pager='reservations'] [data-page-action='prev']").disabled = state.reservationsPage <= 1;
    $("[data-pager='reservations'] [data-page-action='next']").disabled = !hasNextPage(data, list, state.reservationsPage);
  }

  async function loadReservations() {
    const data = await apiFetch(`/reservations/active?page=${state.reservationsPage}&pageSize=${PAGE_SIZE}`);
    renderReservations(data);
  }

  function validateTimeRange(startTime, endTime) {
    const start = new Date(startTime).getTime();
    const end = new Date(endTime).getTime();
    if (!Number.isFinite(start) || !Number.isFinite(end) || start >= end) {
      showToast("End time must be after start time.");
      return false;
    }
    return true;
  }

  async function bootstrapLists() {
    try {
      await loadFloors();
      await loadRooms();
      await loadSeats();
    } catch (error) {
      showToast(error.message);
    }
  }

  function bindEvents() {
    $("#apiBase").value = state.apiBase;
    $("#saveApiBase").addEventListener("click", () => {
      state.apiBase = $("#apiBase").value.trim() || DEFAULT_API_BASE;
      localStorage.setItem(API_BASE_KEY, state.apiBase);
      showToast("API base saved.");
    });

    $$(".tab").forEach((tab) => {
      tab.addEventListener("click", () => setActiveTab(tab.dataset.tab));
    });

    $$(".segment").forEach((segment) => {
      segment.addEventListener("click", () => {
        const mode = segment.dataset.authMode;
        $$(".segment").forEach((item) => item.classList.toggle("active", item === segment));
        $("#loginForm").classList.toggle("hidden", mode !== "login");
        $("#registerForm").classList.toggle("hidden", mode !== "register");
      });
    });

    $("#loginForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!requireForm(event.currentTarget)) return;
      try {
        const data = await apiFetch("/auth/login", {
          method: "POST",
          body: JSON.stringify(formToJson(event.currentTarget))
        });
        setToken(data.token || data.accessToken);
        showToast("Logged in.");
      } catch (error) {
        showToast(error.message);
      }
    });

    $("#registerForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!requireForm(event.currentTarget)) return;
      try {
        const data = await apiFetch("/auth/register", {
          method: "POST",
          body: JSON.stringify(formToJson(event.currentTarget))
        });
        setToken(data.token || data.accessToken || "");
        showToast("Account created.");
      } catch (error) {
        showToast(error.message);
      }
    });

    $("#logoutBtn").addEventListener("click", () => {
      setToken("");
      showToast("Logged out.");
    });

    $("#floorFilter").addEventListener("change", async () => {
      state.seatsPage = 1;
      try {
        await loadRooms();
        await loadSeats();
      } catch (error) {
        showToast(error.message);
      }
    });

    $("#roomFilter").addEventListener("change", () => {
      state.seatsPage = 1;
      loadSeats().catch((error) => showToast(error.message));
    });
    $("#seatStatusFilter").addEventListener("change", () => {
      state.seatsPage = 1;
      loadSeats().catch((error) => showToast(error.message));
    });
    $("#refreshSeats").addEventListener("click", () => bootstrapLists());
    $("#refreshReservations").addEventListener("click", () => loadReservations().catch((error) => showToast(error.message)));

    $$(".pagination").forEach((pager) => {
      pager.addEventListener("click", (event) => {
        const action = event.target.dataset.pageAction;
        if (!action) return;
        const isSeatPager = pager.dataset.pager === "seats";
        const key = isSeatPager ? "seatsPage" : "reservationsPage";
        state[key] += action === "next" ? 1 : -1;
        state[key] = Math.max(1, state[key]);
        (isSeatPager ? loadSeats : loadReservations)().catch((error) => showToast(error.message));
      });
    });

    $("#reservationForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!requireForm(event.currentTarget)) return;
      const payload = formToJson(event.currentTarget);
      if (!validateTimeRange(payload.startTime, payload.endTime)) return;
      try {
        await apiFetch("/reservations", {
          method: "POST",
          body: JSON.stringify(payload)
        });
        event.currentTarget.reset();
        showToast("Reservation submitted.");
      } catch (error) {
        showToast(error.message);
      }
    });

    $("#reportForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!requireForm(event.currentTarget)) return;
      try {
        await apiFetch("/reports", {
          method: "POST",
          body: JSON.stringify(formToJson(event.currentTarget))
        });
        event.currentTarget.reset();
        showToast("Report submitted.");
      } catch (error) {
        showToast(error.message);
      }
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    bindEvents();
    updateAuthStatus();
    bootstrapLists();
    loadReservations().catch(() => {});
  });
})();
