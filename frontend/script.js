const API_URL = "";

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
  '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.29 1.51 4.04 3 5.5l7 7Z"/></svg>';

// --- Toast bildirimi ---
const toastEl = document.getElementById("toast");
let toastTimeout;

function showToast(message, duration = 2500) {
  clearTimeout(toastTimeout);
  toastEl.textContent = message;
  toastEl.classList.remove("hidden-field");
  void toastEl.offsetWidth; // reflow, geçiş animasyonunun çalışması için
  toastEl.classList.add("is-visible");

  toastTimeout = setTimeout(() => {
    toastEl.classList.remove("is-visible");
    setTimeout(() => toastEl.classList.add("hidden-field"), 250);
  }, duration);
}

// --- Kullanıcı oturumu ---
let currentUser = null;

const authModal = document.getElementById("auth-modal");
const authOpenBtn = document.getElementById("auth-open-btn");
const authModalClose = document.getElementById("auth-modal-close");
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
  authModal.classList.remove("hidden-field");
}
function closeAuthModal() {
  authModal.classList.add("hidden-field");
  loginForm.reset();
  registerForm.reset();
  loginError.textContent = "";
  registerError.textContent = "";
}

authOpenBtn.addEventListener("click", openAuthModal);
authModalClose.addEventListener("click", closeAuthModal);
authModal.addEventListener("click", (e) => {
  if (e.target === authModal) closeAuthModal();
});

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
}

async function loadCurrentUser() {
  try {
    const response = await fetch(`${API_URL}/auth/me`, { credentials: "include" });
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
    const response = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await response.json();
    if (!response.ok) {
      loginError.textContent = data.detail || "Giriş yapılamadı.";
      return;
    }
    currentUser = data;
    updateAuthUI();
    closeAuthModal();
    loadFavorites();
    showToast(`Tekrar hoş geldin, ${currentUser.name || currentUser.email}!`);
  } catch (err) {
    loginError.textContent = "Bir hata oluştu, sunucuyu kontrol et.";
  }
});

registerForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  registerError.textContent = "";
  const name = document.getElementById("register-name").value;
  const email = document.getElementById("register-email").value;
  const password = document.getElementById("register-password").value;

  try {
    const response = await fetch(`${API_URL}/auth/register`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, password }),
    });
    const data = await response.json();
    if (!response.ok) {
      registerError.textContent = data.detail || "Kayıt oluşturulamadı.";
      return;
    }
    currentUser = data;
    updateAuthUI();
    closeAuthModal();
    loadFavorites();
    showToast(`Hoş geldin, ${currentUser.name || currentUser.email}!`);
  } catch (err) {
    registerError.textContent = "Bir hata oluştu, sunucuyu kontrol et.";
  }
});

logoutBtn.addEventListener("click", async () => {
  try {
    await fetch(`${API_URL}/auth/logout`, { method: "POST", credentials: "include" });
  } catch (err) {
    // yok say
  }
  currentUser = null;
  favJobs = [];
  favoriteIds.clear();
  updateAuthUI();
  renderFavorites();
  syncFavoriteButtons();
  showToast("Çıkış yaptınız.");
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
    const response = await fetch(`${API_URL}/extract-text`, {
      method: "POST",
      body: formData,
    });
    const data = await response.json();
    profileTextArea.value = data.text;
    cvStatus.textContent = `✓ CV okundu (${data.text.length} karakter)`;
  } catch (err) {
    profileTextArea.value = "";
    cvStatus.textContent = "PDF okunamadı, dosyayı kontrol et.";
  }
});

// --- "Yenile" butonu: yeni ilan çek ---
const refreshBtn = document.getElementById("refresh-btn");
const refreshStatus = document.getElementById("refresh-status");

