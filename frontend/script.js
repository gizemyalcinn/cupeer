const API_URL = "";

const HTML_ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => HTML_ESCAPES[c]);
}

// Üçüncü taraf ilan adreslerinde yalnızca http(s) kabul edilir (javascript: vb. engellenir).
function safeUrl(url) {
  try {
    const parsed = new URL(url, window.location.origin);
    return parsed.protocol === "http:" || parsed.protocol === "https:" ? parsed.href : "#";
  } catch {
    return "#";
  }
}

class ApiError extends Error {}

const SLOW_SERVER_MESSAGE =
  "Sunucu uykudan uyanıyor olabilir (ücretsiz plan), ilk istek 30-50 saniye sürebilir…";

// fetch + zaman aşımı. Ağ hatası ve zaman aşımı, kullanıcıya okunur bir ApiError olarak döner.
async function apiFetch(path, options = {}, { timeout = 30000, slowAfter = 6000, onSlow } = {}) {
  const controller = new AbortController();
  const killTimer = setTimeout(() => controller.abort(), timeout);
  const slowTimer = onSlow ? setTimeout(onSlow, slowAfter) : null;
  try {
    return await fetch(`${API_URL}${path}`, {
      credentials: "include",
      ...options,
      signal: controller.signal,
    });
  } catch (err) {
    if (err.name === "AbortError") {
      throw new ApiError("Sunucu zamanında yanıt vermedi. Bir dakika sonra tekrar dene.");
    }
    throw new ApiError(
      navigator.onLine === false
        ? "İnternet bağlantın yok gibi görünüyor."
        : "Sunucuya ulaşılamadı. Bağlantını kontrol edip tekrar dene.",
    );
  } finally {
    clearTimeout(killTimer);
    clearTimeout(slowTimer);
  }
}

function jsonRequest(method, payload) {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  };
}

async function apiError(response, fallback) {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // gövde JSON değilse durum koduna göre mesaj ver
  }
  if (response.status === 429) return "Çok sık denedin, biraz bekleyip tekrar dene.";
  if (response.status >= 500) return "Sunucu şu an yanıt veremiyor. Birkaç dakika sonra tekrar dene.";
  return fallback;
}

function errorMessage(err, fallback) {
  return err instanceof ApiError ? err.message : fallback;
}

// Destekleyen cihazlarda kısa titreşim; hareket azaltma tercihine saygı gösterir.
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
function haptic(pattern = 12) {
  if (reducedMotion.matches || typeof navigator.vibrate !== "function") return;
  navigator.vibrate(pattern);
}

const SOURCE_LABELS = {
  linkedin: "LinkedIn",
  indeed: "Indeed",
  upwork: "Upwork",
  kariyer: "Kariyer.net",
  eleman: "Eleman.net",
  glassdoor: "Glassdoor",
  remoteok: "RemoteOK",
};

const HEART_ICON =
  '<svg aria-hidden="true" focusable="false" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.29 1.51 4.04 3 5.5l7 7Z"/></svg>';

// --- Toast bildirimi ---
const toastEl = document.getElementById("toast");
let toastTimeout;

function hideToast() {
  clearTimeout(toastTimeout);
  toastEl.classList.remove("is-visible");
  toastTimeout = setTimeout(() => toastEl.classList.add("hidden-field"), 250);
}

function showToast(message, { duration = 2500, action, error = false } = {}) {
  clearTimeout(toastTimeout);
  toastEl.textContent = message;
  toastEl.classList.toggle("is-error", error);
  toastEl.classList.toggle("has-action", Boolean(action));
  if (action) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "toast-action";
    btn.textContent = action.label;
    btn.addEventListener("click", () => {
      hideToast();
      action.onClick();
    });
    toastEl.appendChild(btn);
  }
  if (error) haptic([30, 40, 30]);
  toastEl.classList.remove("hidden-field");
  void toastEl.offsetWidth; // reflow, geçiş animasyonunun çalışması için
  toastEl.classList.add("is-visible");

  toastTimeout = setTimeout(hideToast, action ? Math.max(duration, 5000) : duration);
}

