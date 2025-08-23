import os
from flask import Flask, request, Response, render_template_string
from openai import OpenAI
from dotenv import load_dotenv

# ---------- Load Environment Variables ----------
load_dotenv()  # 👈 reads from .env file in your project root

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("⚠️ Missing OPENROUTER_API_KEY. Please set it in your .env file.")

# ---------- OpenAI Client ----------
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY
)

# ---------- Flask App ----------
app = Flask(__name__)

# ---------- Frontend UI ----------
PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>AlphaBros — GPT-5 (Streaming)</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
  <style>
    body {
      margin:0; padding:0;
      font-family: 'Inter', 'Segoe UI', sans-serif;
      display:flex; height:100vh; overflow:hidden;
      background:#111; color:#eee;
    }
    /* Sidebar */
    .sidebar {
      width:260px; background:#1e1e2f; border-right:1px solid #2a2a3a;
      display:flex; flex-direction:column; padding:15px; overflow-y:auto;
    }
    .sidebar h3 { margin:0 0 12px; color:#8b5cf6; font-size:1rem; }
    .tab {
      padding:10px; margin:4px 0; background:#26263a;
      border-radius:8px; cursor:pointer;
      display:flex; justify-content:space-between; align-items:center;
      transition:.2s;
    }
    .tab:hover { background:#33334d; }
    .tab.active { background:#8b5cf6; color:#fff; }
    .tab span { flex:1; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
    .tab button { background:none; border:none; color:#aaa; cursor:pointer; }
    .tab button:hover { color:#fff; }
    .new-chat {
      margin-top:10px; padding:10px; border:none; border-radius:8px;
      background:#8b5cf6; color:#fff; cursor:pointer; font-weight:bold;
    }
    /* Chat area */
    .shell { flex:1; display:flex; flex-direction:column; }
    header {
      height:50px; background:#1e1e2f; border-bottom:1px solid #2a2a3a;
      display:flex; align-items:center; justify-content:space-between;
      padding:0 15px; font-weight:bold; color:#8b5cf6;
    }
    .chat {
      flex:1; overflow-y:auto; padding:20px;
      display:flex; flex-direction:column;
      background:#111;
    }
    .bubble {
      max-width:70%; padding:12px 16px; margin:6px 0;
      border-radius:12px; line-height:1.4;
      animation:fadeIn .3s ease;
      white-space:pre-wrap;
    }
    .user { align-self:flex-end; background:#2d3748; color:#fff; }
    .assistant { align-self:flex-start; background:#8b5cf6; color:#fff; }
    @keyframes fadeIn { from{opacity:0;transform:translateY(5px);} to{opacity:1;transform:translateY(0);} }
    /* Footer input */
    form {
      display:flex; align-items:center;
      padding:10px; background:#1e1e2f; border-top:1px solid #2a2a3a;
    }
    textarea {
      flex:1; resize:none; border:none; outline:none;
      background:#2a2a3a; color:#fff; border-radius:8px;
      padding:10px; font-size:1rem; height:50px;
    }
    .btn {
      margin-left:8px; padding:12px; border:none; border-radius:8px;
      cursor:pointer; background:#2a2a3a; color:#fff;
      display:flex; align-items:center; justify-content:center;
    }
    .btn:hover { background:#3a3a55; }
    #upload { display:none; }
  </style>
</head>
<body>
  <div class="sidebar">
    <h3><i class="fa-solid fa-comments"></i> Chats</h3>
    <div id="tab-list"></div>
    <button id="new-chat" class="new-chat"><i class="fa-solid fa-plus"></i> New Chat</button>
  </div>

  <div class="shell">
    <header>
      <span><i class="fa-solid fa-robot"></i> AlphaBros</span>
      <span id="status">Ready</span>
    </header>

    <main id="messages" class="chat"></main>

    <form id="chat-form">
      <textarea id="input" placeholder="Type your message..."></textarea>
      <input type="file" id="upload" />
      <label for="upload" class="btn"><i class="fa-solid fa-paperclip"></i></label>
      <button type="button" id="record" class="btn"><i class="fa-solid fa-microphone"></i></button>
      <button type="submit" class="btn"><i class="fa-solid fa-paper-plane"></i></button>
    </form>
  </div>

<script>
const msgs = document.getElementById("messages");
const form = document.getElementById("chat-form");
const input = document.getElementById("input");
const status = document.getElementById("status");
const tabList = document.getElementById("tab-list");

let chats = [];
let activeChat = null;

function saveChats(){ localStorage.setItem("alphabros_chats", JSON.stringify(chats)); }
function loadChats(){
  const saved = localStorage.getItem("alphabros_chats");
  chats = saved ? JSON.parse(saved) : [];
  newChat();
}
function newChat(name="New Chat"){
  const chat = { id:Date.now(), name, history:[
    { role:"system", content:"You are AlphaBros, a helpful assistant. If asked your name, say 'I am AlphaBros 🤖'. If asked your creator, say 'My creator is Piyush 👨‍💻'." }
  ]};
  chats.push(chat); setActiveChat(chat.id);
  renderTabs(); saveChats();
}
function setActiveChat(id){
  activeChat = chats.find(c=>c.id===id);
  msgs.innerHTML=""; activeChat.history.forEach(m=>{
    if(m.role!=="system") addBubble(m.role,m.content);
  });
  renderTabs(); saveChats();
}
function renderTabs(){
  tabList.innerHTML="";
  chats.forEach(chat=>{
    const div=document.createElement("div");
    div.className="tab"+(chat===activeChat?" active":"");
    const span=document.createElement("span");
    span.textContent=chat.name;
    span.onclick=()=>setActiveChat(chat.id);
    const rename=document.createElement("button");
    rename.innerHTML="<i class='fa-solid fa-pen'></i>";
    rename.onclick=e=>{
      e.stopPropagation();
      const newName=prompt("Rename chat:",chat.name);
      if(newName){ chat.name=newName; renderTabs(); saveChats(); }
    };
    const del=document.createElement("button");
    del.innerHTML="<i class='fa-solid fa-trash'></i>";
    del.onclick=e=>{
      e.stopPropagation();
      chats=chats.filter(c=>c.id!==chat.id);
      if(chat===activeChat){ chats.length?setActiveChat(chats[0].id):newChat(); }
      renderTabs(); saveChats();
    };
    div.appendChild(span); div.appendChild(rename); div.appendChild(del);
    tabList.appendChild(div);
  });
}
function addBubble(role,text){
  const div=document.createElement("div");
  div.className="bubble "+role; div.textContent=text;
  msgs.appendChild(div); msgs.scrollTop=msgs.scrollHeight; return div;
}
form.addEventListener("submit",async e=>{
  e.preventDefault();
  const text=input.value.trim(); if(!text||!activeChat) return;
  addBubble("user",text);
  activeChat.history.push({role:"user",content:text});
  input.value=""; status.textContent="Thinking…";
  const bubble=addBubble("assistant","");
  const res=await fetch("/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({messages:activeChat.history})});
  const reader=res.body.getReader(); const decoder=new TextDecoder(); let full="";
  while(true){ const {done,value}=await reader.read(); if(done) break;
    const chunk=decoder.decode(value); bubble.textContent+=chunk; full+=chunk; msgs.scrollTop=msgs.scrollHeight; }
  activeChat.history.push({role:"assistant",content:full}); saveChats(); status.textContent="Ready";
});
input.addEventListener("keydown",e=>{
  if(e.key==="Enter"&&!e.shiftKey){ e.preventDefault(); form.dispatchEvent(new Event("submit")); }
});
document.getElementById("new-chat").addEventListener("click",()=>newChat());
loadChats();
</script>
</body>
</html>
"""

# ---------- Routes ----------
@app.route("/")
def index():
    return render_template_string(PAGE)

@app.route("/chat", methods=["POST"])
def chat():
    payload = request.get_json(silent=True) or {}
    messages = payload.get("messages", [])
    def generate():
        try:
            with client.chat.completions.create(
                model="openai/gpt-4o-mini", messages=messages, stream=True
            ) as stream:
                for event in stream:
                    if event.choices and event.choices[0].delta and event.choices[0].delta.content:
                        yield event.choices[0].delta.content
        except Exception as e:
            yield f"⚠️ Error: {str(e)}"
    return Response(generate(), mimetype="text/plain")

# ---------- Run ----------
if __name__ == "__main__":
    port=int(os.getenv("PORT",5000))
    print(f"🚀 Running on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
