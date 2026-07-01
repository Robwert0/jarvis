let sessionId = null;

const transcript = document.getElementById("transcript");
const form = document.getElementById("composer");
const input = document.getElementById("message");
const micBtn = document.getElementById("mic");

function addMessage(role, content) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = content;
  transcript.appendChild(div);
  transcript.scrollTop = transcript.scrollHeight;
}

function addChips(actions) {
  if (!actions || !actions.length) return;
  const wrap = document.createElement("div");
  wrap.className = "chips";
  for (const a of actions) {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = `${a.tool}: ${a.summary}`;
    wrap.appendChild(chip);
  }
  transcript.appendChild(wrap);
}

function speak(text) {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.speak(new SpeechSynthesisUtterance(text));
}

async function send(message) {
  addMessage("user", message);
  try {
    const res = await fetch("/jarvis/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id: sessionId }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    sessionId = data.session_id;
    addChips(data.actions);
    addMessage("assistant", data.reply);
    speak(data.reply);
    refreshSidebar();
  } catch (err) {
    addMessage("assistant", `[Error: ${err.message}]`);
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const message = input.value.trim();
  if (!message) return;
  input.value = "";
  send(message);
});

document.getElementById("new-chat").addEventListener("click", () => {
  sessionId = null;
  transcript.innerHTML = "";
});

async function refreshSidebar() {
  try {
    const convs = await (await fetch("/jarvis/conversations")).json();
    const ul = document.getElementById("conversations");
    ul.innerHTML = "";
    for (const c of convs) {
      const li = document.createElement("li");
      li.textContent = c.title || "(untitled)";
      if (c.id === sessionId) li.classList.add("active");
      li.addEventListener("click", () => openConversation(c.id));
      ul.appendChild(li);
    }
    const mems = await (await fetch("/jarvis/memories")).json();
    const mu = document.getElementById("memories");
    mu.innerHTML = "";
    for (const m of mems) {
      const li = document.createElement("li");
      li.textContent = m.content;
      mu.appendChild(li);
    }
  } catch (err) {
    console.error("refreshSidebar failed:", err);
  }
}

async function openConversation(id) {
  sessionId = id;
  transcript.innerHTML = "";
  const msgs = await (await fetch(`/jarvis/conversations/${id}`)).json();
  for (const m of msgs) addMessage(m.role, m.content);
  refreshSidebar();
}

// --- Web Speech (input) ---
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SR) {
  const recog = new SR();
  recog.lang = "en-US";
  micBtn.addEventListener("click", () => {
    if (micBtn.classList.contains("listening")) return;
    micBtn.classList.add("listening");
    recog.start();
  });
  recog.onresult = (e) => {
    input.value = e.results[0][0].transcript;
    micBtn.classList.remove("listening");
    form.requestSubmit();
  };
  recog.onend = () => micBtn.classList.remove("listening");
  recog.onerror = () => micBtn.classList.remove("listening");
} else {
  micBtn.style.display = "none";
}

refreshSidebar();