// --- Modal yöneticisi: Escape, geri tuşu, odak tuzağı ---
const modalStack = [];
let skipPopstate = 0;

function focusableIn(el) {
  return [...el.querySelectorAll('a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"])')].filter(
    (node) => !node.disabled && node.offsetParent !== null,
  );
}

function openModal(el, { focus, onClose } = {}) {
  if (modalStack.some((m) => m.el === el)) return;
  modalStack.push({ el, onClose, opener: document.activeElement });
  el.classList.remove("hidden-field");
  document.body.classList.add("modal-open");
  history.pushState({ modal: el.id }, "");
  const items = focusableIn(el);
  (focus || items.find((n) => n.matches("input, textarea")) || items[0] || el).focus();
}

function closeModal(el, { fromHistory = false } = {}) {
  const index = modalStack.findIndex((m) => m.el === el);
  if (index === -1) return;
  const [entry] = modalStack.splice(index, 1);
  el.classList.add("hidden-field");
  if (modalStack.length === 0) document.body.classList.remove("modal-open");
  if (!fromHistory && history.state && history.state.modal === el.id) {
    skipPopstate += 1;
    history.back();
  }
  if (entry.onClose) entry.onClose();
  if (entry.opener && document.contains(entry.opener)) entry.opener.focus();
}

window.addEventListener("popstate", () => {
  if (skipPopstate > 0) {
    skipPopstate -= 1;
    return;
  }
  const top = modalStack[modalStack.length - 1];
  if (top) closeModal(top.el, { fromHistory: true });
});

document.addEventListener("keydown", (e) => {
  const top = modalStack[modalStack.length - 1];
  if (e.key === "Escape") {
    if (top) closeModal(top.el);
    else closeNavMenu();
    return;
  }
  if (e.key === "Tab" && top) {
    const items = focusableIn(top.el);
    if (items.length === 0) return;
    const first = items[0];
    const last = items[items.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }
});

document.querySelectorAll(".modal-overlay").forEach((overlay) => {
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay || e.target.closest("[data-close-modal]")) closeModal(overlay);
  });
});

// Yıkıcı ya da maliyetli işlemlerden önce onay iste; true/false döner.
const confirmModal = document.getElementById("confirm-modal");
const confirmTitle = document.getElementById("confirm-title");
const confirmText = document.getElementById("confirm-text");
const confirmOk = document.getElementById("confirm-ok");
const confirmCancel = document.getElementById("confirm-cancel");

function confirmDialog({ title, message, okText = "Devam et" }) {
  return new Promise((resolve) => {
    let answer = false;
    confirmTitle.textContent = title;
    confirmText.textContent = message;
    confirmOk.textContent = okText;
    confirmOk.onclick = () => {
      answer = true;
      closeModal(confirmModal);
    };
    confirmCancel.onclick = () => closeModal(confirmModal);
    openModal(confirmModal, { focus: confirmCancel, onClose: () => resolve(answer) });
  });
}

// --- Kullanıcı oturumu ---
let currentUser = null;

const authModal = document.getElementById("auth-modal");
const authOpenBtn = document.getElementById("auth-open-btn");
const userMenu = document.getElementById("user-menu");
const userNameLabel = document.getElementById("user-name-label");
const logoutBtn = document.getElementById("logout-btn");
const loginForm = document.getElementById("login-form");
const registerForm = document.getElementById("register-form");
const loginError = document.getElementById("login-error");
const registerError = document.getElementById("register-error");

function openAuthModal() {
  loginForm.reset();
  registerForm.reset();
  openModal(authModal, {
    onClose: () => {
      loginForm.reset();
      registerForm.reset();
      loginError.textContent = "";
      registerError.textContent = "";
    },
  });
}
function closeAuthModal() {
  closeModal(authModal);
}

authOpenBtn.addEventListener("click", openAuthModal);

// --- Mobil hamburger menü ---
const navToggleBtn = document.getElementById("nav-toggle-btn");
const navLinks = document.querySelector(".nav-links");

