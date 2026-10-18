# ============================================================
#                 🤖 MUBE AI  –  Full Strong Version
#         Telegram + Multi-AI + Image + Voice + Owner System
#         Clean, Professional, Feature-rich
# ============================================================
# Author idea: MUBE + Grok improvements
# ============================================================

import json
import os
import time
import urllib.request
import urllib.error
import urllib.parse
from collections import defaultdict
from datetime import datetime

# ============================================================
# 1. CONFIGURATION  (Render Environment Variables-ን ይጠቀማል)
# ============================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN", "Enter your bot token")

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "Enter your api key")          # Whisper + optional GPT
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "Enter Your Gemni api key")

# Models
OPENROUTER_MODELS = [
    "openrouter/free",
    "deepseek/deepseek-r1:free",
    "nvidia/nemotron-3.5-lightning:free",
]
GEMINI_MODELS = ["gemini-3.8-flash", "gemini-3.5-flash"]
OPENAI_MODEL = "gpt-4o-mini"
MISTRAL_MODEL = "mistral-small-latest"

# Owner
OWNER_ID = 8408469048
OWNER_USERNAME = "@MUBE_E_R"

# Channel & Group
CHANNEL_USERNAME = "@ETHIO_NET_MASTER"
CHANNEL_ID = -1003937708981
GROUP_USERNAME = "@ETHIO_NET_MASTER_G_p"
GROUP_ID = -1003577790019

# Limits & Settings
MAX_MEMORY = 16
MEMORY_FILE = "mube_memory.json"
FEATURES_FILE = "mube_features.json"
RATE_LIMIT_SECONDS = 2.5
MAX_IMAGE_PER_USER_DAY = 15          # free limit
MAX_VOICE_PER_USER_DAY = 20

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
OPENROUTER_API = "https://openrouter.ai/api/v1/chat/completions"
OPENAI_API = "https://api.openai.com/v1/chat/completions"
MISTRAL_API = "https://api.mistral.ai/v1/chat/completions"
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models/"

# ============================================================
# 2. GLOBAL STATE
# ============================================================

user_memory = {}
users = {}
last_message_time = defaultdict(float)
daily_usage = defaultdict(lambda: {"image": 0, "voice": 0, "date": ""})

bot_settings = {
    "ai_enabled": True,
    "maintenance_mode": False,
    "group_ai_enabled": True,
    "private_ai_enabled": True,
    "image_enabled": True,
    "voice_enabled": True,
}

features = {
    "modes": {},
    "last": {},
    "saved": {},
    "projects": {},
    "feedback": [],
    "referrals": {},
    "verified_members": [],
}

MODE_PROMPTS = {
    "smart": "Answer clearly, accurately and naturally in the user's language. Be helpful and concise.",
    "coding": "You are in CODING mode. Give clean, runnable code with short clear explanations. Prefer Python when possible.",
    "study": "You are in STUDY mode. Teach step-by-step with simple language, examples and a short practice question when useful.",
    "translate": "You are in TRANSLATOR mode. Translate accurately and keep the original tone. Do not add extra explanation unless asked.",
    "writing": "You are in WRITING mode. Help draft, edit, structure and improve writing.",
    "creative": "You are in CREATIVE mode. Be imaginative, original and fun.",
}

MODE_LABELS = {
    "smart": "✧🧠 Smart AI",
    "coding": "⌘💻 Coding",
    "study": "📚 Study",
    "translate": "🌐 Translator",
    "writing": "✍️ Writing",
    "creative": "🎨 Creative",
}

# ============================================================
# 3. TELEGRAM HELPERS
# ============================================================

def telegram_api(method, data=None, timeout=60):
    url = f"{TELEGRAM_API}/{method}"
    if data is None:
        data = {}
    encoded = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=encoded, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"❌ Telegram Error ({method}):", e)
        return None


