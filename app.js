// ============================================================
// FitBot AI — Main Application Logic
// ============================================================

const API_BASE = '';
let chatHistory = [];
let guestMsgCount = 0;

// ---- Auth ----
let currentUser = null;

function getToken() { return localStorage.getItem('fitbot-token') || ''; }
function authHeaders() {
  const t = getToken();
  return t && t !== 'guest' ? { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + t } : { 'Content-Type': 'application/json' };
}

async function initAuth() {
  const token = getToken();
  const stored = localStorage.getItem('fitbot-user');
  if (!token) { window.location.href = '/login'; return false; }
  if (token === 'guest') {
    currentUser = { username: 'Guest', role: 'guest' };
    renderAuthUI();
    return true;
  }
  try {
    const res = await fetch('/api/auth/me', { headers: { Authorization: 'Bearer ' + token } });
    const data = await res.json();
    if (data.error) { localStorage.clear(); window.location.href = '/login'; return false; }
    currentUser = data;
    localStorage.setItem('fitbot-user', JSON.stringify(currentUser));
  } catch {
    if (stored) { currentUser = JSON.parse(stored); }
    else { window.location.href = '/login'; return false; }
  }
  renderAuthUI();
  return true;
}

function renderAuthUI() {
  if (!currentUser) return;
  const role = currentUser.role;

  // Inject user info into navbar
  const navbar = document.getElementById('navbar');
  const existingInfo = document.getElementById('nav-user-info');
  if (existingInfo) existingInfo.remove();
  const userInfo = document.createElement('div');
  userInfo.id = 'nav-user-info';
  userInfo.className = 'nav-user-info';
  const roleEmoji = role === 'admin' ? '👑' : role === 'client' ? '🏋️' : '👤';
  const roleBadgeColor = role === 'admin' ? '#ff006e' : role === 'client' ? '#00f0ff' : 'rgba(255,255,255,.3)';
  userInfo.innerHTML = `
    <div class="nav-avatar" style="border-color:${roleBadgeColor}">${roleEmoji}</div>
    <div class="nav-uname">
      <span>${currentUser.username}</span>
      <span class="nav-role" style="color:${roleBadgeColor}">${role.toUpperCase()}</span>
    </div>
    <button class="nav-logout" onclick="doLogout()">Sign Out</button>
  `;
  navbar.appendChild(userInfo);

  // Show admin nav link
  if (role === 'admin') {
    const adminLink = document.querySelector('.nav-links');
    if (adminLink && !document.getElementById('admin-nav-link')) {
      const li = document.createElement('li');
      li.innerHTML = '<a href="#admin" id="admin-nav-link" onclick="document.getElementById(\'admin-panel\').scrollIntoView({behavior:\'smooth\'})">👑 Admin</a>';
      adminLink.appendChild(li);
    }
    document.getElementById('admin-panel').style.display = 'block';
    loadAdminPanel();
  }

  // Guest restrictions
  if (role === 'guest') {
    document.getElementById('plan').style.opacity = '0.5';
    document.querySelectorAll('.tracker-card').forEach(c => {
      const overlay = document.createElement('div');
      overlay.className = 'locked-overlay';
      overlay.innerHTML = '<div class="lock-msg">🔒 <strong>Login to save data</strong><br><a href="/login" style="color:var(--cyan)">Sign in →</a></div>';
      overlay.style.cssText = 'position:absolute;inset:0;background:rgba(6,6,15,.85);border-radius:inherit;display:flex;align-items:center;justify-content:center;z-index:5;backdrop-filter:blur(4px)';
      c.style.position = 'relative';
      c.appendChild(overlay);
    });
  }
}

async function doLogout() {
  const token = getToken();
  if (token && token !== 'guest') {
    await fetch('/api/auth/logout', { method: 'POST', headers: { Authorization: 'Bearer ' + token } }).catch(()=>{});
  }
  localStorage.removeItem('fitbot-token');
  localStorage.removeItem('fitbot-user');
  localStorage.removeItem('fitbot-chat');
  window.location.href = '/login';
}