function closeNavMenu() {
  navToggleBtn.classList.remove("is-open");
  navToggleBtn.setAttribute("aria-expanded", "false");
  navLinks.classList.remove("is-open");
}

navToggleBtn.addEventListener("click", () => {
  const isOpen = navLinks.classList.toggle("is-open");
  navToggleBtn.classList.toggle("is-open", isOpen);
  navToggleBtn.setAttribute("aria-expanded", String(isOpen));
});

navLinks.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", closeNavMenu);
});

document.querySelectorAll(".auth-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".auth-tab").forEach((t) => t.classList.remove("is-active"));
    tab.classList.add("is-active");
    const isLogin = tab.dataset.tab === "login";
    loginForm.classList.toggle("hidden-field", !isLogin);
    registerForm.classList.toggle("hidden-field", isLogin);
  });
});

function updateAuthUI() {
  if (currentUser) {
    authOpenBtn.classList.add("hidden-field");
    userMenu.classList.remove("hidden-field");
    userNameLabel.textContent = currentUser.name || currentUser.email;
  } else {
    authOpenBtn.classList.remove("hidden-field");
    userMenu.classList.add("hidden-field");
  }
  const canRefresh = Boolean(currentUser && currentUser.can_refresh);
  document.getElementById("refresh-form").classList.toggle("hidden-field", !canRefresh);
  document.getElementById("refresh-locked").classList.toggle("hidden-field", canRefresh);
}

async function loadCurrentUser() {
  try {
    const response = await apiFetch("/auth/me", {}, { timeout: 20000 });
    const data = await response.json();
    currentUser = data.logged_in ? data : null;
  } catch (err) {
    currentUser = null;
  }
  updateAuthUI();
}

loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  loginError.textContent = "";
  const email = document.getElementById("login-email").value;
  const password = document.getElementById("login-password").value;

  try {
    const response = await apiFetch("/auth/login", jsonRequest("POST", { email, password }), {
      onSlow: () => (loginError.textContent = SLOW_SERVER_MESSAGE),
    });
    if (!response.ok) {
      loginError.textContent = await apiError(response, "Giriş yapılamadı.");
      return;
    }
    currentUser = await response.json();
    updateAuthUI();
    closeAuthModal();
    loadFavorites();
    showToast(`Tekrar hoş geldin, ${currentUser.name || currentUser.email}!`);
  } catch (err) {
    loginError.textContent = errorMessage(err, "Giriş yapılamadı, tekrar dene.");
  }
});

registerForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  registerError.textContent = "";
  const name = document.getElementById("register-name").value;
  const email = document.getElementById("register-email").value;
  const password = document.getElementById("register-password").value;

  try {
    const response = await apiFetch("/auth/register", jsonRequest("POST", { name, email, password }), {
      onSlow: () => (registerError.textContent = SLOW_SERVER_MESSAGE),
    });
    if (!response.ok) {
      registerError.textContent = await apiError(response, "Kayıt oluşturulamadı.");
      return;
    }
    currentUser = await response.json();
    updateAuthUI();
    closeAuthModal();
    loadFavorites();
    showToast(`Hoş geldin, ${currentUser.name || currentUser.email}!`);
  } catch (err) {
    registerError.textContent = errorMessage(err, "Kayıt oluşturulamadı, tekrar dene.");
  }
});

function resetSession() {
  currentUser = null;
  favJobs = [];
  favoriteIds.clear();
  updateAuthUI();
  renderFavorites();
  syncFavoriteButtons();
}

logoutBtn.addEventListener("click", async () => {
  try {
    await apiFetch("/auth/logout", { method: "POST" }, { timeout: 10000 });
  } catch (err) {
    // sunucuya ulaşılamasa da bu cihazdaki oturum görünümünü kapat
  }
  resetSession();
  showToast("Çıkış yaptın.");
});

// --- Hesabım / hesabı sil ---
const accountModal = document.getElementById("account-modal");
const accountEmail = document.getElementById("account-email");
const deleteForm = document.getElementById("delete-form");
const deleteConfirmInput = document.getElementById("delete-confirm");
const deleteBtn = document.getElementById("delete-btn");
const deleteError = document.getElementById("delete-error");

