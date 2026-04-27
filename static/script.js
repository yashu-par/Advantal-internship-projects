let sessionId = null;

window.onload = async () => {
  await loadStats();
  await loadSessions();
  await newSession();
};

async function newSession() {
  try {
    const res = await fetch("/api/new-session", { method: "POST" });
    const data = await res.json();
    sessionId = data.session_id;
    document.getElementById("msgs").innerHTML = `
      <div class="msg bot">
        <div class="av">M</div>
        <div class="bubble">Hello! I am Medico, your Assistant. I don't know your name yet — what should I call you? 😊</div>
      </div>`;
    await loadSessions();
  } catch(e) {
    console.error("newSession error:", e);
  }
}

async function send() {
  const inp = document.getElementById("inp");
  const text = inp.value.trim();
  if (!text) return;
  inp.value = "";

  addMsg("user", text);
  const tid = addTyping();

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message: text })
    });
    const data = await res.json();
    removeTyping(tid);

    // Memory sidebar update karo
    if (data.memory) {
      updateMemory(data.memory);
    }

    addMsg("bot", data.answer, data.sources || [], data.time || 0, data.source_pdfs || []);
    await loadStats();
    await loadSessions();

  } catch(e) {
    removeTyping(tid);
    console.error("send error:", e);
    addMsg("bot", "Connection error: " + e.message);
  }
}

function addMsg(role, content, sources = [], time = null, sourcePdfs = []) {
  const msgs = document.getElementById("msgs");
  const isUser = role === "user";

  // Page chips
  let chipsHTML = "";
  if (sources && sources.length > 0) {
    chipsHTML = `<div class="chips">` +
      sources.map(p => `<span class="chip">Page ${p}</span>`).join("") +
      (time ? `<span class="chip">${time}s</span>` : "") +
      `</div>`;
  }

  // PDF source naam — niche dikhao
  let pdfSourceHTML = "";
  if (sourcePdfs && sourcePdfs.length > 0) {
    pdfSourceHTML = `<div class="pdf-source">` +
      sourcePdfs.map(pdf => `<span class="pdf-chip">📄 ${pdf}</span>`).join("") +
      `</div>`;
  }

  msgs.innerHTML += `
    <div class="msg ${isUser ? "user" : "bot"}">
      <div class="av">${isUser ? "Y" : "M"}</div>
      <div>
        <div class="bubble">${content}</div>
        ${chipsHTML}
        ${pdfSourceHTML}
      </div>
    </div>`;

  msgs.scrollTop = msgs.scrollHeight;
}

function updateMemory(memory) {
  const nameEl = document.getElementById("mem-name");
  const cityEl = document.getElementById("mem-city");
  if (nameEl) nameEl.textContent = memory.name || "—";
  if (cityEl) cityEl.textContent = memory.city || "—";
}

function addTyping() {
  const id = "t" + Date.now();
  const msgs = document.getElementById("msgs");
  msgs.innerHTML += `
    <div class="msg bot" id="${id}">
      <div class="av">M</div>
      <div class="bubble">
        <span class="dot"></span><span class="dot"></span><span class="dot"></span>
      </div>
    </div>`;
  msgs.scrollTop = msgs.scrollHeight;
  return id;
}

function removeTyping(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

async function loadSessions() {
  try {
    const res = await fetch("/api/sessions");
    const data = await res.json();
    const list = document.getElementById("sess-list");
    if (!list) return;
    list.innerHTML = data.sessions.map(s => `
      <div class="sess-item ${s.id === sessionId ? "active" : ""}"
           onclick="loadSession(${s.id})">
        ${s.name}
        <div style="font-size:11px;color:#9ca3af">${s.date ? s.date.slice(0,10) : ""}</div>
      </div>`).join("");
  } catch(e) { console.error(e); }
}

async function loadSession(id) {
  sessionId = id;
  try {
    const res = await fetch(`/api/history/${id}`);
    const data = await res.json();
    const msgs = document.getElementById("msgs");
    msgs.innerHTML = data.messages.map(m => `
      <div class="msg ${m.role === "user" ? "user" : "bot"}">
        <div class="av">${m.role === "user" ? "Y" : "M"}</div>
        <div class="bubble">${m.content}</div>
      </div>`).join("");
    msgs.scrollTop = msgs.scrollHeight;
    await loadSessions();
  } catch(e) { console.error(e); }
}

async function loadStats() {
  try {
    const res = await fetch("/api/stats");
    const data = await res.json();
    const s = document.getElementById("st-s");
    const q = document.getElementById("st-q");
    const t = document.getElementById("st-t");
    if (s) s.textContent = data.sessions;
    if (q) q.textContent = data.queries;
    if (t) t.textContent = data.avg_time + "s";
  } catch(e) { console.error(e); }
}

async function uploadPDF(input) {
  const file = input.files[0];
  if (!file) return;

  const status = document.getElementById("upload-status");
  status.style.color = "#6b7280";
  status.textContent = `Uploading ${file.name}...`;

  const formData = new FormData();
  formData.append("pdf", file);

  try {
    const res = await fetch("/api/upload-pdf", {
      method: "POST",
      body: formData
    });
    const data = await res.json();

    if (data.error) {
      status.style.color = "#dc2626";
      status.textContent = "Error: " + data.error;
    } else {
      status.style.color = "#16a34a";
      status.textContent = `✓ ${data.filename} ready!`;

      // Chat mein confirmation dikhao
      addMsg("bot", `📄 I've read <b>${data.filename}</b> — ${data.chunks} chunks added. You can now ask me anything about it!`);
    }
  } catch(e) {
    status.style.color = "#dc2626";
    status.textContent = "Upload failed!";
    console.error(e);
  }

  // Input reset karo
  input.value = "";
}