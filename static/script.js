// ── State ──────────────────────────────────────────
let conversationHistory = [];
let msgCount            = 0;
let assignedDoctorId    = null;
let assignedDoctor      = null;
let chatTurnCount       = 0;
let symptomTurns        = 0;
let assignInProgress    = false;
let patientData         = { name:'', age:'', gender:'', emergency:false };
let stage               = 'name';
let collectedPrecautions = '';  // Store precautions from AI

// ── DOM ────────────────────────────────────────────
const chatEl        = document.getElementById('chat-messages');
const inputEl       = document.getElementById('user-input');
const sendBtnEl     = document.getElementById('send-btn');
const msgCountEl    = document.getElementById('msg-count');
const doctorsListEl = document.getElementById('doctors-list');
const assignedCard  = document.getElementById('assigned-card');
const assignedInner = document.getElementById('assigned-inner');

// ── Storage Keys ───────────────────────────────────────────
const SS_CHAT       = 'hosp_chat_messages';
const SS_STATE      = 'hosp_chat_state';
const SS_BANNER     = 'hosp_confirm_banner';

function storeItem(key, value) {
  try {
    sessionStorage.setItem(key, value);
    localStorage.setItem(key, value);
  } catch (e) {}
}

function getStoredItem(key) {
  return sessionStorage.getItem(key) || localStorage.getItem(key);
}

function removeStoredItem(key) {
  try {
    sessionStorage.removeItem(key);
    localStorage.removeItem(key);
  } catch (e) {}
}

window.addEventListener('DOMContentLoaded', () => {
  startClock();
  loadDoctors();
  loadSessionUser();
  restoreChatFromSession(); // FIX: restore chat on page load
  inputEl.focus();
});
window.addEventListener('beforeunload', saveChatState);
window.addEventListener('pagehide', saveChatState);

// ── Save chat state to storage ─────────────────────
function saveChatState() {
  const stateObj = {
    conversationHistory,
    msgCount,
    assignedDoctorId,
    assignedDoctor,
    chatTurnCount,
    symptomTurns,
    patientData,
    stage,
    collectedPrecautions
  };
  const stateJson = JSON.stringify(stateObj);
  storeItem(SS_STATE, stateJson);
  // Save rendered HTML of chat
  storeItem(SS_CHAT, chatEl.innerHTML);
}

// ── Restore chat from storage ──────────────────────
function restoreChatFromSession() {
  const savedState = getStoredItem(SS_STATE);
  const savedChat  = getStoredItem(SS_CHAT);

  if (!savedState || !savedChat) {
    // No saved session — show welcome message
    setTimeout(() => {
      appendMessage('ai', `👋 Welcome to <strong>City Hospital</strong>!<br>I'm <strong>Aria</strong>, your AI medical receptionist.<br><br>May I know your <strong>full name</strong> please?`);
      saveChatState();
    }, 400);
    return;
  }

  try {
    const state = JSON.parse(savedState);
    // Restore all state variables
    conversationHistory  = state.conversationHistory  || [];
    msgCount             = state.msgCount             || 0;
    assignedDoctorId     = state.assignedDoctorId     || null;
    assignedDoctor       = state.assignedDoctor       || null;
    chatTurnCount        = state.chatTurnCount        || 0;
    symptomTurns         = state.symptomTurns         || 0;
    patientData          = state.patientData          || { name:'', age:'', gender:'', emergency:false };
    stage                = state.stage                || 'name';
    collectedPrecautions = state.collectedPrecautions || '';

    // Restore chat HTML
    chatEl.innerHTML = savedChat;
    chatEl.scrollTop = chatEl.scrollHeight;
    msgCountEl.textContent = `${msgCount} messages`;

    // Restore assigned card if doctor was assigned
    if (assignedDoctor) {
      highlightDoctor(assignedDoctor.id);
    }

    // FIX: Restore confirmation banner if appointment was booked
    const bannerData = getStoredItem(SS_BANNER);
    if (bannerData) {
      try {
        const bd = JSON.parse(bannerData);
        showConfirmationBanner(bd.slot, true); // true = restored (no auto-remove)
      } catch(e) {}
    }

    // Re-show slot buttons if still in slots stage and no appointment booked yet
    if (stage === 'slots' && assignedDoctor && assignedDoctor.slots) {
      setTimeout(() => {
        if (!document.getElementById('slot-buttons')) {
          showSlotButtons(assignedDoctor.slots);
        }
      }, 300);
    }

    setInputDisabled(false);
    inputEl.focus();
  } catch(e) {
    // If restore fails, start fresh
    removeStoredItem(SS_STATE);
    removeStoredItem(SS_CHAT);
    setTimeout(() => {
      appendMessage('ai', `👋 Welcome to <strong>City Hospital</strong>!<br>I'm <strong>Aria</strong>, your AI medical receptionist.<br><br>May I know your <strong>full name</strong> please?`);
      saveChatState();
    }, 400);
  }
}