userNameLabel.addEventListener("click", () => {
  if (!currentUser) return;
  accountEmail.textContent = currentUser.email || currentUser.name || "";
  deleteForm.reset();
  deleteBtn.disabled = true;
  deleteError.textContent = "";
  openModal(accountModal);
});

deleteConfirmInput.addEventListener("input", () => {
  const typed = deleteConfirmInput.value.trim().toLowerCase();
  deleteBtn.disabled = !currentUser || typed !== (currentUser.email || "").toLowerCase();
});

deleteForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  deleteError.textContent = "";
  deleteBtn.disabled = true;
  deleteBtn.classList.add("is-loading");
  try {
    const response = await apiFetch("/auth/delete-account", jsonRequest("POST", { confirm_email: deleteConfirmInput.value }));
    if (!response.ok) {
      deleteError.textContent = await apiError(response, "Hesap silinemedi, tekrar dene.");
      deleteBtn.disabled = false;
      return;
    }
    closeModal(accountModal);
    resetSession();
    showToast("Hesabın ve favorilerin silindi. Yolun açık olsun, yolcu.", { duration: 5000 });
  } catch (err) {
    deleteError.textContent = errorMessage(err, "Hesap silinemedi, tekrar dene.");
    deleteBtn.disabled = false;
  } finally {
    deleteBtn.classList.remove("is-loading");
  }
});

// --- Kaydırınca beliren (scroll reveal) efekt ---
const revealElements = document.querySelectorAll(".reveal");

const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("visible");
        observer.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.15 },
);

revealElements.forEach((el) => observer.observe(el));

// --- CV dosyası yükleme ---
const cvFileInput = document.getElementById("cv-file");
const profileTextArea = document.getElementById("profile-text");
const cvStatus = document.getElementById("cv-status");

cvFileInput.addEventListener("change", async () => {
  const file = cvFileInput.files[0];
  if (!file) return;
  document.getElementById("file-name").textContent = file.name;

  const formData = new FormData();
  formData.append("file", file);

  cvStatus.textContent = "PDF okunuyor...";

  try {
    const response = await apiFetch(
      "/extract-text",
      { method: "POST", body: formData },
      { timeout: 45000, onSlow: () => (cvStatus.textContent = SLOW_SERVER_MESSAGE) },
    );
    if (!response.ok) {
      throw new ApiError(await apiError(response, "PDF okunamadı. Metin içeren bir PDF olduğundan emin ol."));
    }
    const data = await response.json();
    profileTextArea.value = data.text;
    cvStatus.textContent = `✓ CV okundu (${data.text.length} karakter)`;
  } catch (err) {
    profileTextArea.value = "";
    cvStatus.textContent = errorMessage(err, "PDF okunamadı. Metin içeren bir PDF olduğundan emin ol.");
  }
});

// --- "Yenile" butonu: yeni ilan çek ---
const refreshBtn = document.getElementById("refresh-btn");
const refreshStatus = document.getElementById("refresh-status");