def send_message(chat_id, text, reply_markup=None, parse_mode=None):
    if not text:
        text = "⚠️ ምንም መልስ አልተገኘም።"
    max_len = 3900
    for i in range(0, len(text), max_len):
        part = text[i:i + max_len]
        payload = {
            "chat_id": str(chat_id),
            "text": part,
            "disable_web_page_preview": "true",
        }
        if reply_markup and i + max_len >= len(text):
            payload["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
        if parse_mode:
            payload["parse_mode"] = parse_mode
        telegram_api("sendMessage", payload)
        time.sleep(0.2)


def edit_message(chat_id, message_id, text):
    telegram_api("editMessageText", {
        "chat_id": str(chat_id),
        "message_id": message_id,
        "text": text,
        "disable_web_page_preview": "true",
    })


def send_typing(chat_id):
    telegram_api("sendChatAction", {"chat_id": str(chat_id), "action": "typing"})


def send_photo(chat_id, photo_url, caption=""):
    telegram_api("sendPhoto", {
        "chat_id": str(chat_id),
        "photo": photo_url,
        "caption": (caption or "")[:1024],
    })


def send_animated_thinking(chat_id):
    send_typing(chat_id)
    result = telegram_api("sendMessage", {
        "chat_id": str(chat_id),
        "text": "⏳ እያሰብኩ",
    })
    if not result or not result.get("ok"):
        return None
    msg_id = result["result"]["message_id"]
    frames = ["⏳ እያሰብኩ.", "⏳ እያሰብኩ..", "⏳ እያሰብኩ...", "🧠 እያሰብኩ...", "✨ እያሰብኩ..."]
    for frame in frames:
        time.sleep(0.35)
        edit_message(chat_id, msg_id, frame)
        send_typing(chat_id)
    return msg_id


def delete_message(chat_id, message_id):
    if message_id:
        telegram_api("deleteMessage", {
            "chat_id": str(chat_id),
            "message_id": message_id,
        })


# ============================================================
# 4. MEMORY & FEATURES
# ============================================================

def load_memory():
    global user_memory, users
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        user_memory = {int(k): v for k, v in data.get("user_memory", {}).items()}
        users = {int(k): v for k, v in data.get("users", {}).items()}
        print("✅ Memory loaded")
    except Exception:
        print("ℹ️ No previous memory")


def save_memory():
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "user_memory": user_memory,
                "users": users,
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("⚠️ Memory save error:", e)


def load_features():
    global features
    try:
        with open(FEATURES_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        for k in features:
            if k in loaded:
                features[k] = loaded[k]
        print("✅ Features loaded")
    except Exception:
        pass


def save_features():
    try:
        with open(FEATURES_FILE, "w", encoding="utf-8") as f:
            json.dump(features, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("⚠️ Features save error:", e)


def check_daily_limit(user_id, kind):
    """kind = 'image' or 'voice'"""
    today = datetime.now().strftime("%Y-%m-%d")
    rec = daily_usage[user_id]
    if rec["date"] != today:
        rec["date"] = today
        rec["image"] = 0
        rec["voice"] = 0
    limit = MAX_IMAGE_PER_USER_DAY if kind == "image" else MAX_VOICE_PER_USER_DAY
    if rec[kind] >= limit and user_id != OWNER_ID:
        return False
    rec[kind] += 1
    return True


# ============================================================
# 5. AI PROVIDERS
# ============================================================

def call_openai_compatible(api_url, api_key, model, messages, name):
    if not api_key:
        return None
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.55,
        "max_tokens": 1800,
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    if "openrouter" in api_url:
        headers["HTTP-Referer"] = "https://t.me/ETHIO_NET_MASTER"
        headers["X-Title"] = "MUBE AI"
    req = urllib.request.Request(api_url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        content = result["choices"][0]["message"]["content"]
        if content:
            print(f"✅ AI → {name} | {model}")
            return content.strip()
    except Exception as e:
        print(f"⚠️ {name} failed:", e)
    return None


def call_gemini(model, messages):
    if not GEMINI_API_KEY:
        return None
    system = ""
    contents = []
    for m in messages:
        if m["role"] == "system":
            system += m["content"] + "\n"
        else:
            role = "model" if m["role"] == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})
    if not contents:
        return None
    payload = {
        "contents": contents,
        "generationConfig": {"temperature": 0.55, "maxOutputTokens": 1800},
    }
    if system.strip():
        payload["systemInstruction"] = {"parts": [{"text": system.strip()}]}
    url = f"{GEMINI_API_BASE}{urllib.parse.quote(model)}:generateContent?key={GEMINI_API_KEY}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=75) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        parts = result["candidates"][0]["content"]["parts"]
        answer = "".join(p.get("text", "") for p in parts).strip()
        if answer:
            print(f"✅ AI → Gemini | {model}")
            return answer
    except Exception as e:
        print(f"⚠️ Gemini {model} failed:", e)
    return None


def ask_ai(user_id, text, chat_type="private"):
    if not bot_settings["ai_enabled"]:
        return "🔴 AI በአሁኑ ጊዜ ተዘግቷል።"
    if chat_type in ("group", "supergroup") and not bot_settings["group_ai_enabled"]:
        return "👥 Group AI ተዘግቷል።"
    if chat_type == "private" and not bot_settings["private_ai_enabled"]:
        return "💬 Private AI ተዘግቷል።"

    if user_id not in user_memory:
        user_memory[user_id] = []

    is_owner = user_id == OWNER_ID
    mode = features["modes"].get(str(user_id), "smart")

    system = """You are MUBE AI – a helpful, natural and intelligent Telegram assistant.
Respond in the user's language (Amharic or English).
Be clear, concise and useful. Use short paragraphs and bullets when helpful.
Never reveal API keys, tokens or private configuration.
"""
    if is_owner:
        system += f"""
You are talking to the verified owner: ሙቤ / Mubarek (@MUBE_E_R, ID {OWNER_ID}).
Be especially helpful with coding, bot development and project ideas.
"""
    system += "\n" + MODE_PROMPTS.get(mode, MODE_PROMPTS["smart"])

    messages = [{"role": "system", "content": system}]
    messages.extend(user_memory[user_id][-MAX_MEMORY:])
    messages.append({"role": "user", "content": text})

    answer = None
    for model in GEMINI_MODELS:
        answer = call_gemini(model, messages)
        if answer:
            break
    if not answer and OPENROUTER_API_KEY:
        for model in OPENROUTER_MODELS:
            answer = call_openai_compatible(OPENROUTER_API, OPENROUTER_API_KEY, model, messages, "OpenRouter")
            if answer:
                break
    if not answer and OPENAI_API_KEY:
        answer = call_openai_compatible(OPENAI_API, OPENAI_API_KEY, OPENAI_MODEL, messages, "OpenAI")
    if not answer and MISTRAL_API_KEY:
        answer = call_openai_compatible(MISTRAL_API, MISTRAL_API_KEY, MISTRAL_MODEL, messages, "Mistral")

    if not answer:
        return "⚠️ AI service ላይ ጊዜያዊ ችግር አለ። ትንሽ ቆይተህ እንደገና ሞክር።"

    user_memory[user_id].append({"role": "user", "content": text})
    user_memory[user_id].append({"role": "assistant", "content": answer})
    if len(user_memory[user_id]) > MAX_MEMORY:
        user_memory[user_id] = user_memory[user_id][-MAX_MEMORY:]
    save_memory()

    features["last"][str(user_id)] = {
        "question": text[:8000],
        "answer": answer[:16000],
        "chat_type": chat_type,
        "time": int(time.time()),
    }
    save_features()
    return answer


# ============================================================
# 6. IMAGE GENERATION (Pollinations - free)
# ============================================================

def generate_image(prompt: str) -> str | None:
    try:
        clean = urllib.parse.quote(prompt.strip()[:400])
        url = f"https://image.pollinations.ai/prompt/{clean}?width=1024&height=1024&nologo=true&enhance=true"
        return url
    except Exception as e:
        print("Image generation error:", e)
        return None


# ============================================================
# 7. VOICE (Speech-to-Text with Whisper)
# ============================================================

def download_telegram_file(file_id: str) -> bytes | None:
    info = telegram_api("getFile", {"file_id": file_id})
    if not info or not info.get("ok"):
        return None
    path = info["result"]["file_path"]
    url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{path}"
    try:
        with urllib.request.urlopen(url, timeout=40) as resp:
            return resp.read()
    except Exception as e:
        print("Download error:", e)
        return None


def transcribe_voice(file_bytes: bytes) -> str | None:
    if not OPENAI_API_KEY:
        return None
    boundary = "----MubeBoundary7MA4YWxk"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="voice.ogg"\r\n'
        f"Content-Type: audio/ogg\r\n\r\n"
    ).encode() + file_bytes + f"\r\n--{boundary}\r\n".encode()
    body += (
        f'Content-Disposition: form-data; name="model"\r\n\r\n'
        f"whisper-1\r\n"
        f"--{boundary}--"
    ).encode()

    req = urllib.request.Request(
        "https://api.openai.com/v1/audio/transcriptions",
        data=body,
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=70) as resp:
            result = json.loads(resp.read().decode())
            return result.get("text", "").strip()
    except Exception as e:
        print("Whisper error:", e)
        return None


# ============================================================
# 8. MEMBERSHIP + UI
# ============================================================

def is_verified(user_id):
    return str(user_id) in [str(x) for x in features.get("verified_members", [])]


def send_join_gate(chat_id):
    keyboard = {
        "inline_keyboard": [
            [{"text": "📢 Join Channel", "url": f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"}],
            [{"text": "👥 Join Group", "url": f"https://t.me/{GROUP_USERNAME.lstrip('@')}"}],
            [{"text": "✅ I Joined — Verify", "callback_data": "mube:verify"}],
        ]
    }
    send_message(
        chat_id,
        "✧🤖 MUBE AI — Welcome!\n\n"
        "ቦቱን ለመጠቀም መጀመሪያ Channel እና Group ተቀላቀል።\n"
        "ከተቀላቀልክ በኋላ **Verify** ተጫን።",
        reply_markup=keyboard,
    )


def verify_membership(user_id):
    for cid in (CHANNEL_ID, GROUP_ID):
        res = telegram_api("getChatMember", {"chat_id": cid, "user_id": user_id})
        if not res or not res.get("ok"):
            return False, "አባልነት ማረጋገጥ አልተቻለም።"
        status = res["result"].get("status")
        if status not in ("creator", "administrator", "member") and not (
            status == "restricted" and res["result"].get("is_member")
        ):
            return False, "ገና Channel እና Group ሁለቱንም አልተቀላቀልክም።"
    if str(user_id) not in features["verified_members"]:
        features["verified_members"].append(str(user_id))
        features["verified_members"] = features["verified_members"][-10000:]
        save_features()
    return True, ""


def action_keyboard(user_id):
    uid = str(user_id)
    return {
        "inline_keyboard": [
            [
                {"text": "✧📋 Save", "callback_data": f"mube:save:{uid}"},
                {"text": "♻️ Regenerate", "callback_data": f"mube:regen:{uid}"},
            ],
            [
                {"text": "💖 Like", "callback_data": f"mube:like:{uid}"},
                {"text": "💔 Dislike", "callback_data": f"mube:dislike:{uid}"},
            ],
        ]
    }


def send_answer_with_actions(chat_id, user_id, answer):
    send_message(chat_id, f"✧🤖 MUBE AI\n\n{answer}", reply_markup=action_keyboard(user_id))


def send_home_menu(chat_id, first_name="Friend"):
    keyboard = {
        "inline_keyboard": [
            [{"text": "✧🤖 Ask MUBE AI", "callback_data": "mube:ask"}],
            [
                {"text": "✎ New Chat", "callback_data": "mube:new"},
                {"text": "🎛 AI Modes", "callback_data": "mube:modes"},
            ],
            [
                {"text": "🎨 Create Image", "callback_data": "mube:imagine"},
                {"text": "💎 Saved", "callback_data": "mube:saved"},
            ],
            [
                {"text": "👤 My Info", "callback_data": "mube:myinfo"},
                {"text": "⚙️ Help", "callback_data": "mube:help"},
            ],
        ]
    }
    send_message(
        chat_id,
        f"✨ MUBE AI\n\nሰላም {first_name}!\nምን ልረዳህ?\n\n"
        "• ጥያቄ በቀጥታ ጻፍ\n"
        "• ድምጽ ላክ (Voice)\n"
        "• /imagine ስዕል ፍጠር\n\n"
        "ከታች ያለውን ምረጥ ወይም በቀጥታ ጻፍ።",
        reply_markup=keyboard,
    )


# ============================================================
# 9. COMMANDS
# ============================================================

def is_owner(user_id):
    return user_id == OWNER_ID


def handle_command(chat_id, user, text):
    user_id = user.get("id")
    parts = text.strip().split(maxsplit=1)
    cmd = parts[0].lower().split("@")[0]
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd == "/start":
        send_home_menu(chat_id, user.get("first_name", "Friend"))
        return True

    if cmd == "/help":
        send_message(chat_id, """🤖 MUBE AI – Commands

/start – ዋና ምናሌ
/mode – AI ሁነታ
/newchat – አዲስ ውይይት
/clear – Memory አጽዳ
/imagine <prompt> – ስዕል ፍጠር
/save – የመጨረሻ መልስ አስቀምጥ
/saved – የተቀመጡ መልሶች
/id – የአንተ ID
/myinfo – የአንተ መረጃ

🎤 ድምጽ ልትልክ ትችላለህ (Voice message)
🎨 /imagine a beautiful landscape

Owner:
/panel  /stats  /broadcast
""")
        return True

    if cmd in ("/mode", "/modes"):
        rows = []
        items = list(MODE_LABELS.items())
        for i in range(0, len(items), 2):
            row = [{"text": MODE_LABELS[k], "callback_data": f"mube:mode:{k}"} for k, _ in items[i:i+2]]
            rows.append(row)
        send_message(chat_id, "🎛 የAI ሁነታ ምረጥ", reply_markup={"inline_keyboard": rows})
        return True

    if cmd == "/newchat":
        user_memory[user_id] = []
        save_memory()
        send_message(chat_id, "✎ አዲስ ውይይት ተጀምሯል።")
        return True

    if cmd == "/clear":
        user_memory.pop(user_id, None)
        save_memory()
        send_message(chat_id, "🧹 Memory ተጠርጓል።")
        return True

    if cmd == "/id":
        send_message(chat_id, f"🆔 Your Telegram ID:\n`{user_id}`")
        return True

    if cmd == "/myinfo":
        info = users.get(user_id, {})
        mode = MODE_LABELS.get(features["modes"].get(str(user_id), "smart"), "Smart")
        send_message(chat_id, f"""👤 My Information

Name: {info.get('first_name', user.get('first_name', 'Unknown'))}
Username: @{info.get('username') or 'None'}
ID: {user_id}
Messages: {info.get('messages', 0)}
Mode: {mode}
""")
        return True

    if cmd in ("/imagine", "/image"):
        if not bot_settings.get("image_enabled", True):
            send_message(chat_id, "🎨 Image generation አሁን ተዘግቷል።")
            return True
        if not check_daily_limit(user_id, "image"):
            send_message(chat_id, f"🎨 ዛሬ {MAX_IMAGE_PER_USER_DAY} ስዕል ገደብ ደርሰሃል።")
            return True
        prompt = arg or "a beautiful Ethiopian landscape"
        send_typing(chat_id)
        send_message(chat_id, "🎨 ስዕል እየፈጠርኩ...")
        url = generate_image(prompt)
        if url:
            send_photo(chat_id, url, caption=f"🎨 {prompt[:200]}")
        else:
            send_message(chat_id, "⚠️ ስዕል መፍጠር አልተቻለም።")
        return True

    if cmd == "/save":
        last = features["last"].get(str(user_id))
        if not last:
            send_message(chat_id, "📋 ለማስቀመጥ መልስ እስኪኖር ጠብቅ።")
        else:
            features["saved"].setdefault(str(user_id), []).append(last)
            features["saved"][str(user_id)] = features["saved"][str(user_id)][-40:]
            save_features()
            send_message(chat_id, "💎 መልሱ ተቀምጧል። /saved ብለህ አይተው።")
        return True

    if cmd == "/saved":
        saved = features["saved"].get(str(user_id), [])
        if not saved:
            send_message(chat_id, "💎 ገና የተቀመጠ መልስ የለም።")
        else:
            lines = ["💎 የተቀመጡ መልሶች"]
            for i, item in enumerate(saved[-8:], 1):
                q = item.get("question", "")[:90]
                lines.append(f"\n{i}. {q}")
            send_message(chat_id, "\n".join(lines))
        return True

    # Owner
    if cmd == "/panel" and is_owner(user_id):
        status = "🟢 ON" if bot_settings["ai_enabled"] else "🔴 OFF"
        maint = "🔴 ON" if bot_settings["maintenance_mode"] else "🟢 OFF"
        send_message(chat_id, f"""👑 MUBE AI OWNER PANEL

🧠 AI: {status}
🔧 Maintenance: {maint}
🎨 Image: {"🟢" if bot_settings.get("image_enabled") else "🔴"}
🎤 Voice: {"🟢" if bot_settings.get("voice_enabled") else "🔴"}

👥 Users: {len(users)}
🧠 Memory: {len(user_memory)}
✅ Verified: {len(features['verified_members'])}

/ai_on  /ai_off
/maintenance_on  /maintenance_off
/stats
/broadcast <message>
""")
        return True

    if cmd == "/ai_on" and is_owner(user_id):
        bot_settings["ai_enabled"] = True
        send_message(chat_id, "🧠 AI በርቷል 🟢")
        return True
    if cmd == "/ai_off" and is_owner(user_id):
        bot_settings["ai_enabled"] = False
        send_message(chat_id, "🧠 AI ጠፍቷል 🔴")
        return True
    if cmd == "/maintenance_on" and is_owner(user_id):
        bot_settings["maintenance_mode"] = True
        send_message(chat_id, "🔧 Maintenance Mode ON")
        return True
    if cmd == "/maintenance_off" and is_owner(user_id):
        bot_settings["maintenance_mode"] = False
        send_message(chat_id, "🔧 Maintenance Mode OFF")
        return True
    if cmd == "/stats" and is_owner(user_id):
        send_message(chat_id, f"""📊 Statistics

Users: {len(users)}
Memory: {len(user_memory)}
Verified: {len(features['verified_members'])}
Saved replies: {sum(len(v) for v in features['saved'].values())}
""")
        return True

    if cmd == "/broadcast" and is_owner(user_id):
        if not arg:
            send_message(chat_id, "Usage:\n/broadcast የመልእክትህ")
            return True
        count = 0
        for uid in list(users.keys()):
            try:
                send_message(uid, f"📢 From MUBE AI Owner:\n\n{arg}")
                count += 1
                time.sleep(0.04)
            except Exception:
                pass
        send_message(chat_id, f"✅ Broadcast ተልኳል → {count} users")
        return True

    return False


# ============================================================
# 10. CALLBACK HANDLER
# ============================================================

def handle_callback(callback):
    data = callback.get("data", "")
    msg = callback.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    user = callback.get("from", {})
    user_id = user.get("id")
    cb_id = callback.get("id")

    if cb_id:
        telegram_api("answerCallbackQuery", {"callback_query_id": cb_id})

    if not chat_id:
        return

    if data == "mube:verify":
        ok, reason = verify_membership(user_id)
        if ok:
            send_message(chat_id, "✅ አባልነትህ ተረጋግጧል! እንኳን ደህና መጣህ ✧")
            send_home_menu(chat_id, user.get("first_name", "Friend"))
        else:
            send_message(chat_id, "⚠️ " + reason)
            send_join_gate(chat_id)
        return

    if data == "mube:ask":
        send_message(chat_id, "✧🤖 ጥያቄህን በቀጥታ ጻፍ ወይም ድምጽ ላክ።")
        return
    if data == "mube:new":
        user_memory[user_id] = []
        save_memory()
        send_message(chat_id, "✎ አዲስ ውይይት ተጀምሯል።")
        return
    if data == "mube:modes":
        rows = []
        items = list(MODE_LABELS.items())
        for i in range(0, len(items), 2):
            row = [{"text": MODE_LABELS[k], "callback_data": f"mube:mode:{k}"} for k, _ in items[i:i+2]]
            rows.append(row)
        send_message(chat_id, "🎛 የAI ሁነታ ምረጥ", reply_markup={"inline_keyboard": rows})
        return
    if data == "mube:imagine":
        send_message(chat_id, "🎨 ስዕል ለመፍጠር እንዲህ ጻፍ፦\n\n/imagine a beautiful Ethiopian girl in traditional clothes")
        return
    if data == "mube:saved":
        handle_command(chat_id, user, "/saved")
        return
    if data == "mube:myinfo":
        handle_command(chat_id, user, "/myinfo")
        return
    if data == "mube:help":
        handle_command(chat_id, user, "/help")
        return

    if data.startswith("mube:mode:"):
        mode = data.split(":")[-1]
        if mode in MODE_PROMPTS:
            features["modes"][str(user_id)] = mode
            save_features()
            send_message(chat_id, f"✧ ሁነታህ ወደ {MODE_LABELS[mode]} ተቀይሯል።")
        return

    if data.startswith("mube:"):
        parts = data.split(":")
        if len(parts) < 3:
            return
        action, target = parts[1], parts[2]
        if target != str(user_id):
            return
        last = features["last"].get(str(user_id))
        if not last:
            send_message(chat_id, "⚠️ የቀድሞ መልስ አልተገኘም።")
            return

        if action == "save":
            features["saved"].setdefault(str(user_id), []).append(last)
            features["saved"][str(user_id]] = features["saved"][str(user_id)][-40:]
            save_features()
            send_message(chat_id, "💎 ተቀምጧል")
        elif action in ("like", "dislike"):
            features["feedback"].append({
                "user_id": user_id,
                "action": action,
                "question": last.get("question", "")[:400],
                "time": int(time.time()),
            })
            features["feedback"] = features["feedback"][-2000:]
            save_features()
            send_message(chat_id, "💖 አመሰግናለሁ" if action == "like" else "💔 አመሰግናለሁ")
            if OWNER_ID:
                send_message(OWNER_ID, f"Feedback: {action}\nUser: {user_id}\nQ: {last.get('question','')[:200]}")
        elif action == "regen":
            thinking_id = send_animated_thinking(chat_id)
            answer = ask_ai(user_id, last["question"], last.get("chat_type", "private"))
            delete_message(chat_id, thinking_id)
            send_answer_with_actions(chat_id, user_id, answer)


# ============================================================
# 11. MAIN MESSAGE HANDLER
# ============================================================

def handle_message(message):
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    chat_type = chat.get("type", "private")
    user = message.get("from", {})
    user_id = user.get("id")
    text = message.get("text", "").strip()

    if not user_id:
        return

    # Register user
    users[user_id] = {
        "id": user_id,
        "username": user.get("username", ""),
        "first_name": user.get("first_name", ""),
        "messages": users.get(user_id, {}).get("messages", 0) + 1,
    }

    # Anti-spam
    now = time.time()
    if now - last_message_time[user_id] < RATE_LIMIT_SECONDS and not is_owner(user_id):
        send_message(chat_id, "⏳ ትንሽ ቆይተህ እንደገና ሞክር።")
        return
    last_message_time[user_id] = now

    # Membership gate
    if not is_owner(user_id) and not is_verified(user_id):
        send_join_gate(chat_id)
        return

    # ========== VOICE MESSAGE ==========
    if "voice" in message and bot_settings.get("voice_enabled", True):
        if not check_daily_limit(user_id, "voice"):
            send_message(chat_id, f"🎤 ዛሬ {MAX_VOICE_PER_USER_DAY} ድምጽ ገደብ ደርሰሃል።")
            return

        send_typing(chat_id)
        file_id = message["voice"]["file_id"]
        file_bytes = download_telegram_file(file_id)
        if not file_bytes:
            send_message(chat_id, "⚠️ ድምጹን ማውረድ አልተቻለም።")
            return

        transcript = transcribe_voice(file_bytes)
        if not transcript:
            send_message(chat_id, "⚠️ ድምጹን መስማት አልተቻለም።\n(OpenAI API Key ያስፈልጋል)")
            return

        send_message(chat_id, f"🎤 ሰምቻለሁ፦\n\n{transcript}")

        thinking_id = send_animated_thinking(chat_id)
        answer = ask_ai(user_id, transcript, chat_type)
        delete_message(chat_id, thinking_id)
        send_answer_with_actions(chat_id, user_id, answer)
        return

    if not text:
        return

    # Commands
    if text.startswith("/"):
        if handle_command(chat_id, user, text):
            return

    # Quick image trigger
    lower = text.lower()
    if lower.startswith(("ስዕል", "ፎቶ ፍጠር", "image create", "draw")):
        prompt = text
        for p in ["ስዕል", "ፎቶ ፍጠር", "image create", "draw"]:
            if lower.startswith(p):
                prompt = text[len(p):].strip()
                break
        if prompt:
            handle_command(chat_id, user, f"/imagine {prompt}")
            return

    # Maintenance
    if bot_settings["maintenance_mode"] and not is_owner(user_id):
        send_message(chat_id, "🔧 MUBE AI በmaintenance ላይ ነው። ትንሽ ቆይተህ ሞክር።")
        return

    # Normal AI
    thinking_id = send_animated_thinking(chat_id)
    answer = ask_ai(user_id, text, chat_type)
    delete_message(chat_id, thinking_id)
    send_answer_with_actions(chat_id, user_id, answer)


# ============================================================
# 12. MAIN LOOP
# ============================================================

def main():
    print("=" * 60)
    print("🤖 MUBE AI – Full Strong Version Starting...")
    print("=" * 60)

    if not BOT_TOKEN or BOT_TOKEN.startswith("PASTE_"):
        print("❌ BOT_TOKEN አልገባም")
        return

    me = telegram_api("getMe")
    if not me or not me.get("ok"):
        print("❌ Telegram connection failed")
        return
    print(f"✅ Bot connected: @{me['result'].get('username')}")

    load_memory()
    load_features()

    print("🚀 MUBE AI is ONLINE")
    print("   • Multi-AI fallback")
    print("   • Image Generation (Pollinations)")
    print("   • Voice → Text (Whisper)")
    print("   • Owner Panel + Broadcast")
    print("   • Animated Thinking")
    print("   • Membership Gate")
    print("=" * 60)

    offset = None
    while True:
        try:
            data = {"timeout": 30}
            if offset:
                data["offset"] = offset
            updates = telegram_api("getUpdates", data)
            if not updates or not updates.get("ok"):
                time.sleep(3)
                continue

            for update in updates.get("result", []):
                offset = update["update_id"] + 1
                if "callback_query" in update:
                    handle_callback(update["callback_query"])
                elif "message" in update:
                    handle_message(update["message"])

        except KeyboardInterrupt:
            print("\n🛑 MUBE AI Stopped")
            break
        except Exception as e:
            print("⚠️ Loop error:", e)
            time.sleep(5)


if __name__ == "__main__":
    main()
