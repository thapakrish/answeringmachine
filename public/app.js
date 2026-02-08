import { initializeApp } from "https://www.gstatic.com/firebasejs/11.3.0/firebase-app.js";
import { getAuth, signInAnonymously } from "https://www.gstatic.com/firebasejs/11.3.0/firebase-auth.js";
import {
  getFirestore, collection, doc, getDoc, getDocs, setDoc, deleteDoc, serverTimestamp,
} from "https://www.gstatic.com/firebasejs/11.3.0/firebase-firestore.js";

// Firebase config
const app = initializeApp({
  apiKey: "REDACTED_API_KEY",
  authDomain: "contlearn.firebaseapp.com",
  projectId: "contlearn",
  storageBucket: "contlearn.firebasestorage.app",
  messagingSenderId: "764252345870",
  appId: "1:764252345870:web:819df01d41a6ca52068e5f",
});

const auth = getAuth(app);
const db = getFirestore(app);

// State
let currentFamilyId = null;
let currentFamilyData = null;

const $ = (id) => document.getElementById(id);

const loginScreen = $("login-screen");
const dashScreen = $("dashboard-screen");

// DOM helpers
function el(tag, attrs, ...children) {
  const e = document.createElement(tag);
  if (attrs) {
    for (const [k, v] of Object.entries(attrs)) {
      if (k === "className") e.className = v;
      else if (k.startsWith("data-")) e.setAttribute(k, v);
      else e[k] = v;
    }
  }
  for (const c of children) {
    if (typeof c === "string") e.appendChild(document.createTextNode(c));
    else if (c) e.appendChild(c);
  }
  return e;
}

function clearChildren(parent) {
  while (parent.firstChild) parent.removeChild(parent.firstChild);
}

function formatTimestamp(ts) {
  if (!ts) return "\u2014";
  const d = ts.toDate ? ts.toDate() : new Date(ts);
  return d.toLocaleString();
}

// Auth
async function ensureAnonymousAuth() {
  if (!auth.currentUser) {
    await signInAnonymously(auth);
  }
}

// Login
$("signin-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const familyId = $("signin-family-id").value.trim();
  const passphrase = $("signin-passphrase").value.trim();
  const errEl = $("signin-error");
  errEl.style.display = "none";

  try {
    await ensureAnonymousAuth();
    const snap = await getDoc(doc(db, "families", familyId));
    if (!snap.exists()) {
      errEl.textContent = "Family not found.";
      errEl.style.display = "block";
      return;
    }
    const data = snap.data();
    if (data.passphrase !== passphrase) {
      errEl.textContent = "Incorrect passphrase.";
      errEl.style.display = "block";
      return;
    }
    currentFamilyId = familyId;
    currentFamilyData = data;
    sessionStorage.setItem("familyId", familyId);
    showDashboard();
  } catch (err) {
    errEl.textContent = "Error: " + err.message;
    errEl.style.display = "block";
  }
});

// Create Family
$("create-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const name = $("create-name").value.trim();
  const familyId = $("create-id").value.trim().toLowerCase().replace(/\s+/g, "_");
  const phone = $("create-phone").value.trim();
  const passphrase = $("create-passphrase").value.trim();
  const errEl = $("create-error");
  const okEl = $("create-success");
  errEl.style.display = "none";
  okEl.style.display = "none";

  if (!/^\+1\d{10}$/.test(phone)) {
    errEl.textContent = "Phone must be E.164 format: +1XXXXXXXXXX";
    errEl.style.display = "block";
    return;
  }

  try {
    await ensureAnonymousAuth();
    const existing = await getDoc(doc(db, "families", familyId));
    if (existing.exists()) {
      errEl.textContent = "Family ID already exists.";
      errEl.style.display = "block";
      return;
    }
    await setDoc(doc(db, "families", familyId), {
      name,
      device_phones: [phone],
      passphrase,
      created_at: serverTimestamp(),
    });
    okEl.textContent = `Family "${name}" created! Sign in with ID: ${familyId}`;
    okEl.style.display = "block";
    $("create-form").reset();
  } catch (err) {
    errEl.textContent = "Error: " + err.message;
    errEl.style.display = "block";
  }
});

