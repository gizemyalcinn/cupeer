const API_URL = "http://127.0.0.1:8000";

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

  resultsList.innerHTML = "<p>Aranıyor...</p>";

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
    resultsList.innerHTML = "<p>Sonuç bulunamadı.</p>";
    return;
  }

  const visibleJobs = lastJobs.slice(0, visibleCount);

  const cardsHtml = visibleJobs
    .map(
      (job, index) => `
      <div class="job-card">
        <div class="job-top-row">
          <span class="job-title">${job.title}</span>
          <span class="job-tag">${job.source}</span>
        </div>
        <div class="job-meta">${job.company || "Bilinmiyor"} · ${job.location || "Belirtilmemiş"}</div>
        <div class="job-bottom-row">
          <span class="job-score">Uyum: %${Math.round(job.score * 100)}</span>
          <a href="${job.url}" target="_blank" class="job-link">İlana git →</a>
          <button class="cover-letter-btn" data-index="${index}">Ön Yazı Oluştur</button>
        </div>
        <div class="cover-letter-output" id="cover-letter-${index}"></div>
      </div>
    `,
    )
    .join("");

  const remaining = lastJobs.length - visibleCount;
  const loadMoreHtml =
    remaining > 0
      ? `<button id="load-more-btn" class="btn btn-outline">Daha Fazla Göster (${remaining} kaldı)</button>`
      : "";

  resultsList.innerHTML = cardsHtml + loadMoreHtml;
}

// --- "Ön Yazı Oluştur" / "PDF Olarak İndir" / "Daha Fazla Göster" butonları ---
resultsList.addEventListener("click", async (e) => {
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
});