// ---- Admin Panel ----
async function loadAdminPanel() {
  const token = getToken();
  try {
    const [usersRes, statsRes] = await Promise.all([
      fetch('/api/admin/users', { headers: { Authorization: 'Bearer ' + token } }),
      fetch('/api/admin/stats', { headers: { Authorization: 'Bearer ' + token } })
    ]);
    const { users } = await usersRes.json();
    const stats = await statsRes.json();

    document.getElementById('admin-stats').innerHTML = `
      <div class="admin-stat"><div class="as-val">${stats.total_users}</div><div class="as-lbl">Total Users</div></div>
      <div class="admin-stat"><div class="as-val">${stats.total_workout_logs}</div><div class="as-lbl">Workout Logs</div></div>
      <div class="admin-stat"><div class="as-val">${stats.total_water_glasses}</div><div class="as-lbl">Water Glasses</div></div>
      <div class="admin-stat"><div class="as-val">${stats.total_progress_entries}</div><div class="as-lbl">Progress Entries</div></div>
    `;

    const tbody = document.getElementById('admin-users-body');
    tbody.innerHTML = users.map(u => `
      <tr>
        <td>${u.username}</td>
        <td style="color:rgba(255,255,255,.5);font-size:.8rem">${u.email}</td>
        <td><span class="role-pill ${u.role}">${u.role === 'admin' ? '👑' : '🏋️'} ${u.role}</span></td>
        <td style="color:rgba(255,255,255,.4);font-size:.75rem">${(u.created_at||'').slice(0,10)}</td>
        <td>
          ${u.id !== currentUser.id ? `
            <button class="admin-action-btn" onclick="changeRole(${u.id},'${u.role==='admin'?'client':'admin'}')">${u.role==='admin'?'↓ Client':'↑ Admin'}</button>
            <button class="admin-action-btn danger" onclick="deleteUser(${u.id})">🗑️</button>
          ` : '<span style="color:rgba(255,255,255,.2);font-size:.75rem">You</span>'}
        </td>
      </tr>
    `).join('');
  } catch (e) { console.error(e); }
}

async function deleteUser(id) {
  if (!confirm('Delete this user?')) return;
  await fetch(`/api/admin/users/${id}`, { method: 'DELETE', headers: { Authorization: 'Bearer ' + getToken() } });
  loadAdminPanel();
  showToast('✅ User deleted');
}

async function changeRole(id, newRole) {
  await fetch(`/api/admin/users/${id}/role`, {
    method: 'PATCH',
    headers: { Authorization: 'Bearer ' + getToken(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ role: newRole })
  });
  loadAdminPanel();
  showToast(`✅ Role updated to ${newRole}`);
}



// DOM
const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const typingIndicator = document.getElementById('typing-indicator');
const planForm = document.getElementById('plan-form');
const planResult = document.getElementById('plan-result');

// ---- Nav ----
document.querySelectorAll('.nav-links a').forEach(link => {
  link.addEventListener('click', () => {
    document.querySelectorAll('.nav-links a').forEach(l => l.classList.remove('active'));
    link.classList.add('active');
  });
});
const sections = document.querySelectorAll('section[id]');
window.addEventListener('scroll', () => {
  const pos = window.scrollY + 150;
  sections.forEach(s => {
    const link = document.querySelector(`.nav-links a[href="#${s.id}"]`);
    if (link && pos >= s.offsetTop && pos < s.offsetTop + s.offsetHeight) {
      document.querySelectorAll('.nav-links a').forEach(l => l.classList.remove('active'));
      link.classList.add('active');
    }
  });
});

// ---- Toast ----
function showToast(msg) {
  const t = document.createElement('div');
  t.className = 'toast';
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3000);
}

// ---- Chat ----
function addMessage(text, type) {
  const div = document.createElement('div');
  div.className = `message ${type}`;
  const av = document.createElement('div');
  av.className = 'msg-avatar';
  av.textContent = type === 'ai' ? '🤖' : '🏋️';
  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  bubble.innerHTML = text.replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  div.appendChild(av);
  div.appendChild(bubble);
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  chatHistory.push({ text, type, time: Date.now() });
  try { localStorage.setItem('fitbot-chat', JSON.stringify(chatHistory.slice(-50))); } catch(e){}
}

function showTyping() { typingIndicator.classList.add('active'); chatMessages.scrollTop = chatMessages.scrollHeight; }
function hideTyping() { typingIndicator.classList.remove('active'); }

async function sendMessage() {
  const msg = chatInput.value.trim();
  if (!msg) return;
  addMessage(msg, 'user');
  chatInput.value = '';
  showTyping();
  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg })
    });
    const data = await res.json();
    await new Promise(r => setTimeout(r, 500 + Math.random() * 700));
    hideTyping();
    addMessage(data.reply, 'ai');
  } catch {
    hideTyping();
    addMessage('⚠️ Connection issue. Please make sure the server is running.', 'ai');
  }
}

chatInput.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } });
sendBtn.addEventListener('click', sendMessage);
document.querySelectorAll('.quick-btn').forEach(btn => btn.addEventListener('click', () => { chatInput.value = btn.dataset.msg; sendMessage(); }));

