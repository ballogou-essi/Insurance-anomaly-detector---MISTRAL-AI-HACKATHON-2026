let selectedFile = null;
let lastResult = null;

const $ = (id) => document.getElementById(id);

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function typeText(el, text, speed = 35) {
  el.textContent = "";
  for (let i = 0; i < text.length; i++) {
    el.textContent += text[i];
    await sleep(speed);
  }
}

async function runTypingIntro() {
  const helloEl = $("typedHello");
  const introEl = $("typedIntro");
  const cursorEl = $("typedCursor");

  if (!helloEl || !introEl || !cursorEl) return;

  const hour = new Date().getHours();
  const greeting = hour >= 18 || hour < 5 ? "Bonsoir, bienvenue sur votre espace d’analyse." : "Bonjour, bienvenue sur votre espace d’analyse.";

  const intro =
    "Importez un fichier ou complétez le formulaire pour obtenir un statut, un score de risque, des alertes clés et une recommandation claire en quelques instants.";

  await typeText(helloEl, greeting, 34);
  await sleep(250);
  await typeText(introEl, intro, 18);

  await sleep(250);
  cursorEl.classList.add("hidden");
}

function initParticlesBackground() {
  const canvas = $("particles-canvas");
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  let width = 0;
  let height = 0;
  let dpr = 1;

  const particles = [];
  const PARTICLE_COUNT = 70;
  const LINK_DISTANCE = 170;

  function random(min, max) {
    return Math.random() * (max - min) + min;
  }

  function resize() {
    dpr = Math.max(1, window.devicePixelRatio || 1);
    width = window.innerWidth;
    height = window.innerHeight;

    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function createParticles() {
    particles.length = 0;
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      particles.push({
        x: random(0, width),
        y: random(0, height),
        vx: random(-0.35, 0.35),
        vy: random(-0.35, 0.35),
        r: random(1.5, 3.4),
      });
    }
  }

  function draw() {
    ctx.clearRect(0, 0, width, height);

    for (const p of particles) {
      p.x += p.vx;
      p.y += p.vy;

      if (p.x <= 0 || p.x >= width) p.vx *= -1;
      if (p.y <= 0 || p.y >= height) p.vy *= -1;

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(79, 124, 255, 0.35)";
      ctx.fill();
    }

    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const a = particles[i];
        const b = particles[j];
        const dx = a.x - b.x;
        const dy = a.y - b.y;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < LINK_DISTANCE) {
          const alpha = 1 - dist / LINK_DISTANCE;

          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.strokeStyle = `rgba(122, 92, 255, ${0.16 * alpha})`;
          ctx.lineWidth = 1.1;
          ctx.stroke();
        }
      }
    }

    requestAnimationFrame(draw);
  }

  window.addEventListener("resize", () => {
    resize();
    createParticles();
  });

  resize();
  createParticles();
  draw();
}

function toast(message) {
  const toastEl = $("toast");
  if (!toastEl) return;

  toastEl.textContent = message;
  toastEl.style.display = "block";

  clearTimeout(toastEl._timer);
  toastEl._timer = setTimeout(() => {
    toastEl.style.display = "none";
  }, 3500);
}

function setActiveTab(tabName) {
  document.querySelectorAll(".tab").forEach((button) => {
    button.classList.remove("active");
  });

  document.querySelectorAll(".tabview").forEach((view) => {
    view.classList.remove("active");
  });

  const activeButton = document.querySelector(`.tab[data-tab="${tabName}"]`);
  const activeView = document.querySelector(`#tab-${tabName}`);

  if (activeButton) activeButton.classList.add("active");
  if (activeView) activeView.classList.add("active");
}

function setResult(result) {
  lastResult = result;
  $("exportBtn").disabled = !lastResult;

  const status = String(result.status || "REVIEW").toUpperCase();
  const badge = $("statusBadge");

  badge.textContent = status;
  badge.classList.remove("ok", "review", "flagged");

  if (status === "OK") {
    badge.classList.add("ok");
  } else if (status === "FLAGGED") {
    badge.classList.add("flagged");
  } else {
    badge.classList.add("review");
  }

  $("riskScore").textContent =
    result.risk_score !== undefined && result.risk_score !== null
      ? `${result.risk_score}/100`
      : "—";

  const alerts = Array.isArray(result.top_alerts) ? result.top_alerts : [];
  const alertsList = $("alertsList");
  alertsList.innerHTML = "";

  if (!alerts.length) {
    alertsList.innerHTML = `<li class="muted">Aucune alerte</li>`;
  } else {
    alerts.forEach((alertText) => {
      const li = document.createElement("li");
      li.textContent = alertText;
      alertsList.appendChild(li);
    });
  }

  $("recommendedAction").textContent = result.recommended_action || "—";
  $("summaryExplanation").textContent = result.summary_explanation || "—";
  $("rawJson").textContent = JSON.stringify(result, null, 2);
}