// ── Load session user ──────────────────────────────
async function loadSessionUser() {
  try {
    const res  = await fetch('/api/session');
    const data = await res.json();
    if (data.logged_in) {
      const nameEl = document.getElementById('session-name');
      if (nameEl) nameEl.textContent = data.name;
    }
  } catch(e) {}
}

// ── Clock ──────────────────────────────────────────
function startClock() {
  function tick() {
    const now = new Date();
    document.getElementById('clock').textContent =
      now.toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit'});
    document.getElementById('date-label').textContent =
      now.toLocaleDateString('en-US',{weekday:'long',day:'numeric',month:'long'});
  }
  tick();
  setInterval(tick, 30000);
}

// ── Load Doctors ───────────────────────────────────
async function loadDoctors() {
  try {
    const res  = await fetch('/api/doctors');
    const data = await res.json();
    if (data.success) {
      renderDoctors(data.doctors);
      updateStats(data.doctors);
      // Re-highlight if doctor was previously assigned
      if (assignedDoctorId) {
        setTimeout(() => highlightDoctor(assignedDoctorId), 200);
      }
    }
  } catch(err) {
    doctorsListEl.innerHTML = '<p style="color:#ef4444;font-size:13px;padding:10px">Failed to load doctors.</p>';
  }
}

function renderDoctors(doctors) {
  doctorsListEl.innerHTML = '';
  doctors.forEach(doc => {
    const div = document.createElement('div');
    div.className = 'doctor-item' + (!doc.available ? ' unavailable' : '');
    div.id = `doctor-${doc.id}`;
    div.innerHTML = `
      <div class="doc-avatar" style="background:${doc.color}18;color:${doc.color};border:1.5px solid ${doc.color}44">${doc.initials}</div>
      <div class="doc-info">
        <div class="doc-name">${doc.name}</div>
        <div class="doc-spec">${doc.specialty}</div>
        <div class="doc-room">${doc.room}</div>
      </div>
      <div class="doc-right">
        <div class="doc-count">${doc.count} pts</div>
        <div class="doc-status ${doc.available ? 'status-available':'status-unavailable'}"></div>
      </div>`;
    doctorsListEl.appendChild(div);
  });
}

function updateStats(doctors) {
  document.getElementById('stat-avail').textContent    = doctors.filter(d=>d.available).length;
  document.getElementById('stat-patients').textContent = doctors.reduce((s,d)=>s+d.count,0);
}

// ── Greeting check ─────────────────────────────────
function isGreeting(input) {
  const greetings = ['hello','hi','hey','hii','helo','helloo','heyy','namaste','namaskar',
    'good morning','good evening','good afternoon','good night','howdy','sup'];
  return greetings.includes(input.toLowerCase().trim());
}