refreshBtn.addEventListener("click", async () => {
  if (!currentUser || !currentUser.can_refresh) {
    showToast("Yeni ilan çekme yalnızca site sahibine açık.");
    return;
  }

  const keywordsInput = document.getElementById("keywords");
  const keywords = keywordsInput.value.trim();
  const location = document.getElementById("scrape-location").value.trim();
  if (!keywords) {
    refreshStatus.textContent = 'Önce bir anahtar kelime yaz, örneğin "data scientist".';
    keywordsInput.focus();
    return;
  }

  const ok = await confirmDialog({
    title: "Yeni ilanlar çekilsin mi?",
    message:
      "Yedi platform canlı taranır ve ücretli bir servis kullanılır. Birkaç dakika sürer; saatte en fazla 3 kez yapabilirsin.",
    okText: "Taramayı başlat",
  });
  if (!ok) return;

  refreshBtn.disabled = true;
  refreshBtn.classList.add("is-loading");
  refreshStatus.textContent = "Taranıyor, birkaç dakika sürebilir...";

  try {
    const response = await apiFetch("/refresh", jsonRequest("POST", location ? { keywords, location } : { keywords }), {
      timeout: 15 * 60 * 1000,
    });
    if (!response.ok) {
      throw new ApiError(await apiError(response, "Tarama tamamlanamadı, birazdan tekrar dene."));
    }
    const data = await response.json();
    refreshStatus.textContent =
      data.inserted === 0
        ? "Yeni ilan çıkmadı; bu aramadaki ilanların hepsi zaten kayıtlıydı."
        : `${data.inserted} yeni ilan eklendi.`;
    haptic(15);
  } catch (err) {
    refreshStatus.textContent = errorMessage(err, "Tarama tamamlanamadı, birazdan tekrar dene.");
    haptic([30, 40, 30]);
  }

  refreshBtn.disabled = false;
  refreshBtn.classList.remove("is-loading");
});

// --- Favoriler: paylaşılan durum ---
const favoriteIds = new Set();
let favJobs = [];
const favoritesList = document.getElementById("favorites-list");

async function loadFavorites() {
  try {
    const response = await apiFetch("/favorites", {}, { timeout: 20000 });
    if (!response.ok) return;
    favJobs = await response.json();
    favoriteIds.clear();
    favJobs.forEach((job) => favoriteIds.add(job.id));
    renderFavorites();
  } catch (err) {
    // Sunucu henüz hazır olmayabilir, sessizce geç.
  }
}

function setFavoriteLocal(jobId, makeFavorite, job) {
  if (makeFavorite) {
    favoriteIds.add(jobId);
    const source = job || lastJobs.find((j) => j.id === jobId) || favJobs.find((j) => j.id === jobId);
    if (source && !favJobs.some((j) => j.id === jobId)) {
      favJobs = [{ ...source }, ...favJobs];
    }
  } else {
    favoriteIds.delete(jobId);
    favJobs = favJobs.filter((j) => j.id !== jobId);
  }
  syncFavoriteButtons();
  renderFavorites();
}

// Önce arayüz güncellenir; sunucu reddederse eski haline döner ve kullanıcıya söylenir.
async function toggleFavorite(jobId, makeFavorite) {
  const job = lastJobs.find((j) => j.id === jobId) || favJobs.find((j) => j.id === jobId);
  setFavoriteLocal(jobId, makeFavorite, job);

  try {
    const response = await apiFetch("/favorite", jsonRequest("POST", { job_id: jobId, favorite: makeFavorite }), {
      timeout: 15000,
    });
    if (!response.ok) {
      throw new ApiError(await apiError(response, "Favori kaydedilemedi, tekrar dene."));
    }
  } catch (err) {
    setFavoriteLocal(jobId, !makeFavorite, job);
    showToast(errorMessage(err, "Favori kaydedilemedi, tekrar dene."), { error: true });
    return;
  }

  haptic(12);
  if (!makeFavorite) {
    showToast("Hazinenden çıkarıldı.", {
      action: { label: "Geri al", onClick: () => toggleFavorite(jobId, true) },
    });
  }
}

function syncFavoriteButtons() {
  document.querySelectorAll(".favorite-btn").forEach((btn) => {
    const isFav = favoriteIds.has(btn.dataset.jobId);
    btn.classList.toggle("is-favorite", isFav);
    btn.setAttribute("aria-pressed", isFav ? "true" : "false");
  });
}

function renderFavorites() {
  if (!currentUser) {
    favoritesList.innerHTML =
      '<p class="empty-state">Hazineni saklamak için önce kapıdan içeri gir (giriş yap).</p>';
    return;
  }
  if (favJobs.length === 0) {
    favoritesList.innerHTML =
      '<p class="empty-state">Sandığın henüz boş, yolcu. Sonuçlardaki kalp ikonuna basarak hazinene ekle.</p>';
    return;
  }
  favoritesList.innerHTML = favJobs.map((job) => jobCardHtml(job, { showScore: false })).join("");
}

