const tabs = document.querySelectorAll('.tab-btn');
const panels = {
  single: document.getElementById('panel-single'),
  arrows: document.getElementById('panel-arrows'),
  auto1: document.getElementById('panel-auto1'),
};

const navList = [
  document.getElementById('tab-single'),
  document.getElementById('tab-arrows'),
  document.getElementById('tab-auto1'),
  document.getElementById('dir-up'),
  document.getElementById('dir-down'),
  document.getElementById('dir-left'),
  document.getElementById('dir-right'),
  document.getElementById('singleDistance'),
  document.getElementById('queueBtn'),
  document.getElementById('step'),
  document.getElementById('applyStep'),
  document.getElementById('start'),
  document.getElementById('stop')
];

let navIndex = 0;
let navMode = false;  
let mode = 'single';

function updateFocus() {
  const element = navList[navIndex];
  if (!element) return;
  element.focus();
}

function append(line){
  const logBox = document.getElementById('log');
  logBox.textContent += line + "\n";
  logBox.scrollTop = logBox.scrollHeight;
}

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
const singleDistance  = document.getElementById('singleDistance');
const lastDir         = document.getElementById('lastDir');
const lastDist        = document.getElementById('lastDist');
const dirButtons = document.querySelectorAll('.dir-btn');
let currentDir = 'UP';

function setDirection(dir) {
  currentDir = dir
  dirButtons.forEach(btn => {
    btn.classList.toggle('active', btn.dataset.dir === dir);
  });
  lastDir.textContent = dir;
}

dirButtons.forEach(btn => {
  btn.addEventListener('click', () => {
    const dir = btn.dataset.dir;
    setDirection(dir);
    append(`Dir selected: ${dir}`);
  });
});

// continous steps
const stepInput = document.getElementById('step');
const contDir = document.getElementById('contDir');
const contBadge = document.getElementById('contBadge');
const logBox  = document.getElementById('log');
const startBtn = document.getElementById('start');
const stopBtn  = document.getElementById('stop');
const coordX   = document.getElementById('coordX');
const coordY   = document.getElementById('coordY');

// auto mode event listeners
startBtn.addEventListener('click', async () => {
  append('Auto sequence starting');
  // disable start and enable stop
  startBtn.disabled = true;
  stopBtn.disabled = false;
  await postJSON('/auto-control', { command: 'START' });
});

stopBtn.addEventListener('click', async () => {
  append('Auto sequence stopping');
  startBtn.disabled = false;
  stopBtn.disabled = true;
  await postJSON('/auto-control', { command: 'STOP' });
});

// websocket backend
let ws;
// handle status Messages
let lastStatus = null;

function connectWS() {
  try {
    ws = new WebSocket(`ws://${location.host}/ws`);
    ws.onopen = () => append('WS connected');
    ws.onmessage = (e) => {
      try {
        const m = JSON.parse(e.data || '{}');

      if (m.type === 'status') {
        const newStatus = `${m.pos}-${m.active}-${m.queue}`;

        if (newStatus !== lastStatus) {
          lastStatus = newStatus;
        }
        return; // dont log
      }

      // handle coordinates
      if (m.type === 'coords') {
        coordX.textContent = m.x.toFixed(2);
        coordY.textContent = m.y.toFixed(2);
        return;
      }

      // Handle keypad tokens
      if (m.type === 'key' && m.token) {
        handleKeyToken(m.token, m.pressed);
        return;
      }

      // Log anything else
      append(`[WS msg] ${JSON.stringify(m)}`);

    } catch (err) {
      console.error("WS message error:", err);
    }
};

    ws.onerror = () => append('WS error');
    ws.onclose = () => {
          append('WS closed');
          setTimeout(connectWS, 3000);
    };
    } catch (err) {
        append('WS not available');
    }
  }

connectWS();

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

//queue single comman and apply step
document.getElementById('queueBtn').addEventListener('click', async () => {
  const dir  = currentDir;                  // UP,DOWN,LEFT,RIGHT
  const dist = +(singleDistance.value || 0);
  if (!dir || !Number.isFinite(dist) || dist <= 0) {
    append('Distance must be > 0');
    return;
  }

  lastDir.textContent  = dir;
  lastDist.textContent = String(dist);
  append(`Queued: ${dir} ${dist}`);

  const axis = (dir === 'LEFT' || dir === 'RIGHT') ? 'x' : 'y';
  const dirSign = (dir === 'UP' || dir === 'RIGHT') ? 1 : -1;

  const res = await postJSON('/apply-step', { axis, dist: dist, dirSign: dirSign });

  append(`Server: ${JSON.stringify(res)}`);

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

function handleKeyToken(token, pressed) {
  const isDown = (pressed === true || String(pressed).toLowerCase() === "true" || pressed === 1);
  const dirMap = { "8": "UP", "2": "DOWN", "4": "LEFT", "6": "RIGHT", "UP": "UP", "DOWN": "DOWN", "LEFT": "LEFT", "RIGHT": "RIGHT" };
  const joyDir = dirMap[token];

  // # CHANGE BUTTON
  // if (token === "*") {
  //   postJSON('/toggle-cam', { active: isDown });
  //   return; 
  // }

  if (!isDown) {
    if (mode === 'arrows' && joyDir) {
      contDir.textContent = "—";
      append(`Joystick stopped`);
      postJSON('/stop-motion');
    }
    return; 
  }

  // toggle navigation Mode
  if (token === "NUM") {
    navMode = !navMode;
    append(navMode ? "[nav] ON" : "[nav] OFF");
    if (navMode) updateFocus();
    return;
  }

  if (navMode) {
    if (joyDir === "RIGHT" || joyDir === "DOWN") {
      navIndex = (navIndex + 1) % navList.length;
      updateFocus();
      return;
    }
    if (joyDir === "LEFT" || joyDir === "UP") {
      navIndex = (navIndex - 1 + navList.length) % navList.length;
      updateFocus();
      return;
    }
    if (token === "ENTER") {
      const el = navList[navIndex];
      if (el && typeof el.click === "function") el.click();
    }
    return; 
  }

  // state control modes
  if (mode === 'auto1') {
    if (token === "ENTER") startBtn.click();
    else if (token === "BACKSPACE" || token === "0") stopBtn.click();
    return;
  }

  if (mode === 'single') {
    if (["UP", "DOWN", "LEFT", "RIGHT"].includes(token)) {
      setDirection(token);
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
    if (joyDir) {
      contDir.textContent = joyDir;
      append(`Joystick moving: ${joyDir}`);
      const axis = (joyDir === 'LEFT' || joyDir === 'RIGHT') ? 'x' : 'y';
      const dirSign = (joyDir === 'UP' || joyDir === 'RIGHT') ? 1 : -1;
      postJSON('/apply-step', { axis: axis, dist: 9999, dirSign: dirSign });
    }
    return;
  }
}

// block browser from moving tabs
window.addEventListener('keydown', function(e) {
  if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(e.key)) {
    e.preventDefault();
  }
}, { passive: false });