// ── Extract first name ─────────────────────────────
function extractFirstName(input) {
  if (isGreeting(input)) return null;
  let cleaned = input
    .replace(/my name is/i,'').replace(/i am/i,'')
    .replace(/i'm/i,'').replace(/call me/i,'').replace(/this is/i,'').trim();
  const parts = cleaned.split(' ').filter(p=>p.length>0);
  if (parts.length === 0) return null;
  const first = parts[0];
  if (first.length < 2 || /^\d+$/.test(first)) return null;
  return first.charAt(0).toUpperCase() + first.slice(1).toLowerCase();
}

// ── Extract gender ─────────────────────────────────
function extractGender(input) {
  const lower = input.toLowerCase().trim();
  if (lower.includes('female')||lower.includes('woman')||lower.includes('girl')||lower==='f') return 'Female';
  if (lower.includes('male')||lower.includes('man')||lower.includes('boy')||lower==='m') return 'Male';
  if (lower.includes('other')) return 'Other';
  return input.trim().charAt(0).toUpperCase()+input.trim().slice(1).toLowerCase();
}

// ── Get Future Slots for assigned doctor ──────────────────
// Day name → JS getDay() number
const DAY_MAP = {
  'sunday':0,'monday':1,'tuesday':2,'wednesday':3,
  'thursday':4,'friday':5,'saturday':6
};

function parseSlotDateTime(slotStr) {
  // Format: "Monday 10:00 AM" or "Wednesday 11:00 AM"
  const parts = slotStr.trim().split(' ');
  if (parts.length < 3) return null;

  const dayName  = parts[0].toLowerCase();
  const timeStr  = parts[1]; // "10:00"
  const ampm     = parts[2]; // "AM" or "PM"

  const targetDay = DAY_MAP[dayName];
  if (targetDay === undefined) return null;

  const [hourStr, minStr] = timeStr.split(':');
  let hour = parseInt(hourStr, 10);
  const min = parseInt(minStr, 10);

  if (ampm.toUpperCase() === 'PM' && hour !== 12) hour += 12;
  if (ampm.toUpperCase() === 'AM' && hour === 12) hour = 0;

  // Find next occurrence of this weekday
  const now = new Date();
  const result = new Date(now);
  result.setHours(hour, min, 0, 0);

  const currentDay = now.getDay();
  let diff = targetDay - currentDay;

  // If same day but time already passed → next week
  if (diff < 0 || (diff === 0 && result <= now)) {
    diff += 7;
  }

  result.setDate(now.getDate() + diff);
  return result;
}

function getFutureSlots(slots) {
  if (!slots || slots.length === 0) return [];
  const now = new Date();
  return slots.filter(slot => {
    const dt = parseSlotDateTime(slot);
    return dt && dt > now;
  });
}

// Format slot with actual upcoming date
function formatSlotWithDate(slotStr) {
  const dt = parseSlotDateTime(slotStr);
  if (!dt) return slotStr;
  const dateLabel = dt.toLocaleDateString('en-IN', {
    weekday:'short', day:'numeric', month:'short'
  });
  // Extract time portion
  const parts = slotStr.split(' ');
  const time  = parts.slice(1).join(' ');
  return `${dateLabel} · ${time}`;
}

// ── Show Slot Buttons (only future slots of assigned doctor) ────
function showSlotButtons(slots) {
  const old = document.getElementById('slot-buttons');
  if (old) old.remove();

  // Filter only future slots
  const futureSlots = getFutureSlots(slots);

  if (!futureSlots || futureSlots.length === 0) {
    // No future slots available
    appendMessage('ai',
      `⚠️ No upcoming slots are available for ${assignedDoctor ? assignedDoctor.name : 'this doctor'} right now.<br>` +
      `Please visit the reception desk to book an appointment.`
    );
    stage = 'post';
    setInputDisabled(false);
    saveChatState();
    return;
  }

  const container = document.createElement('div');
  container.id = 'slot-buttons';
  container.style.cssText = `
    display:flex;flex-wrap:wrap;gap:8px;
    padding:12px 20px 14px;
    background:#f8faff;
    border-top:1px solid #e2e8f0;
  `;

  const label = document.createElement('div');
  label.style.cssText = 'width:100%;font-size:11px;color:#94a3b8;font-weight:600;margin-bottom:4px;';
  label.textContent = 'Select a slot to confirm appointment:';
  container.appendChild(label);

  futureSlots.forEach(slot => {
    const btn = document.createElement('button');
    const displaySlot = formatSlotWithDate(slot);
    btn.textContent = '📅 ' + displaySlot;
    btn.dataset.originalSlot = slot; // store original for booking
    btn.style.cssText = `
      padding:9px 18px;background:#eef2ff;
      border:1.5px solid #c7d2fe;border-radius:22px;
      color:#4f46e5;font-size:13px;font-weight:600;
      cursor:pointer;font-family:'Plus Jakarta Sans',sans-serif;
      transition:all 0.15s;
    `;
    btn.onmouseover = () => { btn.style.background='#6366f1'; btn.style.color='#fff'; btn.style.borderColor='#6366f1'; };
    btn.onmouseout  = () => { btn.style.background='#eef2ff'; btn.style.color='#4f46e5'; btn.style.borderColor='#c7d2fe'; };

    btn.onclick = async () => {
      container.remove();
      const originalSlot = btn.dataset.originalSlot;
      const displayText  = displaySlot;
      appendMessage('user', displayText);

      // Save appointment to DB
      await fetch('/api/book', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({
          name: patientData.name,
          appointment_time: displayText,
          precautions: collectedPrecautions
        })
      });

      stage = 'post';
      inputEl.placeholder = 'Ask anything else...';

      // FIX: Save banner info to sessionStorage so it persists across navigation
        storeItem(SS_BANNER, JSON.stringify({
        slot: displayText,
        doctor: assignedDoctor ? assignedDoctor.name : '',
        room: assignedDoctor ? assignedDoctor.room : ''
      }));

      // ✅ Show confirmation banner (persistent — no auto-remove)
      showConfirmationBanner(displayText, false);
      showAppointmentPopup(displayText, assignedDoctor ? assignedDoctor.name : '', assignedDoctor ? assignedDoctor.room : '');

      appendMessage('ai',
        `🎉 Appointment <strong>confirmed</strong>, <strong>${patientData.name}</strong>!<br><br>` +
        `📅 <strong>Slot:</strong> ${displayText}<br>` +
        `👨‍⚕️ <strong>Doctor:</strong> ${assignedDoctor ? assignedDoctor.name : ''}<br>` +
        `📍 <strong>Room:</strong> ${assignedDoctor ? assignedDoctor.room : ''}<br><br>` +
        `Please arrive <strong>10 minutes early</strong> and bring your previous medical reports. Get well soon! 🙏`
      );
      saveChatState();
      setInputDisabled(false);
      inputEl.focus();
    };
    container.appendChild(btn);
  });

  const inputRow = document.querySelector('.input-row');
  inputRow.parentNode.insertBefore(container, inputRow);
}