// Toggle login/create
$("show-create").addEventListener("click", () => {
  $("signin-box").classList.add("hidden");
  $("create-box").classList.remove("hidden");
});
$("show-signin").addEventListener("click", () => {
  $("create-box").classList.add("hidden");
  $("signin-box").classList.remove("hidden");
});

// Logout
$("btn-logout").addEventListener("click", () => {
  currentFamilyId = null;
  currentFamilyData = null;
  sessionStorage.removeItem("familyId");
  dashScreen.classList.add("hidden");
  loginScreen.classList.remove("hidden");
  $("signin-form").reset();
});

// Dashboard
async function showDashboard() {
  loginScreen.classList.add("hidden");
  dashScreen.classList.remove("hidden");
  $("dash-family-name").textContent = currentFamilyData.name;
  $("dash-family-id").textContent = currentFamilyId;
  loadMembers();
  loadMessages();
  loadCallLogs();
  loadReminders();
}

// Tabs
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    $("tab-" + btn.dataset.tab).classList.add("active");
  });
});

// Members
async function loadMembers() {
  const loading = $("members-loading");
  const table = $("members-table");
  const empty = $("members-empty");
  const tbody = $("members-tbody");
  loading.classList.remove("hidden");
  table.classList.add("hidden");
  empty.classList.add("hidden");

  const snap = await getDocs(collection(db, "families", currentFamilyId, "members"));
  const members = [];
  snap.forEach((d) => members.push({ id: d.id, ...d.data() }));

  loading.classList.add("hidden");
  if (members.length === 0) {
    empty.classList.remove("hidden");
    return;
  }

  clearChildren(tbody);
  members.sort((a, b) => a.name.localeCompare(b.name));

  for (const m of members) {
    const typeBadge = el("span", { className: m.is_device_user ? "badge badge-green" : "badge badge-blue" },
      m.is_device_user ? "Device User" : "Family");

    const deleteBtn = el("button", { className: "btn-logout" }, "Delete");
    deleteBtn.addEventListener("click", async () => {
      if (!confirm(`Delete member ${m.name}?`)) return;
      await deleteDoc(doc(db, "families", currentFamilyId, "members", m.id));
      loadMembers();
    });

    const row = el("tr", null,
      el("td", null, m.name),
      el("td", null, m.role),
      el("td", null, (m.phone_numbers || []).join(", ")),
      el("td", null, typeBadge),
      el("td", null, deleteBtn),
    );
    tbody.appendChild(row);
  }

  table.classList.remove("hidden");
}

// Add Member
$("add-member-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const name = $("member-name").value.trim();
  const role = $("member-role").value;
  const phone = $("member-phone").value.trim();
  const isDevice = $("member-device-user").checked;
  const errEl = $("member-error");
  const okEl = $("member-success");
  errEl.style.display = "none";
  okEl.style.display = "none";

  if (!/^\+1\d{10}$/.test(phone)) {
    errEl.textContent = "Phone must be E.164 format: +1XXXXXXXXXX";
    errEl.style.display = "block";
    return;
  }

  const memberId = "member_" + name.toLowerCase().replace(/\s+/g, "_");

  try {
    await setDoc(doc(db, "families", currentFamilyId, "members", memberId), {
      name,
      role,
      phone_numbers: [phone],
      is_device_user: isDevice,
      preferences: {},
    });
    okEl.textContent = `Member "${name}" added!`;
    okEl.style.display = "block";
    $("add-member-form").reset();
    loadMembers();
    setTimeout(() => { okEl.style.display = "none"; }, 3000);
  } catch (err) {
    errEl.textContent = "Error: " + err.message;
    errEl.style.display = "block";
  }
});

// Messages
async function loadMessages() {
  const loading = $("messages-loading");
  const list = $("messages-list");
  const empty = $("messages-empty");
  loading.classList.remove("hidden");
  list.classList.add("hidden");
  empty.classList.add("hidden");

  const snap = await getDocs(collection(db, "families", currentFamilyId, "messages"));
  const msgs = [];
  snap.forEach((d) => msgs.push({ id: d.id, ...d.data() }));

  loading.classList.add("hidden");
  if (msgs.length === 0) {
    empty.classList.remove("hidden");
    return;
  }

  msgs.sort((a, b) => {
    const ta = a.created_at?.toDate?.() || new Date(0);
    const tb = b.created_at?.toDate?.() || new Date(0);
    return tb - ta;
  });

  clearChildren(list);
  for (const m of msgs) {
    const readBadge = el("span",
      { className: m.read ? "badge badge-green" : "badge badge-orange" },
      m.read ? "Read" : "Unread");

    const card = el("div", { className: "card" },
      el("div", { className: "card-header" },
        el("span", { className: "name" }, "From: " + (m.from_name || m.from_member_id)),
        el("span", { className: "time" }, formatTimestamp(m.created_at)),
      ),
      el("div", { className: "card-body" }, m.content),
      el("div", { className: "card-meta" },
        document.createTextNode("To: " + m.to_member_id + " \u00b7 "),
        readBadge,
      ),
    );
    list.appendChild(card);
  }

  list.classList.remove("hidden");
}

