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

  // auto tab node
  if (mode === 'auto1') {
    // map keypad to start/stop buttons
    if (token === "ENTER") {
        startBtn.click();
    } else if (token === "BACKSPACE" || token === "0") {
        stopBtn.click();
    }
    return;
  }

  if (mode === 'single') {
    if (["UP","DOWN","LEFT","RIGHT"].includes(token)) {
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
    if (["UP","DOWN","LEFT","RIGHT"].includes(token)) {
      contDir.textContent = token;
      const stepVal = +(contBadge.textContent || 0);
      append(`Jog ${token} by ${stepVal}`);
      if (stepVal > 0) {
        const axis = (token === 'LEFT' || token === 'RIGHT') ? 'X' : 'Y';
        const dirSign = (token === 'UP' || token === 'RIGHT') ? 1 : -1;
        postJSON('/apply-step', { axis: axis, dist: stepVal, dirSign: dirSign });
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



  