// ── Confirmation Banner ────────────────────────────
// FIX: restored param = true means don't auto-remove (came from sessionStorage)
function showConfirmationBanner(slot, restored = false) {
  // Remove old banner if any
  const oldBanner = document.getElementById('confirm-banner');
  if (oldBanner) oldBanner.remove();

  // Get stored data if available
  let doctorName = assignedDoctor ? assignedDoctor.name : '';
  let room       = assignedDoctor ? assignedDoctor.room : '';
const bannerData = getStoredItem(SS_BANNER);
  if (bannerData) {
    try {
      const bd = JSON.parse(bannerData);
      if (!doctorName) doctorName = bd.doctor || '';
      if (!room)       room       = bd.room   || '';
      if (!slot)       slot       = bd.slot   || '';
    } catch(e) {}
  }

  const banner = document.createElement('div');
  banner.id = 'confirm-banner';
  banner.style.cssText = `
    background: linear-gradient(135deg, #22c55e, #16a34a);
    color: #fff;
    padding: 14px 20px;
    border-radius: 14px;
    margin: 10px 0;
    font-size: 14px;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 12px;
    box-shadow: 0 4px 16px rgba(34,197,94,0.25);
    animation: slideDown 0.4s ease;
  `;

  // Add animation keyframes once
  if (!document.getElementById('confirm-banner-style')) {
    const style = document.createElement('style');
    style.id = 'confirm-banner-style';
    style.textContent = `
      @keyframes slideDown {
        from { opacity:0; transform:translateY(-12px); }
        to   { opacity:1; transform:translateY(0); }
      }
    `;
    document.head.appendChild(style);
  }

  banner.innerHTML = `
    <span style="font-size:24px">✅</span>
    <div>
      <div style="font-size:15px;margin-bottom:2px">Appointment Confirmed!</div>
      <div style="font-size:12px;opacity:0.9;font-weight:500">
        ${doctorName} · ${slot}
      </div>
    </div>
    <button onclick="this.parentElement.remove()" style="
      margin-left:auto;background:rgba(255,255,255,0.2);border:none;
      color:#fff;width:24px;height:24px;border-radius:50%;cursor:pointer;
      font-size:14px;display:flex;align-items:center;justify-content:center;
      font-family:sans-serif;
    ">×</button>
  `;

  // Insert at the top of body so banner stays visible across all chat layouts
  document.body.prepend(banner);

  // FIX: Only auto-remove if NOT restored from session (fresh confirmation)
  // Restored banners stay until manually closed
  if (!restored) {
    // Auto remove after 30 seconds (was 8 — now much longer)
    setTimeout(() => { if (banner.parentNode) banner.remove(); }, 30000);
  }
}

