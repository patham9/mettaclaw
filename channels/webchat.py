import threading
from flask import Flask, request, jsonify, Response

_last_message = ""
_msg_lock = threading.Lock()
_bot_replies = []
_reply_lock = threading.Lock()

app = Flask(__name__)

HTML_PAGE = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Chat</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family: system-ui, sans-serif; background:#111; color:#eee; height:100vh; display:flex; flex-direction:column; }
  #messages { flex:1; overflow-y:auto; padding:16px; display:flex; flex-direction:column; gap:8px; }
  .msg { max-width:80%; padding:8px 12px; border-radius:8px; font-size:14px; }
  .user { align-self:flex-end; background:#4f46e5; }
  .bot { align-self:flex-start; background:#222; }
  #input { display:flex; padding:12px; background:#1a1a1a; gap:8px; }
  #input input { flex:1; padding:8px 12px; border-radius:6px; border:none; background:#333; color:#eee; }
  #input button { padding:8px 16px; border-radius:6px; border:none; background:#4f46e5; color:#fff; cursor:pointer; }
</style>
</head>
<body>
  <div id="messages"></div>
  <div id="input">
    <input id="txt" placeholder="Message..." autocomplete="off" />
    <button onclick="sendMsg()">Send</button>
  </div>
<script>
  const box = document.getElementById('messages');
  const txt = document.getElementById('txt');
  let seen = 0;

  txt.addEventListener('keydown', e => { if (e.key === 'Enter') sendMsg(); });

  function addMsg(text, cls) {
    const d = document.createElement('div');
    d.className = 'msg ' + cls;
    d.textContent = text;
    box.appendChild(d);
    box.scrollTop = box.scrollHeight;
  }

  function sendMsg() {
    const msg = txt.value.trim();
    if (!msg) return;
    txt.value = '';
    addMsg(msg, 'user');
    fetch('/api/send', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({msg: msg})
    });
  }

  function poll() {
    fetch('/api/recv?since=' + seen)
      .then(r => r.json())
      .then(data => {
        data.messages.forEach(m => addMsg(m.text, 'bot'));
        if (data.messages.length) seen = data.cursor;
      })
      .catch(() => {});
    setTimeout(poll, 1000);
  }
  poll();
</script>
</body>
</html>"""


def _set_last(msg):
    global _last_message
    with _msg_lock:
        if _last_message == "":
            _last_message = msg
        else:
            _last_message = _last_message + " | " + msg


def getLastMessage():
    global _last_message
    with _msg_lock:
        tmp = _last_message
        _last_message = ""
        return tmp


def send_message(text):
    text = str(text).replace("\\n", "\n")
    with _reply_lock:
        _bot_replies.append(text)


@app.route("/")
def index():
    return Response(HTML_PAGE, content_type="text/html")


@app.route("/api/send", methods=["POST"])
def api_send():
    data = request.get_json(force=True)
    msg = data.get("msg", "").strip()
    if msg:
        _set_last(f"user: {msg}")
    return jsonify(ok=True)


@app.route("/api/recv")
def api_recv():
    since = int(request.args.get("since", 0))
    with _reply_lock:
        new = _bot_replies[since:]
        cursor = len(_bot_replies)
    return jsonify(messages=[{"text": m} for m in new], cursor=cursor)


def start_webchat(port=5001):
    import logging
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)
    t = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=int(port), use_reloader=False),
        daemon=True,
    )
    t.start()
    print(f"[webchat] http://localhost:{port}")
    return t


def stop_webchat():
    pass