document.getElementById('clear-chat-btn').addEventListener('click', () => {
  chatMessages.innerHTML = '';
  chatHistory = [];
  localStorage.removeItem('fitbot-chat');
  setTimeout(() => addMessage("Chat cleared! 👋 I'm FitBot — ask me anything about fitness or wellness!", 'ai'), 300);
});

// ---- Plan ----
planForm.addEventListener('submit', async e => {
  e.preventDefault();
  const formData = {
    age: parseInt(document.getElementById('age').value),
    weight: parseFloat(document.getElementById('weight').value),
    height: parseFloat(document.getElementById('height').value),
    goal: document.getElementById('goal').value,
    experience: document.getElementById('experience').value
  };
  planResult.innerHTML = `<div class="empty-state"><div class="icon" style="animation:pulse 1s infinite">⏳</div><p>Generating your personalized plan...</p></div>`;
  try {
    const res = await fetch(`${API_BASE}/api/plan`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(formData)
    });
    const data = await res.json();
    planResult.innerHTML = `<div class="plan-output">${formatPlan(data.plan)}</div>`;
  } catch {
    planResult.innerHTML = `<div class="plan-output" style="color:var(--magenta)">❌ Failed to generate plan.</div>`;
  }
});

function formatPlan(plan) {
  return plan
    .replace(/WORKOUT/g, '<strong>💪 WORKOUT</strong>')
    .replace(/DIET/g, '<strong>🥗 DIET</strong>')
    .replace(/CARDIO/g, '<strong>🏃 CARDIO</strong>')
    .replace(/TIPS/g, '<strong>💡 TIPS</strong>')
    .replace(/Age:/g, '<strong>📊 Age:</strong>')
    .replace(/BMI:/g, '<strong>BMI:</strong>');
}

// ---- Daily Tip ----
async function loadDailyTip() {
  try {
    const res = await fetch(`${API_BASE}/api/tips`);
    const data = await res.json();
    document.getElementById('daily-tip-text').textContent = data.tip;
    document.getElementById('daily-tip-emoji').textContent = data.emoji;
  } catch {
    document.getElementById('daily-tip-text').textContent = 'Stay consistent. Small steps lead to big results.';
  }
}

// ---- BMI Calculator ----
function calcBMI() {
  const w = parseFloat(document.getElementById('bmi-weight').value);
  const h = parseFloat(document.getElementById('bmi-height').value);
  if (!w || !h) return showToast('⚠️ Enter weight and height');
  const bmi = +(w / ((h/100)**2)).toFixed(1);
  const result = document.getElementById('bmi-result');
  result.style.display = 'block';
  document.getElementById('bmi-value-text').textContent = bmi;
  // Animate arc: BMI 15=0% to 40=100%
  const pct = Math.min(Math.max((bmi - 15) / 25, 0), 1);
  document.getElementById('bmi-arc').style.strokeDashoffset = 251 - (251 * pct);
  let cat, color, tip;
  if (bmi < 18.5) { cat='Underweight'; color='#00f0ff'; tip='Focus on eating more nutrient-dense foods and building muscle mass.'; }
  else if (bmi < 25) { cat='Normal Weight ✅'; color='#39ff14'; tip='Great! Maintain your healthy lifestyle with balanced nutrition and regular exercise.'; }
  else if (bmi < 30) { cat='Overweight'; color='#ff8c00'; tip='A moderate calorie deficit with strength training will help improve body composition.'; }
  else { cat='Obese'; color='#ff006e'; tip='Consult a healthcare professional and focus on sustainable lifestyle changes.'; }
  const catEl = document.getElementById('bmi-category');
  catEl.textContent = cat; catEl.style.color = color;
  document.getElementById('bmi-tip').textContent = tip;
}

// ---- TDEE Calculator ----
function calcTDEE() {
  const age = parseInt(document.getElementById('tdee-age').value);
  const w = parseFloat(document.getElementById('tdee-weight').value);
  const h = parseFloat(document.getElementById('tdee-height').value);
  const gender = document.getElementById('tdee-gender').value;
  const activity = parseFloat(document.getElementById('tdee-activity').value);
  if (!age || !w || !h) return showToast('⚠️ Fill all TDEE fields');
  let bmr = gender === 'male'
    ? 10*w + 6.25*h - 5*age + 5
    : 10*w + 6.25*h - 5*age - 161;
  bmr = Math.round(bmr);
  const tdee = Math.round(bmr * activity);
  const cut = tdee - 500;
  const bulk = tdee + 300;
  document.getElementById('tdee-result').style.display = 'block';
  document.getElementById('tdee-bmr').textContent = bmr;
  document.getElementById('tdee-tdee').textContent = tdee;
  document.getElementById('tdee-cut').textContent = cut;
  document.getElementById('tdee-bulk').textContent = bulk;
  const protein = Math.round(w * 2);
  const fat = Math.round(w * 0.9);
  const carbs = Math.round((tdee - protein*4 - fat*9) / 4);
  document.getElementById('macros-result').innerHTML =
    `<strong style="color:var(--cyan)">📊 Macro Guide (Maintenance)</strong><br>
    🥩 Protein: <strong>${protein}g</strong> (${protein*4} kcal)<br>
    🥑 Fat: <strong>${fat}g</strong> (${fat*9} kcal)<br>
    🍚 Carbs: <strong>${Math.max(carbs,0)}g</strong> (${Math.max(carbs,0)*4} kcal)`;
}