// ── Appointment popup overlay ─────────────────────
function showAppointmentPopup(slot, doctor, room) {
  const overlay = document.getElementById('appt-popup');
  if (!overlay) return;
  const details = document.getElementById('popup-details');
  const popupId = document.getElementById('popup-id');

  details.innerHTML = `
    <div class="popup-row"><span>Patient</span><span>${patientData.name || 'Guest'}</span></div>
    <div class="popup-row"><span>Doctor</span><span>${doctor || 'Assigned doctor'}</span></div>
    <div class="popup-row"><span>Room</span><span>${room || 'N/A'}</span></div>
    <div class="popup-row"><span>Slot</span><span>${slot || 'Selected slot'}</span></div>
  `;
  const now = new Date();
  popupId.textContent = `Booking ID: ${now.getTime()}`;
  overlay.style.display = 'flex';
}

// ── Send Message ───────────────────────────────────
async function sendMessage() {
  const text = inputEl.value.trim();
  if (!text) return;

  inputEl.value = '';
  setInputDisabled(true);
  appendMessage('user', text);

  // STAGE: Name
  if (stage === 'name') {
    const firstName = extractFirstName(text);
    if (!firstName) {
      const lower = text.toLowerCase().trim();
      let greeting = 'Hello';
      if (lower.includes('namaste')||lower.includes('namaskar')) greeting = 'Hello';
      else if (lower.includes('good morning'))   greeting = 'Good morning';
      else if (lower.includes('good evening'))   greeting = 'Good evening';
      else if (lower.includes('good afternoon')) greeting = 'Good afternoon';
      setTimeout(() => {
        appendMessage('ai', `${greeting}! 😊 Welcome to City Hospital.<br>May I know your <strong>full name</strong> please?`);
        saveChatState();
        setInputDisabled(false);
        inputEl.focus();
      }, 400);
      return;
    }
    patientData.name = firstName;
    stage = 'age';
    setTimeout(() => {
      appendMessage('ai', `Nice to meet you, <strong>${firstName}</strong>! 😊 How old are you?`);
      saveChatState();
      setInputDisabled(false);
      inputEl.focus();
    }, 400);
    return;
  }

  // STAGE: Age
  if (stage === 'age') {
    const ageMatch  = text.match(/\d+/);
    patientData.age = ageMatch ? ageMatch[0] : text.trim();
    stage = 'gender';
    setTimeout(() => {
      appendMessage('ai', `Got it! What is your gender — Male, Female, or Other?`);
      saveChatState();
      setInputDisabled(false);
      inputEl.focus();
    }, 400);
    return;
  }

  // STAGE: Gender
  if (stage === 'gender') {
    patientData.gender = extractGender(text);
    stage = 'symptoms';
    setTimeout(() => {
      appendMessage('ai',
        `Thank you, <strong>${patientData.name}</strong>! 🙏<br>` +
        `What problem are you facing today? Please describe your symptoms.`
      );
      saveChatState();
      setInputDisabled(false);
      inputEl.focus();
    }, 400);
    return;
  }

  // STAGE: Slots — patient typed instead of clicking
  if (stage === 'slots') {
    conversationHistory.push({role:'user', content:text});
    const doctorContext = assignedDoctor
      ? `\nAssigned Doctor: ${assignedDoctor.name} (${assignedDoctor.specialty}), ${assignedDoctor.room}\nAvailable Slots: ${(assignedDoctor.slots||[]).join(', ')}`
      : '';
    showTyping();
    try {
      const res = await fetch('/api/chat', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({
          message:text, name:patientData.name, age:patientData.age,
          gender:patientData.gender, history:conversationHistory.slice(0,-1),
          doctorContext:doctorContext, stage:'slots', symptomTurns:symptomTurns
        })
      });
      const data = await res.json();
      removeTyping();
      const reply = data.reply || "Please click one of the slot buttons above to book. 👆";

      // Collect any precautions mentioned
      if (reply.toLowerCase().includes('precaution') || reply.toLowerCase().includes('rest') || reply.toLowerCase().includes('avoid')) {
        collectedPrecautions += ' ' + reply.replace(/<[^>]*>/g,'');
      }

      appendMessage('ai', reply);
      conversationHistory.push({role:'assistant', content:reply});

      // Re-show slot buttons if they were removed
      if (!document.getElementById('slot-buttons') && assignedDoctor && assignedDoctor.slots && assignedDoctor.slots.length > 0) {
        setTimeout(() => showSlotButtons(assignedDoctor.slots), 300);
      }
    } catch(err) {
      removeTyping();
      appendMessage('ai', 'Please click one of the available slot buttons above to confirm. 👆');
      if (!document.getElementById('slot-buttons') && assignedDoctor) {
        setTimeout(() => showSlotButtons(assignedDoctor.slots||[]), 300);
      }
    }
    saveChatState();
    setInputDisabled(false);
    inputEl.focus();
    return;
  }

  // STAGE: Symptoms + Post → AI
  conversationHistory.push({role:'user', content:text});
  chatTurnCount++;
  if (stage === 'symptoms') symptomTurns++;

  showTyping();

  try {
    const lowerText = text.toLowerCase();
    if (lowerText.includes('chest pain')||lowerText.includes("can't breathe")||
        lowerText.includes('unconscious')||lowerText.includes('bleeding heavily')) {
      patientData.emergency = true;
    }

    const doctorContext = assignedDoctor
      ? `\nAssigned Doctor: ${assignedDoctor.name} (${assignedDoctor.specialty}), ${assignedDoctor.room}`
      : '';

    const chatRes = await fetch('/api/chat', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        message:text, name:patientData.name, age:patientData.age,
        gender:patientData.gender, history:conversationHistory.slice(0,-1),
        doctorContext:doctorContext, stage:stage, symptomTurns:symptomTurns
      })
    });

    const chatData = await chatRes.json();
    removeTyping();

    const aiReply = chatData.reply || "Sorry, something went wrong.";
    appendMessage('ai', aiReply);
    conversationHistory.push({role:'assistant', content:aiReply});

    // Collect precautions from AI replies
    const plainReply = aiReply.replace(/<[^>]*>/g,'');
    if (plainReply.toLowerCase().includes('precaution') ||
        plainReply.toLowerCase().includes('rest') ||
        plainReply.toLowerCase().includes('avoid') ||
        plainReply.toLowerCase().includes('drink water')) {
      collectedPrecautions += ' ' + plainReply;
    }

    if (aiReply.toLowerCase().includes('emergency') && !assignedDoctorId) {
      patientData.emergency = true;
      showEmergencyBanner();
    }

    // Assign doctor after 2nd symptom turn OR if AI says "Let me find"
    const shouldAssign = stage === 'symptoms' && !assignedDoctorId && !assignInProgress && (
      symptomTurns >= 2 ||
      aiReply.toLowerCase().includes('let me find') ||
      aiReply.toLowerCase().includes('best doctor') ||
      aiReply.toLowerCase().includes('right now')
    );

    if (shouldAssign) {
      await assignDoctor();
    }

  } catch(err) {
    removeTyping();
    appendMessage('ai', '⚠️ Something went wrong. Please try again.');
    console.error(err);
  }

  saveChatState();
  setInputDisabled(false);
  inputEl.focus();
}