refreshBtn.addEventListener("click", async () => {
  const keywords = document.getElementById("keywords").value;
  const location = document.getElementById("scrape-location").value;

  refreshBtn.disabled = true;
  refreshStatus.textContent = "Taranıyor, birkaç dakika sürebilir...";

  try {
    const response = await fetch(`${API_URL}/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keywords, location }),
    });
    const data = await response.json();
    refreshStatus.textContent = `${data.inserted} yeni ilan eklendi.`;
  } catch (err) {
    refreshStatus.textContent =
      "Bir hata oluştu, sunucunun çalıştığından emin ol.";
  }

  refreshBtn.disabled = false;
});

// --- Favoriler: paylaşılan durum ---
const favoriteIds = new Set();
let favJobs = [];
const favoritesList = document.getElementById("favorites-list");

async function loadFavorites() {
  try {
    const response = await fetch(`${API_URL}/favorites`);
    favJobs = await response.json();
    favoriteIds.clear();
    favJobs.forEach((job) => favoriteIds.add(job.id));
    renderFavorites();
  } catch (err) {
    // Sunucu henüz hazır olmayabilir, sessizce geç.
  }
}

async function toggleFavorite(jobId, makeFavorite) {
  try {
    await fetch(`${API_URL}/favorite`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_id: jobId, favorite: makeFavorite }),
    });
  } catch (err) {
    // Ağ hatası olsa da yerel durumu güncellemeye devam ediyoruz.
  }

  if (makeFavorite) {
    favoriteIds.add(jobId);
    const job = lastJobs.find((j) => j.id === jobId) || favJobs.find((j) => j.id === jobId);
    if (job && !favJobs.some((j) => j.id === jobId)) {
      favJobs = [{ ...job }, ...favJobs];
    }
  } else {
    favoriteIds.delete(jobId);
    favJobs = favJobs.filter((j) => j.id !== jobId);
  }

  syncFavoriteButtons();
  renderFavorites();
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
function jobCardHtml(job, { index, showScore = true } = {}) {
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
    <div class="job-card" data-job-id="${job.id}">
      <div class="job-top-row">
        <span class="job-title">${job.title}</span>
        <span class="job-tag">${SOURCE_LABELS[job.source] || job.source}</span>
        <button type="button" class="favorite-btn ${isFav ? "is-favorite" : ""}" data-job-id="${job.id}" aria-pressed="${isFav ? "true" : "false"}" aria-label="Favorilere ekle/çıkar" title="Favorilere ekle/çıkar">
          ${HEART_ICON}
        </button>
      </div>
      <div class="job-meta">${job.company || "Bilinmiyor"} · ${job.location || "Belirtilmemiş"}</div>
      <div class="job-bottom-row">
        ${scoreHtml}
        <a href="${job.url}" target="_blank" class="job-link">İlana git →</a>
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
    resultsList.innerHTML = "<p>Önce bir CV dosyası yükle.</p>";
    return;
  }

  resultsList.innerHTML = "<p>Diyarlar taranıyor...</p>";

  const location = document.getElementById("recommend-location").value;

  try {
    const response = await fetch(`${API_URL}/recommend`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profile_text: profileText, top_n: 50, location }),
    });
    const jobs = await response.json();
    lastJobs = jobs;
    visibleCount = PAGE_SIZE;
    renderResults();
  } catch (err) {
    resultsList.innerHTML =
      "<p>Bir hata oluştu, sunucunun çalıştığından emin ol.</p>";
  }
});

function renderResults() {
  if (lastJobs.length === 0) {
    resultsList.innerHTML = "<p>Bu diyarlarda uygun bir fırsat bulunamadı.</p>";
    return;
  }

  const visibleJobs = lastJobs.slice(0, visibleCount);

  const cardsHtml = visibleJobs
    .map((job, index) => jobCardHtml(job, { index, showScore: true }))
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
      openAuthModal();
      return;
    }
    const jobId = favoriteBtn.dataset.jobId;
    const makeFavorite = !favoriteIds.has(jobId);
    toggleFavorite(jobId, makeFavorite);
    return;
  }

  if (e.target.id === "load-more-btn") {
    visibleCount += PAGE_SIZE;
    renderResults();
    return;
  }

  if (e.target.classList.contains("cover-letter-btn")) {
    const index = e.target.dataset.index;
    const job = lastJobs[index];
    const outputEl = document.getElementById(`cover-letter-${index}`);
    const profileText = document.getElementById("profile-text").value;

    e.target.disabled = true;
    outputEl.innerHTML = "";
    outputEl.textContent = "Ön yazı oluşturuluyor...";

    try {
      const response = await fetch(`${API_URL}/cover-letter`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          profile_text: profileText,
          job_title: job.title,
          company: job.company,
          job_description: job.description,
        }),
      });
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
    } catch (err) {
      outputEl.textContent = "Ön yazı oluşturulamadı, sunucuyu kontrol et.";
    }

    e.target.disabled = false;
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
      const response = await fetch(`${API_URL}/cover-letter-pdf`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text,
          job_title: job.title,
          company: job.company,
          file_name: fileName,
        }),
      });
      if (!response.ok) {
        throw new Error("PDF üretilemedi");
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${fileName}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert("PDF oluşturulamadı, sunucuyu kontrol et.");
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

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
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
  cvReviewStatus.textContent = "CV'n inceleniyor, birkaç saniye sürebilir...";
  cvReviewResult.classList.add("hidden-field");

  try {
    const response = await fetch(`${API_URL}/cv-review`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || "İnceleme başarısız oldu.");
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
    cvReviewStatus.textContent = err.message || "İnceleme başarısız oldu.";
  }

  cvReviewBtn.disabled = false;
});

loadCurrentUser().then(() => {
  if (currentUser) {
    loadFavorites();
  } else {
    renderFavorites();
  }
});