// ---- 1RM Calculator ----
function calcORM() {
  const w = parseFloat(document.getElementById('orm-weight').value);
  const r = parseInt(document.getElementById('orm-reps').value);
  if (!w || !r) return showToast('⚠️ Enter weight and reps');
  if (r === 1) { document.getElementById('orm-result').style.display='block'; document.getElementById('orm-max').textContent=`${w} kg = 100%`; document.getElementById('orm-table').innerHTML=''; return; }
  const orm = Math.round(w * (1 + r/30));
  document.getElementById('orm-result').style.display = 'block';
  document.getElementById('orm-max').textContent = `Estimated 1RM: ${orm} kg`;
  const pcts = [100,95,90,85,80,75,70,65,60];
  document.getElementById('orm-table').innerHTML = `<table class="orm-table"><tbody>` +
    pcts.map(p => `<tr><td>${p}%</td><td>${Math.round(orm * p/100)} kg</td></tr>`).join('') +
    `</tbody></table>`;
}

// ---- Stopwatch ----
let swInterval = null, swRunning = false, swMs = 0, swLaps = [];
function swTick() { swMs += 100; document.getElementById('sw-display').textContent = fmtTime(swMs); }
function swToggle() {
  if (swRunning) { clearInterval(swInterval); swRunning = false; document.getElementById('sw-start').textContent = '▶ Resume'; }
  else { swInterval = setInterval(swTick, 100); swRunning = true; document.getElementById('sw-start').textContent = '⏸ Pause'; }
}
function swReset() {
  clearInterval(swInterval); swRunning = false; swMs = 0; swLaps = [];
  document.getElementById('sw-display').textContent = '00:00:00';
  document.getElementById('sw-start').textContent = '▶ Start';
  document.getElementById('lap-list').innerHTML = '';
}
function swLap() {
  if (!swRunning) return;
  swLaps.push(swMs);
  const li = document.createElement('div');
  li.className = 'lap-item';
  li.innerHTML = `<span>Lap ${swLaps.length}</span><span>${fmtTime(swMs)}</span>`;
  document.getElementById('lap-list').prepend(li);
}
function fmtTime(ms) {
  const h = Math.floor(ms/3600000), m = Math.floor((ms%3600000)/60000), s = Math.floor((ms%60000)/1000);
  return `${pad(h)}:${pad(m)}:${pad(s)}`;
}
function pad(n) { return String(n).padStart(2,'0'); }

// ---- Rest Timer ----
let restTotal = 60, restLeft = 60, restInterval = null, restRunning = false;
function setRest(s) {
  restTotal = s; restLeft = s; restRunning = false;
  clearInterval(restInterval);
  document.getElementById('rest-display').textContent = s;
  document.getElementById('rest-ring-circle').style.strokeDashoffset = 0;
  document.getElementById('rest-start').textContent = '▶ Start';
  document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
}
function restToggle() {
  if (restRunning) { clearInterval(restInterval); restRunning = false; document.getElementById('rest-start').textContent = '▶ Resume'; }
  else {
    if (restLeft <= 0) restReset();
    restRunning = true;
    document.getElementById('rest-start').textContent = '⏸ Pause';
    restInterval = setInterval(() => {
      restLeft--;
      document.getElementById('rest-display').textContent = restLeft;
      const pct = (restTotal - restLeft) / restTotal;
      document.getElementById('rest-ring-circle').style.strokeDashoffset = 314 * pct;
      if (restLeft <= 0) { clearInterval(restInterval); restRunning = false; document.getElementById('rest-start').textContent = '▶ Start'; playBeep(); showToast('✅ Rest complete! Time to work!'); }
    }, 1000);
  }
}
function restReset() {
  clearInterval(restInterval); restRunning = false; restLeft = restTotal;
  document.getElementById('rest-display').textContent = restTotal;
  document.getElementById('rest-ring-circle').style.strokeDashoffset = 0;
  document.getElementById('rest-start').textContent = '▶ Start';
}
function playBeep() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    [0, 0.15, 0.3].forEach(t => {
      const o = ctx.createOscillator(), g = ctx.createGain();
      o.connect(g); g.connect(ctx.destination);
      o.frequency.value = 880; g.gain.setValueAtTime(.3, ctx.currentTime+t);
      g.gain.exponentialRampToValueAtTime(.001, ctx.currentTime+t+.12);
      o.start(ctx.currentTime+t); o.stop(ctx.currentTime+t+.12);
    });
  } catch(e){}
}
function switchTimer(mode) {
  document.querySelectorAll('.timer-tab').forEach(t => t.classList.remove('active'));
  event.target.classList.add('active');
  document.getElementById('stopwatch-panel').style.display = mode==='stopwatch' ? 'block' : 'none';
  document.getElementById('rest-panel').style.display = mode==='rest' ? 'block' : 'none';
}