// ── Assign Doctor ──────────────────────────────────
async function assignDoctor() {
  if (assignedDoctorId || assignInProgress) return;
  assignInProgress = true;

  const symptomsText = conversationHistory
    .filter(m=>m.role==='user').map(m=>m.content).join(' | ');

  try {
    showTyping();
    const res = await fetch('/api/assign', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        symptoms:symptomsText, name:patientData.name,
        age:patientData.age, gender:patientData.gender,
        emergency:patientData.emergency
      })
    });

    const data = await res.json();
    removeTyping();

    if (data.success && data.doctor) {
      assignedDoctor   = data.doctor;
      assignedDoctorId = data.doctor.id;

      // Store instructions as initial precautions
      if (data.instructions) {
        collectedPrecautions = data.instructions;
      }

      highlightDoctor(data.doctor.id);
      showAssignedCard(data.doctor, data.reason, data.priority, data.instructions);

      appendMessage('ai',
        `✅ <strong>${patientData.name}</strong>, based on your symptoms I have found the best doctor for you:<br><br>` +
        `👨‍⚕️ <strong>${data.doctor.name}</strong> — ${data.doctor.specialty}<br>` +
        `📍 <strong>${data.doctor.room}</strong><br><br>` +
        `📋 ${data.instructions}`
      );

      // Get future slots only for assigned doctor
      const futureSlots = getFutureSlots(data.doctor.slots || []);
      stage = 'slots';

      setTimeout(() => {
        if (futureSlots.length > 0) {
          appendMessage('ai',
            `📅 Here are the upcoming available slots for <strong>${data.doctor.name}</strong>.<br>` +
            `Please click a slot below to book your appointment 👇`
          );
          setTimeout(() => {
            showSlotButtons(data.doctor.slots || []);
            saveChatState();
            setInputDisabled(false);
            inputEl.placeholder = 'Ask about precautions, symptoms, or anything...';
            inputEl.focus();
          }, 300);
        } else {
          appendMessage('ai',
            `📅 No upcoming slots are available for <strong>${data.doctor.name}</strong> right now.<br>` +
            `Please visit the reception desk to book an appointment.`
          );
          stage = 'post';
          saveChatState();
          setInputDisabled(false);
        }
      }, 600);

    } else {
      appendMessage('ai', `⚠️ Could not assign a doctor. Please visit the reception desk.`);
      setInputDisabled(false);
    }

  } catch(err) {
    removeTyping();
    appendMessage('ai', '⚠️ Doctor assignment failed. Please visit reception desk.');
    console.error(err);
    setInputDisabled(false);
  }

  assignInProgress = false;
  saveChatState();
}

