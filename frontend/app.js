const tabs = document.querySelectorAll('.tab-btn');
const panels = {
  auto1: document.getElementById('panel-auto1'),
  single: document.getElementById('panel-single'),
  arrows: document.getElementById('panel-arrows'),
};

const navList = [
  document.getElementById('tab-single'),
  document.getElementById('tab-arrows'),
  document.getElementById('tab-auto1'),
  document.getElementById('singleDirection'),
  document.getElementById('singleDistance'),
  document.getElementById('queueBtn'),
  document.getElementById('step'),
  document.getElementById('applyStep'),
];

camInfo1 = document.getElementById('cam-info1');
camInfo2 = document.getElementById('cam-info2');
camInfo3 = document.getElementById('cam-info3');
camInfo4 = document.getElementById('cam-info4');

let navIndex = 0;
let navMode = false; 
setInterval(updateCameraInfo, 300); 

function updateFocus() {
  const element = navList[navIndex];
  if (!element) return;
  element.focus();
}

let mode = 'single';

tabs.forEach(btn => {
  btn.addEventListener('click', () => {
    mode = btn.dataset.tab;                    
    tabs.forEach(b => b.classList.toggle('active', b === btn));
    Object.entries(panels).forEach(([name, el]) =>
      el.classList.toggle('active', name === mode)
    );
    append(`[mode] ${mode}`);
  });
});

const camBox  = document.getElementById('camBox');

// single steps 
const singleDirection = document.getElementById('singleDirection');
const singleDistance  = document.getElementById('singleDistance');
const lastDir         = document.getElementById('lastDir');
const lastDist        = document.getElementById('lastDist');

// continous steps
const stepInput = document.getElementById('step');
const contDir = document.getElementById('contDir');
const contBadge = document.getElementById('contBadge');
const logBox  = document.getElementById('log');

function append(line){
  logBox.textContent += line + "\n";
  logBox.scrollTop = logBox.scrollHeight;
}

// websocket backend
let ws;
try {
  ws = new WebSocket(`ws://${location.host}/ws`);
  ws.onopen = () => append('WS connected');
  ws.onmessage = (e) => {
    try {
      const m = JSON.parse(e.data || '{}');
      append(`[WS msg] ${JSON.stringify(m)}`);
      if (m.type === 'key' && m.token) handleKeyToken(m.token, m.pressed);
    } catch (err) {
      append(`WS parse error: ${err}`);
    }
  };
  ws.onerror = () => append('WS error');
  ws.onclose = () => append('WS closed');
} catch {
  append('WS not available');
}

// REST helpers 
async function postJSON(url, body){
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(body || {})
    });
    return await res.json();
  } catch (e) {
    append(`ERR: ${e.message || e}`);
    return {ok:false, error:String(e)};
  }
}

// update camera info
async function updateCameraInfo() {
  try {
    const res = await fetch('/camera_info');
    if (!res.ok) return;
    const data = await res.json();
    const info = data.info || [];

    if (camInfo1 && info[0] != null) camInfo1.textContent = info[0];
    if (camInfo2 && info[1] != null) camInfo2.textContent = info[1];
    if (camInfo3 && info[2] != null) camInfo3.textContent = info[2];
    if (camInfo4 && info[3] != null) camInfo4.textContent = info[3];
  } catch (e) {
      append(`camera_info error: ${e}`);
  }
}

//queue single comman and apply step
document.getElementById('queueBtn').addEventListener('click', async () => {
  const dir  = singleDirection.value;                  // UP,DOWN,LEFT,RIGHT
  const dist = +(singleDistance.value || 0);
  if (!dir || !Number.isFinite(dist)) return;

  lastDir.textContent  = dir;
  lastDist.textContent = String(dist);
  append(`Queued: ${dir} ${dist}`);

  const axis = (dir === 'LEFT' || dir === 'RIGHT') ? 'X' : 'Y';
  const signed = (dir === 'UP' || dir === 'RIGHT') ? dist : -dist;

  await postJSON('/apply-step', { axis, dist: signed });
});