// ---- Water Tracker ----
let waterCount = 0;
const WATER_GOAL = 8;
async function initWater() {
  try {
    const res = await fetch(`${API_BASE}/api/water`);
    const data = await res.json();
    waterCount = data.glasses || 0;
  } catch { waterCount = parseInt(localStorage.getItem('water-today') || '0'); }
  renderWater();
}
async function addWater(n) {
  waterCount = Math.min(waterCount + n, WATER_GOAL + 4);
  try { await fetch(`${API_BASE}/api/water`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({glasses:n}) }); }
  catch { localStorage.setItem('water-today', waterCount); }
  renderWater();
  if (waterCount === WATER_GOAL) showToast('🎉 Daily water goal reached!');
}
function removeWater() { if(waterCount>0){ waterCount--; localStorage.setItem('water-today',waterCount); renderWater(); } }
function renderWater() {
  const pct = Math.min(waterCount / WATER_GOAL * 100, 100);
  document.getElementById('water-fill').style.height = pct + '%';
  document.getElementById('water-label').textContent = `${waterCount} / ${WATER_GOAL}`;
  const gc = document.getElementById('water-glasses');
  gc.innerHTML = '';
  for(let i=0;i<WATER_GOAL;i++){
    const g = document.createElement('div');
    g.className = 'water-glass' + (i < waterCount ? ' filled' : '');
    g.textContent = '🥤';
    gc.appendChild(g);
  }
  const tip = document.getElementById('water-tip');
  const left = Math.max(WATER_GOAL - waterCount, 0);
  tip.textContent = left > 0 ? `${left} more glass${left===1?'':'es'} to reach your daily goal of ${WATER_GOAL} glasses (2L)` : '🎉 Daily hydration goal achieved!';
}