// --- Ortak ilan kartı şablonu ---
function jobCardHtml(job, { index, showScore = true, enterDelay } = {}) {
  const isFav = favoriteIds.has(job.id);
  const scoreHtml =
    showScore && typeof job.score === "number"
      ? `<span class="job-score">Uyum: %${Math.round(job.score * 100)}</span>`
      : "";
  const coverLetterBtn =
    index !== undefined
      ? `<button class="cover-letter-btn" data-index="${index}">Ön Yazı Oluştur</button>`
      : "";
  const coverLetterOutput = index !== undefined ? `<div class="cover-letter-output" id="cover-letter-${index}"></div>` : "";

  return `
    <div class="job-card${enterDelay !== undefined ? " card-enter" : ""}" data-job-id="${escapeHtml(job.id)}"${enterDelay !== undefined ? ` style="--enter-delay:${enterDelay}ms"` : ""}>
      <div class="job-top-row">
        <span class="job-title">${escapeHtml(job.title)}</span>
        <span class="job-tag">${escapeHtml(SOURCE_LABELS[job.source] || job.source)}</span>
        <button type="button" class="favorite-btn ${isFav ? "is-favorite" : ""}" data-job-id="${escapeHtml(job.id)}" aria-pressed="${isFav ? "true" : "false"}" aria-label="Favorilere ekle/çıkar" title="Favorilere ekle/çıkar">
          ${HEART_ICON}
        </button>
      </div>
      <div class="job-meta">${escapeHtml(job.company || "Bilinmiyor")} · ${escapeHtml(job.location || "Belirtilmemiş")}</div>
      <div class="job-bottom-row">
        ${scoreHtml}
        <a href="${escapeHtml(safeUrl(job.url))}" target="_blank" rel="noopener noreferrer" class="job-link">İlana git →</a>
        ${coverLetterBtn}
      </div>
      ${coverLetterOutput}
    </div>
  `;
}

// --- "Öner" butonu: uygun ilanları getir ---
const recommendBtn = document.getElementById("recommend-btn");
const resultsList = document.getElementById("results-list");

let lastJobs = [];
const PAGE_SIZE = 10;
let visibleCount = PAGE_SIZE;

recommendBtn.addEventListener("click", async () => {
  const profileText = document.getElementById("profile-text").value;
  if (!profileText.trim()) {
    resultsList.innerHTML = '<p class="empty-state">Önce yukarıdan bir CV dosyası (PDF) yükle.</p>';
    return;
  }

  resultsList.innerHTML = '<p class="empty-state">Diyarlar taranıyor...</p>';
  recommendBtn.disabled = true;
  recommendBtn.classList.add("is-loading");

  const location = document.getElementById("recommend-location").value;

  try {
    const response = await apiFetch("/recommend", jsonRequest("POST", { profile_text: profileText, top_n: 50, location }), {
      timeout: 90000,
      onSlow: () => {
        resultsList.innerHTML = `<p class="empty-state">${SLOW_SERVER_MESSAGE}</p>`;
      },
    });
    if (!response.ok) {
      throw new ApiError(await apiError(response, "Öneriler getirilemedi, tekrar dene."));
    }
    const jobs = await response.json();
    lastJobs = jobs;
    visibleCount = PAGE_SIZE;
    renderResults(0);
  } catch (err) {
    resultsList.innerHTML = `<p class="empty-state" role="alert">${escapeHtml(errorMessage(err, "Öneriler getirilemedi, tekrar dene."))}</p>`;
  } finally {
    recommendBtn.disabled = false;
    recommendBtn.classList.remove("is-loading");
  }
});