// Call Logs
async function loadCallLogs() {
  const loading = $("calls-loading");
  const list = $("calls-list");
  const empty = $("calls-empty");
  loading.classList.remove("hidden");
  list.classList.add("hidden");
  empty.classList.add("hidden");

  const snap = await getDocs(collection(db, "families", currentFamilyId, "call_logs"));
  const logs = [];
  snap.forEach((d) => logs.push({ id: d.id, ...d.data() }));

  loading.classList.add("hidden");
  if (logs.length === 0) {
    empty.classList.remove("hidden");
    return;
  }

  logs.sort((a, b) => {
    const ta = a.timestamp?.toDate?.() || new Date(0);
    const tb = b.timestamp?.toDate?.() || new Date(0);
    return tb - ta;
  });

  clearChildren(list);
  for (const l of logs) {
    const anonBadge = el("span",
      { className: l.is_anonymous ? "badge badge-purple" : "badge badge-blue" },
      l.is_anonymous ? "Anonymous" : "Identified");

    const card = el("div", { className: "card" },
      el("div", { className: "card-header" },
        el("span", { className: "name" }, l.caller_name || "Unknown"),
        el("span", { className: "time" }, formatTimestamp(l.timestamp)),
      ),
      el("div", { className: "card-body" }, l.summary || "No summary"),
      el("div", { className: "card-meta" },
        document.createTextNode("Phone: " + (l.caller_phone || "\u2014") + " \u00b7 "),
        anonBadge,
      ),
    );
    list.appendChild(card);
  }

  list.classList.remove("hidden");
}

// Reminders
async function loadReminders() {
  const loading = $("reminders-loading");
  const list = $("reminders-list");
  const empty = $("reminders-empty");
  loading.classList.remove("hidden");
  list.classList.add("hidden");
  empty.classList.add("hidden");

  const snap = await getDocs(collection(db, "families", currentFamilyId, "reminders"));
  const rems = [];
  snap.forEach((d) => rems.push({ id: d.id, ...d.data() }));

  loading.classList.add("hidden");
  if (rems.length === 0) {
    empty.classList.remove("hidden");
    return;
  }

  rems.sort((a, b) => {
    const ta = a.created_at?.toDate?.() || new Date(0);
    const tb = b.created_at?.toDate?.() || new Date(0);
    return tb - ta;
  });

  clearChildren(list);
  for (const r of rems) {
    const activeBadge = el("span",
      { className: r.active ? "badge badge-green" : "badge badge-red" },
      r.active ? "Active" : "Inactive");
    const recurBadge = el("span",
      { className: r.recurring ? "badge badge-purple" : "badge badge-blue" },
      r.recurring ? "Recurring" : "One-time");

    const card = el("div", { className: "card" },
      el("div", { className: "card-header" },
        el("span", { className: "name" }, r.content),
        el("span", { className: "time" }, r.time || "\u2014"),
      ),
      el("div", { className: "card-body" }, "For: " + r.for_member_id),
      el("div", { className: "card-meta" },
        activeBadge,
        document.createTextNode(" "),
        recurBadge,
      ),
    );
    list.appendChild(card);
  }

  list.classList.remove("hidden");
}

// Session restore
(async function init() {
  const savedId = sessionStorage.getItem("familyId");
  if (savedId) {
    try {
      await ensureAnonymousAuth();
      const snap = await getDoc(doc(db, "families", savedId));
      if (snap.exists()) {
        currentFamilyId = savedId;
        currentFamilyData = snap.data();
        showDashboard();
        return;
      }
    } catch (_) {}
    sessionStorage.removeItem("familyId");
  }
})();