// apply step for continuous mode
document.getElementById('applyStep').addEventListener('click', () => {
  const v = +(stepInput.value || 0);
  if (!Number.isFinite(v) || v <= 0) {
    append('Step must be > 0');
    return;
  }
  contBadge.textContent = String(v);
  append(`Jog step set: ${v}`);
});

function handleKeyToken(token, pressed){
  // act on keydown only
  if (!pressed) return;

  // Toggle nav mode with NUM key
  if (token === "NUM") {
    navMode = !navMode;
    append(navMode ? "[nav] ON" : "[nav] OFF");
    if (navMode) {
      updateFocus();
    }
    return;
  }

  // If we're in nav mode, arrows move focus, ENTER clicks
  if (navMode) {
    const numArrowMap = { "8": "UP", "2": "DOWN", "4": "LEFT", "6": "RIGHT" };
    const dir = numArrowMap[token];

    if (dir === "RIGHT" || dir === "DOWN") {
      navIndex = (navIndex + 1) % navList.length;
      updateFocus();
      return;
    }
    if (dir === "LEFT" || dir === "UP") {
      navIndex = (navIndex - 1 + navList.length) % navList.length;
      updateFocus();
      return;
    }

    if (token === "ENTER") {
      const el = navList[navIndex];
      if (el && typeof el.click === "function") {
        el.click();
      }
      return;
    }

    // ignore all other tokens while in navMode
    return;
  }

  // Auto tab placeholder
  if (mode === 'auto1') {
    if (["UP","DOWN","LEFT","RIGHT"].includes(token)) {
      contDir.textContent = token;
      const stepVal = +(contBadge.textContent || 0);
      append(`Jog ${token} by ${stepVal}`);
      if (stepVal > 0) {
        const axis = (token === 'LEFT' || token === 'RIGHT') ? 'X' : 'Y';
        const signed = (token === 'UP' || token === 'RIGHT') ? stepVal : -stepVal;
        postJSON('/apply-step', { axis, dist: signed });
      }
    } else if (/^\d$/.test(token)) {
      stepInput.value = (stepInput.value || '') + token;
      append(`Step buffer: ${stepInput.value}`);
    } else if (token === "BACKSPACE") {
      stepInput.value = (stepInput.value || '').slice(0, -1);
    } else if (token === "ENTER") {
      document.getElementById('applyStep').click();
    }
  }

  if (mode === 'single') {
    if (["UP","DOWN","LEFT","RIGHT"].includes(token)) {
      lastDir.textContent = token;
      append(`Dir selected: ${token}`);
    } else if (/^\d$/.test(token)) {
      singleDistance.value = (singleDistance.value || '') + token;
    } else if (token === "BACKSPACE") {
      singleDistance.value = (singleDistance.value || '').slice(0, -1);
    } else if (token === "ENTER") {
      document.getElementById('queueBtn').click();
    }
    return;
  }

  if (mode === 'arrows') {
    if (["UP","DOWN","LEFT","RIGHT"].includes(token)) {
      contDir.textContent = token;
      const stepVal = +(contBadge.textContent || 0);
      append(`Jog ${token} by ${stepVal}`);
      if (stepVal > 0) {
        const axis = (token === 'LEFT' || token === 'RIGHT') ? 'X' : 'Y';
        const signed = (token === 'UP' || token === 'RIGHT') ? stepVal : -stepVal;
        postJSON('/apply-step', { axis, dist: signed });
      }
    } else if (/^\d$/.test(token)) {
      stepInput.value = (stepInput.value || '') + token;
      append(`Step buffer: ${stepInput.value}`);
    } else if (token === "BACKSPACE") {
      stepInput.value = (stepInput.value || '').slice(0, -1);
    } else if (token === "ENTER") {
      document.getElementById('applyStep').click();
    }
  }
}



  