// ---- Workout Logger ----
async function logWorkout() {
  const exercise = document.getElementById('log-exercise').value.trim();
  const sets = parseInt(document.getElementById('log-sets').value);
  const reps = parseInt(document.getElementById('log-reps').value);
  const weight = parseFloat(document.getElementById('log-weight').value) || 0;
  if (!exercise || !sets || !reps) return showToast('⚠️ Fill exercise, sets and reps');
  try {
    await fetch(`${API_BASE}/api/workout-log`, {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ exercise, sets, reps, weight, notes: '' })
    });
    showToast('✅ Exercise logged!');
  } catch { showToast('⚠️ Saved locally'); }
  const logs = JSON.parse(localStorage.getItem('workout-logs') || '[]');
  logs.unshift({ exercise, sets, reps, weight, time: new Date().toLocaleTimeString() });
  localStorage.setItem('workout-logs', JSON.stringify(logs.slice(0, 50)));
  ['log-exercise','log-sets','log-reps','log-weight'].forEach(id => document.getElementById(id).value = '');
  loadWorkoutLog();
}
async function loadWorkoutLog() {
  let logs = [];
  try {
    const res = await fetch(`${API_BASE}/api/workout-log?days=1`);
    const data = await res.json();
    logs = data.logs.map(l => ({ exercise: l.exercise, sets: l.sets, reps: l.reps, weight: l.weight, time: l.logged_at.slice(11,16) }));
  } catch { logs = JSON.parse(localStorage.getItem('workout-logs') || '[]'); }
  const tbody = document.getElementById('log-body');
  const empty = document.getElementById('log-empty');
  tbody.innerHTML = '';
  if (!logs.length) { empty.style.display='block'; return; }
  empty.style.display = 'none';
  logs.slice(0,10).forEach(l => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${l.exercise}</td><td>${l.sets}</td><td>${l.reps}</td><td>${l.weight||0}</td><td>${l.time||''}</td>`;
    tbody.appendChild(tr);
  });
}

// ---- Progress Logger ----
async function logProgress() {
  const weight = parseFloat(document.getElementById('prog-weight').value);
  const bf = parseFloat(document.getElementById('prog-bf').value) || null;
  const notes = document.getElementById('prog-notes').value.trim();
  if (!weight) return showToast('⚠️ Enter your weight');
  try {
    await fetch(`${API_BASE}/api/progress`, {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ weight, body_fat: bf, notes })
    });
    showToast('📈 Progress logged!');
  } catch { showToast('⚠️ Saved locally'); }
  const logs = JSON.parse(localStorage.getItem('progress-logs') || '[]');
  logs.unshift({ weight, body_fat: bf, notes, logged_at: new Date().toISOString() });
  localStorage.setItem('progress-logs', JSON.stringify(logs.slice(0,30)));
  ['prog-weight','prog-bf','prog-notes'].forEach(id => document.getElementById(id).value = '');
  loadProgress();
}
async function loadProgress() {
  let history = [];
  try {
    const res = await fetch(`${API_BASE}/api/progress`);
    const data = await res.json();
    history = data.history;
  } catch { history = JSON.parse(localStorage.getItem('progress-logs') || '[]'); }
  const el = document.getElementById('progress-history');
  if (!history.length) { el.innerHTML = '<div class="log-empty">No progress entries yet.</div>'; return; }
  el.innerHTML = history.slice(0,8).map(h => `
    <div class="progress-row">
      <span class="pw">⚖️ ${h.weight} kg${h.body_fat ? ` · ${h.body_fat}% BF` : ''}</span>
      <span class="pdate">${(h.logged_at||'').slice(0,10) || 'Today'}</span>
    </div>`).join('');
}

// ---- Exercise Library ----
const EXERCISES = [
  {name:'Barbell Squat',muscle:'Legs',equipment:'Barbell',difficulty:'hard',instructions:'Stand feet shoulder-width apart. Bar on upper traps. Squat until thighs parallel. Drive through heels.'},
  {name:'Romanian Deadlift',muscle:'Legs',equipment:'Barbell',difficulty:'medium',instructions:'Hinge at hips, push them back. Keep bar close to legs. Feel hamstring stretch. Drive hips forward.'},
  {name:'Leg Press',muscle:'Legs',equipment:'Machine',difficulty:'easy',instructions:'Feet shoulder-width on platform. Lower until 90° knee angle. Press through heels.'},
  {name:'Hip Thrust',muscle:'Glutes',equipment:'Barbell',difficulty:'medium',instructions:'Shoulder blades on bench, bar on hips. Drive hips up. Squeeze glutes at top. Lower with control.'},
  {name:'Walking Lunges',muscle:'Legs',equipment:'Bodyweight',difficulty:'easy',instructions:'Step forward, lower back knee toward floor. Push off front foot to step through. Alternate legs.'},
  {name:'Calf Raises',muscle:'Legs',equipment:'Bodyweight',difficulty:'easy',instructions:'Stand on edge of step. Rise onto toes. Hold 1s. Lower slowly below step level for full ROM.'},
  {name:'Goblet Squat',muscle:'Legs',equipment:'Dumbbell',difficulty:'easy',instructions:'Hold dumbbell at chest. Squat deep, elbows inside knees. Drive up through heels.'},
  {name:'Box Jump',muscle:'Legs',equipment:'Box',difficulty:'medium',instructions:'Stand facing box. Jump explosively, land softly with bent knees. Step down carefully.'},
  {name:'Bench Press',muscle:'Chest',equipment:'Barbell',difficulty:'hard',instructions:'Retract shoulder blades. Lower bar to chest. Press explosively. Keep feet flat on floor.'},
  {name:'Incline DB Press',muscle:'Chest',equipment:'Dumbbell',difficulty:'medium',instructions:'Set bench to 30-45°. Press dumbbells from shoulder height. Arch naturally. Full ROM.'},
  {name:'Cable Fly',muscle:'Chest',equipment:'Cable',difficulty:'easy',instructions:'Set cables at shoulder height. Slight bend in elbows. Bring hands together in arc. Squeeze chest.'},
  {name:'Push-up',muscle:'Chest',equipment:'Bodyweight',difficulty:'easy',instructions:'Hands slightly wider than shoulders. Lower chest to floor. Push back up. Keep core tight.'},
  {name:'Dips',muscle:'Chest',equipment:'Bodyweight',difficulty:'medium',instructions:'Lean forward for chest emphasis. Lower until shoulders below elbows. Press up to lockout.'},
  {name:'Deadlift',muscle:'Back',equipment:'Barbell',difficulty:'hard',instructions:'Hip-width stance. Bar over mid-foot. Hinge down, grip. Drive through floor. Lock out hips at top.'},
  {name:'Pull-up',muscle:'Back',equipment:'Bodyweight',difficulty:'hard',instructions:'Dead hang. Pull elbows to hips. Chin over bar. Lower with control. Full dead hang each rep.'},
  {name:'Barbell Row',muscle:'Back',equipment:'Barbell',difficulty:'hard',instructions:'Hip hinge, back parallel to floor. Pull bar to lower chest. Squeeze shoulder blades. Lower slowly.'},
  {name:'Lat Pulldown',muscle:'Back',equipment:'Cable',difficulty:'easy',instructions:'Wide overhand grip. Pull bar to upper chest. Lean back slightly. Squeeze lats at bottom.'},
  {name:'Seated Cable Row',muscle:'Back',equipment:'Cable',difficulty:'easy',instructions:'Pull to lower chest. Squeeze shoulder blades together. Control the eccentric to full stretch.'},
  {name:'Good Morning',muscle:'Back',equipment:'Barbell',difficulty:'medium',instructions:'Bar on upper back. Hinge at hips, lower torso to parallel keeping back neutral. Drive hips forward.'},
  {name:'Face Pull',muscle:'Shoulders',equipment:'Cable',difficulty:'easy',instructions:'Set cable at face height. Pull toward forehead. Flare elbows out. Great for rear delts and posture.'},
  {name:'Overhead Press',muscle:'Shoulders',equipment:'Barbell',difficulty:'hard',instructions:'Bar at shoulder level. Press straight up. Lock out overhead. Lower to front of shoulders.'},
  {name:'Lateral Raise',muscle:'Shoulders',equipment:'Dumbbell',difficulty:'easy',instructions:'Slight bend in elbows. Raise to shoulder height. Lead with elbows. Lower slowly (3s).'},
  {name:'Arnold Press',muscle:'Shoulders',equipment:'Dumbbell',difficulty:'medium',instructions:'Start palms facing you. Rotate as you press overhead. Reverse on the way down.'},
  {name:'Rear Delt Fly',muscle:'Shoulders',equipment:'Dumbbell',difficulty:'easy',instructions:'Hinge forward at hips. Raise dumbbells to sides. Squeeze rear delts. Control down.'},
  {name:'Barbell Curl',muscle:'Arms',equipment:'Barbell',difficulty:'easy',instructions:'Keep elbows at sides. Curl to shoulder height. Squeeze bicep. Lower slowly with control.'},
  {name:'Hammer Curl',muscle:'Arms',equipment:'Dumbbell',difficulty:'easy',instructions:'Neutral grip (thumbs up). Curl without rotating wrist. Targets brachialis for arm thickness.'},
  {name:'Skull Crushers',muscle:'Arms',equipment:'Barbell',difficulty:'medium',instructions:'Lie on bench. Lower bar to forehead by bending elbows only. Press back up.'},
  {name:'Cable Pushdown',muscle:'Arms',equipment:'Cable',difficulty:'easy',instructions:'Keep elbows at sides. Push down to full extension. Squeeze triceps at bottom. Control up.'},
  {name:'Plank',muscle:'Core',equipment:'Bodyweight',difficulty:'easy',instructions:'Forearms on floor. Body in straight line. Brace core and glutes. Breathe. Hold 30-60s.'},
  {name:'Ab Rollout',muscle:'Core',equipment:'Ab Wheel',difficulty:'hard',instructions:'Kneel with wheel. Roll out until nearly flat. Pull back using abs only. Do not let back arch.'},
  {name:'Hanging Leg Raise',muscle:'Core',equipment:'Bar',difficulty:'medium',instructions:'Dead hang. Raise legs to 90° or higher. Control the descent. No swinging.'},
  {name:'Cable Crunch',muscle:'Core',equipment:'Cable',difficulty:'easy',instructions:'Kneel below cable. Pull rope to head sides. Crunch down. Hold 1s at bottom. Control up.'},
  {name:'Dead Bug',muscle:'Core',equipment:'Bodyweight',difficulty:'easy',instructions:'Lie on back, arms and legs up. Lower opposite arm and leg. Keep lower back pressed to floor.'},
  {name:'Pallof Press',muscle:'Core',equipment:'Cable',difficulty:'easy',instructions:'Cable at chest height. Press straight out. Resist rotation. Hold 2s. Pull back in.'},
  {name:'Running',muscle:'Cardio',equipment:'None',difficulty:'medium',instructions:'Start at conversational pace. Build to 20-30 min runs. Zone 2: can hold a conversation.'},
  {name:'HIIT Sprint',muscle:'Cardio',equipment:'None',difficulty:'hard',instructions:'Sprint 20-30s at max effort. Walk/jog 40-60s recovery. Repeat 8-10 times. Total ~20 min.'},
  {name:'Jump Rope',muscle:'Cardio',equipment:'Jump Rope',difficulty:'medium',instructions:'Keep elbows at sides, wrists rotate rope. Land softly on balls of feet. 2-3 min rounds.'},
  {name:'Burpee',muscle:'Cardio',equipment:'Bodyweight',difficulty:'hard',instructions:'Jump up, drop to plank, do push-up, jump feet forward, jump up. Full body conditioning.'},
  {name:'Kettlebell Swing',muscle:'Glutes',equipment:'Kettlebell',difficulty:'medium',instructions:'Hip hinge back, swing KB between legs. Drive hips forward explosively. KB floats to shoulder height.'},
];

let activeFilter = 'All';
function initExerciseLibrary() {
  const muscles = ['All', ...new Set(EXERCISES.map(e => e.muscle))];
  document.getElementById('muscle-filters').innerHTML = muscles.map(m =>
    `<button class="filter-btn${m==='All'?' active':''}" onclick="setFilter('${m}', this)">${m}</button>`
  ).join('');
  renderExercises();
}
function setFilter(muscle, btn) {
  activeFilter = muscle;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  renderExercises();
}
function filterExercises() { renderExercises(); }
function renderExercises() {
  const query = (document.getElementById('exercise-search').value || '').toLowerCase();
  const filtered = EXERCISES.filter(e =>
    (activeFilter === 'All' || e.muscle === activeFilter) &&
    (!query || e.name.toLowerCase().includes(query) || e.muscle.toLowerCase().includes(query))
  );
  const grid = document.getElementById('exercise-grid');
  if (!filtered.length) { grid.innerHTML = '<p style="color:var(--text-muted);grid-column:1/-1;text-align:center;padding:2rem">No exercises found.</p>'; return; }
  grid.innerHTML = filtered.map((e,i) => `
    <div class="exercise-card" onclick="this.classList.toggle('expanded')">
      <div class="ex-header"><div class="ex-name">${e.name}</div><div class="ex-muscle">${e.muscle}</div></div>
      <div class="ex-meta">
        <span class="ex-tag">🏋️ ${e.equipment}</span>
        <span class="ex-difficulty ${e.difficulty}">${e.difficulty==='easy'?'🟢 Beginner':e.difficulty==='medium'?'🟡 Intermediate':'🔴 Advanced'}</span>
      </div>
      <div class="ex-expand">Tap to see instructions ▾</div>
      <div class="ex-instructions">${e.instructions}</div>
    </div>`).join('');
}

// ---- Scroll Animations ----
const observer = new IntersectionObserver(entries => {
  entries.forEach(e => { if (e.isIntersecting) { e.target.style.opacity='1'; e.target.style.transform='translateY(0)'; } });
}, { threshold: 0.1 });
document.querySelectorAll('.glass-card, .feature-card').forEach(el => {
  el.style.opacity = '0'; el.style.transform = 'translateY(20px)';
  el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
  observer.observe(el);
});

// ---- Load Chat History ----
function loadChatHistory() {
  try { JSON.parse(localStorage.getItem('fitbot-chat') || '[]').forEach(m => addMessage(m.text, m.type)); } catch {}
}

// ---- Init ----
document.addEventListener('DOMContentLoaded', async () => {
  const authed = await initAuth();
  if (!authed) return;
  loadChatHistory();
  loadDailyTip();
  initWater();
  loadWorkoutLog();
  loadProgress();
  initExerciseLibrary();
  if (chatHistory.length === 0) {
    const name = currentUser?.username || 'there';
    const role = currentUser?.role || 'guest';
    const greeting = role === 'admin'
      ? `Welcome back, Admin ${name}! 👑 You have full control. Ask me anything or manage users in the Admin Panel.`
      : role === 'guest'
      ? `Hey! 👤 You're browsing as a guest. You can use the chat and calculators freely. Sign in to unlock tracking features!`
      : `Hey ${name}! 💪 I'm FitBot — your AI fitness coach. Ask me anything about workouts, nutrition, injuries, or wellness!`;
    setTimeout(() => addMessage(greeting, 'ai'), 800);
  }
});