// ── Highlight Doctor ───────────────────────────────
function highlightDoctor(doctorId) {
  document.querySelectorAll('.doctor-item').forEach(el=>el.classList.remove('highlighted'));
  const el = document.getElementById(`doctor-${doctorId}`);
  if (el) { el.classList.add('highlighted'); el.scrollIntoView({behavior:'smooth',block:'center'}); }
}

// ── Show Assigned Card ─────────────────────────────
function showAssignedCard(doctor, reason, priority, instructions) {
  if (!doctor) return;
  assignedInner.innerHTML = `
    <div class="doc-header-assigned">
      <div class="doc-avatar-big" style="background:${doctor.color}18;color:${doctor.color};border:1.5px solid ${doctor.color}44">${doctor.initials}</div>
      <div>
        <div class="doc-name-big">${doctor.name}</div>
        <div class="doc-spec-big">${doctor.specialty}</div>
        <div class="doc-room-big">📍 ${doctor.room}</div>
      </div>
    </div>
    <div class="assigned-reason">🎯 <strong>Reason:</strong> ${reason}</div>
    <div class="assigned-instructions">📋 <strong>Instructions:</strong> ${instructions}</div>
    <span class="priority-badge priority-${priority}">
      ${priority==='High'?'🔴':priority==='Medium'?'🟡':'🟢'} Priority: ${priority}
    </span>`;
  assignedCard.style.display = 'block';
}

