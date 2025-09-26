// ============ CONFIG ============
const PARSE_ENDPOINT = "/parse"; // Flask route

// ============ SELECTORS ============
const fileInput = document.getElementById("fileInput");
const clearBtn = document.getElementById("clearBtn");
const uploadCard = document.getElementById("uploadCard");
const progressBar = document.getElementById("progressBar");
const progressWrap = document.querySelector(".progress");
const statusSmall = document.getElementById("status-small");

const noData = document.getElementById("noData");
const results = document.getElementById("results");

// ============ HELPERS ============
function setStatus(text) {
  statusSmall.textContent = text;
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, c => ({
    "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"
  }[c]));
}

function truncate(s, n = 300) {
  return s.length > n ? s.slice(0, n) + "…" : s;
}

function clearResults() {
  noData.style.display = "";
  results.style.display = "none";
  results.innerHTML = "";
  results.classList.remove("multiple");
  setStatus("idle");
  progressBar.style.width = "0%";
  progressBar.style.animation = "none"; // stop gradient animation
}

// Show alert for errors
function showError(msg) {
  setStatus("error");
  progressWrap.style.visibility = "hidden";
  alert(msg);
  clearResults();
}

// ============ RENDER RESULTS ============
function renderResults(data) {
  clearResults();

  if (!Array.isArray(data) || data.length === 0) {
    return showError("No parsed resumes returned.");
  }

  noData.style.display = "none";
  results.style.display = "";

  if (data.length >= 2) {
    results.classList.add("multiple");
  }

  data.forEach(resume => {
    const card = document.createElement("div");
    card.className = "card";

    let contactHTML = `
      <div class="section-title">Contact - ${escapeHtml(resume.filename || "Unknown")}</div>
      <div class="contact-row">
        <span class="badge">Name: ${escapeHtml(resume.contact?.name || "N/A")}</span>
        <span class="badge">Email: ${escapeHtml(resume.contact?.email || "N/A")}</span>
        <span class="badge">Phone: ${escapeHtml(resume.contact?.phone || "N/A")}</span>
      </div>
    `;

    let sectionsHTML = `<div class="section-title">Sections</div>`;
    if (resume.sections && Object.keys(resume.sections).length > 0) {
      Object.entries(resume.sections).forEach(([key, value]) => {
        const isOCR = key.toLowerCase().includes("ocr");
        sectionsHTML += `
          <div>
            <strong>${escapeHtml(key)}</strong>:
            <div class="mini muted" style="${isOCR ? 'background-color:#fff7e6;padding:3px;border-left:3px solid #ffa500;' : ''}">
              ${truncate(escapeHtml(value || ""), 1000)}
            </div>
          </div>
        `;
      });
    } else {
      sectionsHTML += `<div class="muted mini">No sections found</div>`;
    }

    card.innerHTML = contactHTML + sectionsHTML;
    results.appendChild(card);
  });

  progressWrap.style.visibility = "hidden";
  setStatus("parsed");
}

// ============ UPLOAD FILES ============
function uploadFiles(files) {
  clearResults();
  setStatus("uploading");
  progressWrap.style.visibility = "visible";
  progressBar.style.width = "0%";
  progressBar.style.animation = "moveGradient 1s linear infinite"; // start striped animation

  const formData = new FormData();
  for (let i = 0; i < files.length; i++) formData.append("file", files[i]);

  const xhr = new XMLHttpRequest();
  xhr.open("POST", PARSE_ENDPOINT, true);

  xhr.upload.onprogress = function(e) {
    if (e.lengthComputable) {
      let percent = (e.loaded / e.total) * 100;
      progressBar.style.width = percent + "%";
    }
  };

  xhr.onload = function() {
    if (xhr.status === 200) {
      progressBar.style.width = "100%";
      progressBar.style.animation = "none"; // stop moving gradient
      const data = JSON.parse(xhr.responseText);
      renderResults(data);
    } else {
      showError("Upload failed with status: " + xhr.status);
    }
  };

  xhr.onerror = function() {
    showError("Upload failed: network error");
  };

  xhr.send(formData);
}

// ============ EVENTS ============
uploadCard.addEventListener("dragover", e => {
  e.preventDefault();
  uploadCard.classList.add("dragover");
});

uploadCard.addEventListener("dragleave", () => uploadCard.classList.remove("dragover"));

uploadCard.addEventListener("drop", e => {
  e.preventDefault();
  uploadCard.classList.remove("dragover");
  const files = e.dataTransfer.files;
  if (files.length) uploadFiles(files);
});

fileInput.addEventListener("change", () => {
  if (fileInput.files.length) uploadFiles(fileInput.files);
});

clearBtn.addEventListener("click", () => {
  fileInput.value = "";
  clearResults();
});