function renderResults(animateFrom = 0) {
  if (lastJobs.length === 0) {
    resultsList.innerHTML =
      '<p class="empty-state">Bu CV için uygun ilan bulunamadı. Konumu boş bırakmayı ya da önce "Yenile" ile yeni ilan çekmeyi dene.</p>';
    return;
  }

  const visibleJobs = lastJobs.slice(0, visibleCount);

  const cardsHtml = visibleJobs
    .map((job, index) =>
      jobCardHtml(job, {
        index,
        showScore: true,
        enterDelay: index >= animateFrom ? Math.min(index - animateFrom, 10) * 45 : undefined,
      }),
    )
    .join("");

  const remaining = lastJobs.length - visibleCount;
  const loadMoreHtml =
    remaining > 0
      ? `<button id="load-more-btn" class="btn btn-outline">Daha Fazla Göster (${remaining} kaldı)</button>`
      : "";

  resultsList.innerHTML = cardsHtml + loadMoreHtml;
}

// --- "Ön Yazı Oluştur" / "PDF Olarak İndir" / "Daha Fazla Göster" / favori butonları ---
async function handleListClick(e) {
  const favoriteBtn = e.target.closest(".favorite-btn");
  if (favoriteBtn) {
    if (!currentUser) {
      showToast("Favorilere eklemek için önce giriş yapmalısın.");
      openAuthModal();
      return;
    }
    const jobId = favoriteBtn.dataset.jobId;
    const makeFavorite = !favoriteIds.has(jobId);
    toggleFavorite(jobId, makeFavorite);
    return;
  }

  if (e.target.id === "load-more-btn") {
    const previous = visibleCount;
    visibleCount += PAGE_SIZE;
    renderResults(previous);
    return;
  }

  if (e.target.classList.contains("cover-letter-btn")) {
    const index = e.target.dataset.index;
    const job = lastJobs[index];
    const outputEl = document.getElementById(`cover-letter-${index}`);
    const profileText = document.getElementById("profile-text").value;

    e.target.disabled = true;
    e.target.classList.add("is-loading");
    outputEl.innerHTML = "";
    outputEl.textContent = "Ön yazı oluşturuluyor...";

    try {
      const response = await apiFetch(
        "/cover-letter",
        jsonRequest("POST", {
          profile_text: profileText,
          job_title: job.title,
          company: job.company,
          job_description: (job.description || "").slice(0, 25000),
        }),
        { timeout: 60000, onSlow: () => (outputEl.textContent = "Yapay zekâ ön yazıyı hazırlıyor, biraz sürebilir…") },
      );
      if (!response.ok) {
        throw new ApiError(await apiError(response, "Ön yazı oluşturulamadı. Birkaç saniye sonra tekrar dene."));
      }
      const data = await response.json();

      outputEl.innerHTML = "";
      const textarea = document.createElement("textarea");
      textarea.className = "cover-letter-edit";
      textarea.value = data.text;

      const downloadBtn = document.createElement("button");
      downloadBtn.className = "download-pdf-btn";
      downloadBtn.textContent = "PDF Olarak İndir";
      downloadBtn.dataset.index = index;
      downloadBtn.dataset.fileName = data.file_name || "on_yazi";

      outputEl.appendChild(textarea);
      outputEl.appendChild(downloadBtn);
      haptic(15);
    } catch (err) {
      outputEl.textContent = errorMessage(err, "Ön yazı oluşturulamadı. Birkaç saniye sonra tekrar dene.");
    }

    e.target.disabled = false;
    e.target.classList.remove("is-loading");
    return;
  }

  if (e.target.classList.contains("download-pdf-btn")) {
    const textarea = e.target.previousElementSibling;
    const text = textarea.value;
    const job = lastJobs[e.target.dataset.index];
    const fileName = e.target.dataset.fileName || "on_yazi";

    e.target.disabled = true;
    e.target.textContent = "Hazırlanıyor...";

    try {
      const response = await apiFetch(
        "/cover-letter-pdf",
        jsonRequest("POST", { text, job_title: job.title, company: job.company, file_name: fileName }),
        { timeout: 30000 },
      );
      if (!response.ok) {
        throw new ApiError(await apiError(response, "PDF hazırlanamadı. Metni kısaltıp tekrar dene."));
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${fileName}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      showToast(errorMessage(err, "PDF hazırlanamadı. Metni kısaltıp tekrar dene."), { error: true });
    }

    e.target.disabled = false;
    e.target.textContent = "PDF Olarak İndir";
  }
}

resultsList.addEventListener("click", handleListClick);
favoritesList.addEventListener("click", handleListClick);

// --- CV İncele ---
const cvReviewFileInput = document.getElementById("cv-review-file");
const cvReviewFileName = document.getElementById("cv-review-file-name");
const cvReviewStatus = document.getElementById("cv-review-status");
const cvReviewBtn = document.getElementById("cv-review-btn");
const cvReviewResult = document.getElementById("cv-review-result");
const cvReviewOverallScore = document.getElementById("cv-review-overall-score");
const cvReviewSummary = document.getElementById("cv-review-summary");
const cvReviewCategories = document.getElementById("cv-review-categories");
const cvReviewStrengthsList = document.getElementById("cv-review-strengths-list");
const cvReviewImprovementsList = document.getElementById("cv-review-improvements-list");

function scoreClass(score) {
  if (score >= 75) return "is-good";
  if (score >= 50) return "is-mid";
  return "is-low";
}

cvReviewFileInput.addEventListener("change", () => {
  const file = cvReviewFileInput.files[0];
  cvReviewFileName.textContent = file ? file.name : "Dosya seçilmedi";
  cvReviewStatus.textContent = "";
  cvReviewResult.classList.add("hidden-field");
});

cvReviewBtn.addEventListener("click", async () => {
  const file = cvReviewFileInput.files[0];
  if (!file) {
    cvReviewStatus.textContent = "Önce bir PDF seç.";
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  cvReviewBtn.disabled = true;
  cvReviewBtn.classList.add("is-loading");
  cvReviewStatus.textContent = "CV'n inceleniyor, birkaç saniye sürebilir...";
  cvReviewResult.classList.add("hidden-field");

  try {
    const response = await apiFetch(
      "/cv-review",
      { method: "POST", body: formData },
      { timeout: 90000, onSlow: () => (cvReviewStatus.textContent = SLOW_SERVER_MESSAGE) },
    );
    if (!response.ok) {
      throw new ApiError(await apiError(response, "CV incelenemedi, birazdan tekrar dene."));
    }
    const review = await response.json();

    cvReviewOverallScore.textContent = review.overall_score;
    cvReviewOverallScore.parentElement.className =
      "cv-review-score-ring " + scoreClass(review.overall_score);
    cvReviewSummary.textContent = review.summary;

    const CATEGORY_LABELS = ["ATS Uyumluluğu", "İçerik Etkisi", "Format ve Okunabilirlik"];
    cvReviewCategories.innerHTML = review.categories
      .map(
        (cat, i) => `
      <div class="cv-review-category">
        <div class="cv-review-category-head">
          <span>${escapeHtml(CATEGORY_LABELS[i] || cat.name)}</span>
          <span>${cat.score}/100</span>
        </div>
        <div class="cv-review-bar">
          <div class="cv-review-bar-fill ${scoreClass(cat.score)}" style="width:${cat.score}%"></div>
        </div>
        <p>${escapeHtml(cat.comment)}</p>
      </div>
    `,
      )
      .join("");

    cvReviewStrengthsList.innerHTML = review.strengths
      .map((s) => `<li>${escapeHtml(s)}</li>`)
      .join("");
    cvReviewImprovementsList.innerHTML = review.improvements
      .map((s) => `<li>${escapeHtml(s)}</li>`)
      .join("");

    cvReviewStatus.textContent = "";
    cvReviewResult.classList.remove("hidden-field");
  } catch (err) {
    cvReviewStatus.textContent = errorMessage(err, "CV incelenemedi, birazdan tekrar dene.");
  }

  cvReviewBtn.disabled = false;
  cvReviewBtn.classList.remove("is-loading");
});

if (new URLSearchParams(window.location.search).get("login") === "failed") {
  showToast("Google ile giriş yapılamadı, tekrar dene.", { duration: 4000, error: true });
  window.history.replaceState({}, "", window.location.pathname);
}

loadCurrentUser().then(() => {
  if (currentUser) {
    loadFavorites();
  } else {
    renderFavorites();
  }
});