// ── Emergency Banner ───────────────────────────────
let emergencyShown = false;
function showEmergencyBanner() {
  if (emergencyShown) return;
  emergencyShown = true;
  const banner = document.createElement('div');
  banner.className = 'emergency-banner';
  banner.innerHTML = '🚨 <strong>Emergency Detected!</strong> Please proceed to Emergency Ward — Room E1 immediately.';
  document.querySelector('.left-col').insertBefore(banner, document.querySelector('.chat-card'));
}

// ── Append Message ─────────────────────────────────
function appendMessage(role, text) {
  const wrapper = document.createElement('div');
  wrapper.className = `msg ${role==='user'?'user-msg':'ai-msg'}`;
  const avatar = document.createElement('div');
  avatar.className = `avatar ${role==='user'?'user-avatar':'ai-avatar'}`;
  avatar.textContent = role==='user'
    ? (patientData.name ? patientData.name.slice(0,2).toUpperCase() : 'PT')
    : '🩺';
  const bubble = document.createElement('div');
  bubble.className = `bubble ${role==='user'?'user-bubble':'ai-bubble'}`;
  bubble.innerHTML = text;
  wrapper.appendChild(avatar);
  wrapper.appendChild(bubble);
  chatEl.appendChild(wrapper);
  chatEl.scrollTop = chatEl.scrollHeight;
  msgCount++;
  msgCountEl.textContent = `${msgCount} messages`;
}

// ── Typing Indicator ───────────────────────────────
function showTyping() {
  if (document.getElementById('typing-indicator')) return;
  const div = document.createElement('div');
  div.className = 'typing-msg';
  div.id = 'typing-indicator';
  div.innerHTML = `<div class="avatar ai-avatar">🩺</div><div class="typing-dots"><span></span><span></span><span></span></div>`;
  chatEl.appendChild(div);
  chatEl.scrollTop = chatEl.scrollHeight;
}
function removeTyping() {
  const t = document.getElementById('typing-indicator');
  if (t) t.remove();
}

function setInputDisabled(disabled) {
  sendBtnEl.disabled = disabled;
  inputEl.disabled   = disabled;
  if (!disabled) sendBtnEl.textContent = 'Send →';
}

function quickSend(text) {
  if (stage !== 'symptoms') return;
  inputEl.value = text;
  sendMessage();
}