async function analyzeFile() {
  if (!selectedFile) return;

  const useMistral = $("useMistral").checked;
  const formData = new FormData();

  formData.append("file", selectedFile);
  formData.append("use_mistral", String(useMistral));

  $("analyzeBtn").disabled = true;
  toast("Analyse du fichier en cours...");

  try {
    const response = await fetch("/api/analyze/file", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();
    $("analyzeBtn").disabled = false;

    if (!response.ok) {
      toast(data.error || "Une erreur est survenue pendant l’analyse.");
      return;
    }

    setResult(data);
    toast("Analyse terminée.");
  } catch (error) {
    $("analyzeBtn").disabled = false;
    toast("Impossible de contacter le serveur.");
  }
}

async function analyzeForm() {
  const payload = {
    use_mistral: $("useMistral").checked,
    full_name: $("fullName").value,
    age: $("age").value ? Number($("age").value) : null,
    product: $("product").value,
    occupation: $("occupation").value,
    annual_income: $("income").value ? Number($("income").value) : null,
    notes: $("notes").value,
  };

  toast("Analyse du formulaire en cours...");

  try {
    const response = await fetch("/api/analyze/form", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json();

    if (!response.ok) {
      toast(data.error || "Une erreur est survenue pendant l’analyse.");
      return;
    }

    setResult(data);
    toast("Analyse terminée.");
  } catch (error) {
    toast("Impossible de contacter le serveur.");
  }
}

async function exportPdf() {
  if (!lastResult) return;

  const filenameHint =
    lastResult._meta && lastResult._meta.input_name
      ? lastResult._meta.input_name
      : "analysis";

  try {
    const response = await fetch("/api/export/pdf", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        result: lastResult,
        filename_hint: filenameHint,
      }),
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      toast(data.error || "Export PDF impossible.");
      return;
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = "analysis.pdf";
    document.body.appendChild(link);
    link.click();
    link.remove();

    URL.revokeObjectURL(url);
    toast("PDF exporté.");
  } catch (error) {
    toast("Impossible de générer le PDF.");
  }
}

function initTabs() {
  document.querySelectorAll(".tab").forEach((button) => {
    button.addEventListener("click", () => {
      setActiveTab(button.dataset.tab);
    });
  });
}

function initDropzone() {
  const dropzone = $("dropzone");
  const input = $("fileInput");

  $("browseBtn").addEventListener("click", () => input.click());

  input.addEventListener("change", () => {
    const file = input.files && input.files[0];
    if (!file) return;

    selectedFile = file;
    $("fileInfo").textContent = `Fichier sélectionné : ${file.name}`;
    $("analyzeBtn").disabled = false;
  });

  dropzone.addEventListener("dragover", (event) => {
    event.preventDefault();
    dropzone.classList.add("dragover");
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("dragover");
  });

  dropzone.addEventListener("drop", (event) => {
    event.preventDefault();
    dropzone.classList.remove("dragover");

    const file = event.dataTransfer.files && event.dataTransfer.files[0];
    if (!file) return;

    const extension = file.name.includes(".")
      ? file.name.split(".").pop().toLowerCase()
      : "";

    if (!["pdf", "txt", "csv", "json"].includes(extension)) {
      toast("Type non supporté. Utilise un fichier PDF, TXT, CSV ou JSON.");
      return;
    }

    selectedFile = file;
    $("fileInfo").textContent = `Fichier déposé : ${file.name}`;
    $("analyzeBtn").disabled = false;
  });

  $("analyzeBtn").addEventListener("click", analyzeFile);
}

function initActions() {
  $("analyzeFormBtn").addEventListener("click", analyzeForm);
  $("exportBtn").addEventListener("click", exportPdf);
}

window.addEventListener("DOMContentLoaded", async () => {
  initParticlesBackground();
  initTabs();
  initDropzone();
  initActions();
  await runTypingIntro();
});