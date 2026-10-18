# ============================================================
#                 🤖 MUBE AI — Render Ready
#         Telegram + Multi-AI + Image + Voice + Owner System
# ============================================================
# Preserves the original feature set while fixing syntax,
# membership checks, polling, persistence, and configuration.
# ============================================================

import json
import os
import time
import urllib.request
import urllib.error
import urllib.parse
import mimetypes
from collections import defaultdict
from datetime import datetime, timezone

# ============================================================
# 1. CONFIGURATION
# ============================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

OPENROUTER_MODELS = [
    "openrouter/free",
    "deepseek/deepseek-r1:free",
    "nvidia/nemotron-3.5-lightning:free",
]
# Model names change over time; these can be overridden in Render.
GEMINI_MODELS = [
    item.strip() for item in os.environ.get(
        "GEMINI_MODELS", "gemini-2.5-flash"
    ).split(",") if item.strip()
]
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
MISTRAL_MODEL = os.environ.get("MISTRAL_MODEL", "mistral-small-latest")

OWNER_ID = 8408469048
OWNER_USERNAME = "@MUBE_E_R"

CHANNEL_USERNAME = "@ETHIO_NET_MASTER"
CHANNEL_ID = -1003937708981
GROUP_USERNAME = "@ETHIO_NET_MASTER_G_p"
GROUP_ID = -1003577790019

MAX_MEMORY = 16
RATE_LIMIT_SECONDS = 2.5
MAX_IMAGE_PER_USER_DAY = 15
MAX_VOICE_PER_USER_DAY = 20
MAX_TELEGRAM_TEXT = 3900
HTTP_TIMEOUT = 75

# Render persistent disks are available only on supported paid services.
# Set DATA_DIR to the mounted disk path in Render, if configured.
DATA_DIR = os.environ.get("DATA_DIR", ".").strip() or "."
os.makedirs(DATA_DIR, exist_ok=True)
MEMORY_FILE = os.path.join(DATA_DIR, "mube_memory.json")
FEATURES_FILE = os.path.join(DATA_DIR, "mube_features.json")

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

def telegram_api(method, data=None, timeout=HTTP_TIMEOUT):
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN is missing.")
        return None
    url = f"{TELEGRAM_API}/{method}"
    payload = data or {}
    encoded = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(url, data=encoded, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        if not result.get("ok"):
            print(f"⚠️ Telegram API {method}: {result.get('description', 'Unknown error')}")
        return result
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except Exception:
            detail = str(exc)
        print(f"❌ Telegram HTTP error ({method}): {detail[:500]}")
    except Exception as exc:
        print(f"❌ Telegram error ({method}): {exc}")
    return None


def send_message(chat_id, text, reply_markup=None, parse_mode=None):
    text = str(text or "⚠️ ምንም መልስ አልተገኘም።")
    chunks = [text[i:i + MAX_TELEGRAM_TEXT] for i in range(0, len(text), MAX_TELEGRAM_TEXT)]
    last_result = None
    for index, part in enumerate(chunks):
        payload = {
            "chat_id": str(chat_id),
            "text": part,
            "disable_web_page_preview": "true",
        }
        if reply_markup and index == len(chunks) - 1:
            payload["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
        if parse_mode:
            payload["parse_mode"] = parse_mode
        last_result = telegram_api("sendMessage", payload)
        time.sleep(0.12)
    return last_result


def edit_message(chat_id, message_id, text):
    return telegram_api("editMessageText", {
        "chat_id": str(chat_id),
        "message_id": message_id,
        "text": str(text)[:MAX_TELEGRAM_TEXT],
        "disable_web_page_preview": "true",
    })


def send_typing(chat_id):
    return telegram_api("sendChatAction", {"chat_id": str(chat_id), "action": "typing"})


def send_photo(chat_id, photo_url, caption=""):
    return telegram_api("sendPhoto", {
        "chat_id": str(chat_id),
        "photo": photo_url,
        "caption": (caption or "")[:1024],
    })


def send_animated_thinking(chat_id):
    send_typing(chat_id)
    result = telegram_api("sendMessage", {"chat_id": str(chat_id), "text": "⏳ እያሰብኩ..."})
    if not result or not result.get("ok"):
        return None
    msg_id = result["result"]["message_id"]
    frames = ["⏳ እያሰብኩ.", "⏳ እያሰብኩ..", "🧠 እያሰብኩ...", "✨ መልስ እያዘጋጀሁ..."]
    for frame in frames:
        time.sleep(0.25)
        edit_message(chat_id, msg_id, frame)
        send_typing(chat_id)
    return msg_id


def delete_message(chat_id, message_id):
    if message_id:
        return telegram_api("deleteMessage", {"chat_id": str(chat_id), "message_id": message_id})
    return None


def answer_callback(callback_id, text=None, show_alert=False):
    if not callback_id:
        return
    data = {"callback_query_id": callback_id, "show_alert": "true" if show_alert else "false"}
    if text:
        data["text"] = text[:200]
    telegram_api("answerCallbackQuery", data)


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
        print("✅ Memory loaded.")
    except FileNotFoundError:
        print("ℹ️ No previous memory; starting fresh.")
    except Exception as exc:
        print("⚠️ Memory load error:", exc)


def save_memory():
    try:
        tmp = MEMORY_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"user_memory": user_memory, "users": users}, f, ensure_ascii=False, indent=2)
        os.replace(tmp, MEMORY_FILE)
    except Exception as exc:
        print("⚠️ Memory save error:", exc)


def load_features():
    global features, bot_settings
    try:
        with open(FEATURES_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        for key in features:
            if key in loaded:
                features[key] = loaded[key]
        if isinstance(loaded.get("bot_settings"), dict):
            bot_settings.update(loaded["bot_settings"])
        print("✅ Features loaded.")
    except FileNotFoundError:
        pass
    except Exception as exc:
        print("⚠️ Features load error:", exc)


def save_features():
    try:
        tmp = FEATURES_FILE + ".tmp"
        payload = dict(features)
        payload["bot_settings"] = bot_settings
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, FEATURES_FILE)
    except Exception as exc:
        print("⚠️ Features save error:", exc)


def check_daily_limit(user_id, kind):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    record = daily_usage[user_id]
    if record["date"] != today:
        record.update({"date": today, "image": 0, "voice": 0})
    limit = MAX_IMAGE_PER_USER_DAY if kind == "image" else MAX_VOICE_PER_USER_DAY
    if record[kind] >= limit and user_id != OWNER_ID:
        return False
    record[kind] += 1
    return True


def is_owner(user_id):
    return user_id == OWNER_ID


def is_verified(user_id):
    return str(user_id) in {str(value) for value in features.get("verified_members", [])}


# ============================================================
# 5. AI PROVIDERS
# ============================================================

def call_openai_compatible(api_url, api_key, model, messages, name):
    if not api_key:
        return None
    payload = {"model": model, "messages": messages, "temperature": 0.55, "max_tokens": 1800}
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    if "openrouter" in api_url:
        headers["HTTP-Referer"] = "https://t.me/ETHIO_NET_MASTER"
        headers["X-Title"] = "MUBE AI"
    req = urllib.request.Request(
        api_url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        content = result["choices"][0]["message"]["content"]
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        if content:
            print(f"✅ AI → {name} | {model}")
            return str(content).strip()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"⚠️ {name} HTTP {exc.code}: {detail[:400]}")
    except Exception as exc:
        print(f"⚠️ {name} failed: {exc}")
    return None


def call_gemini(model, messages):
    if not GEMINI_API_KEY:
        return None
    system_parts = []
    contents = []
    for message in messages:
        if message.get("role") == "system":
            system_parts.append(message.get("content", ""))
        else:
            role = "model" if message.get("role") == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": message.get("content", "")}]})
    if not contents:
        return None
    payload = {
        "contents": contents,
        "generationConfig": {"temperature": 0.55, "maxOutputTokens": 1800},
    }
    if system_parts:
        payload["systemInstruction"] = {"parts": [{"text": "\n".join(system_parts)}]}
    url = f"{GEMINI_API_BASE}{urllib.parse.quote(model)}:generateContent?key={urllib.parse.quote(GEMINI_API_KEY)}"
    req = urllib.request.Request(
        url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        candidates = result.get("candidates", [])
        if not candidates:
            print(f"⚠️ Gemini {model}: no candidates returned.")
            return None
        parts = candidates[0].get("content", {}).get("parts", [])
        answer = "".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()
        if answer:
            print(f"✅ AI → Gemini | {model}")
            return answer
        print(f"⚠️ Gemini {model}: empty response.")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"⚠️ Gemini HTTP {exc.code} ({model}): {detail[:400]}")
    except Exception as exc:
        print(f"⚠️ Gemini {model} failed: {exc}")
    return None


def ask_ai(user_id, text, chat_type="private"):
    if not bot_settings["ai_enabled"]:
        return "🔴 AI በአሁኑ ጊዜ ተዘግቷል።"
    if chat_type in ("group", "supergroup") and not bot_settings["group_ai_enabled"]:
        return "👥 Group AI ተዘግቷል።"
    if chat_type == "private" and not bot_settings["private_ai_enabled"]:
        return "💬 Private AI ተዘግቷል።"

    user_memory.setdefault(user_id, [])
    mode = features["modes"].get(str(user_id), "smart")
    system = (
        "You are MUBE AI, a helpful Telegram assistant. Respond in the user's language, "
        "including Amharic or English. Be clear, accurate, concise, and useful. "
        "Never reveal API keys, tokens, or private configuration."
    )
    if is_owner(user_id):
        system += (
            f" You are speaking to the verified project owner ({OWNER_USERNAME}, ID {OWNER_ID}). "
            "Be especially helpful with coding, bot development, and project ideas."
        )
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
        return (
            "⚠️ AI service ላይ ጊዜያዊ ችግር አለ። API key፣ model ስም፣ quota እና Render logs ፈትሽ።"
        )

    user_memory[user_id].extend([
        {"role": "user", "content": text},
        {"role": "assistant", "content": answer},
    ])
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
# 6. IMAGE GENERATION
# ============================================================

def generate_image(prompt):
    try:
        clean = urllib.parse.quote((prompt or "").strip()[:400], safe="")
        return (
            "https://image.pollinations.ai/prompt/"
            f"{clean}?width=1024&height=1024&nologo=true&enhance=true"
        )
    except Exception as exc:
        print("Image generation error:", exc)
        return None


# ============================================================
# 7. VOICE — TELEGRAM FILE DOWNLOAD + OPENAI WHISPER
# ============================================================

def download_telegram_file(file_id):
    info = telegram_api("getFile", {"file_id": file_id})
    if not info or not info.get("ok"):
        return None
    path = info.get("result", {}).get("file_path")
    if not path:
        return None
    url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{path}"
    try:
        with urllib.request.urlopen(url, timeout=45) as resp:
            return resp.read()
    except Exception as exc:
        print("Download error:", exc)
        return None


def transcribe_voice(file_bytes):
    if not OPENAI_API_KEY:
        return None
    boundary = "----MubeBoundary7MA4YWxk"
    parts = [
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="file"; filename="voice.ogg"\r\n',
        b"Content-Type: audio/ogg\r\n\r\n",
        file_bytes,
        f"\r\n--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="model"\r\n\r\n',
        b"whisper-1\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    body = b"".join(parts)
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
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        return result.get("text", "").strip() or None
    except urllib.error.HTTPError as exc:
        print("Whisper HTTP error:", exc.code, exc.read().decode("utf-8", errors="replace")[:400])
    except Exception as exc:
        print("Whisper error:", exc)
    return None


# ============================================================
# 8. MEMBERSHIP + UI
# ============================================================

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
        "ከተቀላቀልክ በኋላ «Verify» ተጫን።",
        reply_markup=keyboard,
    )


def verify_membership(user_id):
    for chat_id in (CHANNEL_ID, GROUP_ID):
        result = telegram_api("getChatMember", {"chat_id": chat_id, "user_id": user_id})
        if not result or not result.get("ok"):
            return False, (
                "አባልነት ማረጋገጥ አልተቻለም። Bot-ን በChannel እና Group ውስጥ admin አድርግ፣ "
                "ከዚያ እንደገና ሞክር።"
            )
        member = result.get("result", {})
        status = member.get("status")
        if status not in ("creator", "administrator", "member") and not (
            status == "restricted" and member.get("is_member")
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
        "• /imagine <prompt> ስዕል ፍጠር\n\n"
        "ከታች ያለውን ምረጥ ወይም በቀጥታ ጻፍ።",
        reply_markup=keyboard,
    )


# ============================================================
# 9. COMMANDS
# ============================================================

def handle_command(chat_id, user, text):
    user_id = user.get("id")
    parts = text.strip().split(maxsplit=1)
    command = parts[0].lower().split("@")[0]
    arg = parts[1].strip() if len(parts) > 1 else ""

    if command == "/start":
        if not is_owner(user_id) and not is_verified(user_id):
            send_join_gate(chat_id)
        else:
            send_home_menu(chat_id, user.get("first_name", "Friend"))
        return True

    if command == "/help":
        send_message(chat_id, """🤖 MUBE AI — Commands

/start — ዋና ምናሌ
/help — እገዛ
/mode — AI ሁነታ
/newchat — አዲስ ውይይት
/clear — Memory አጽዳ
/imagine <prompt> — ስዕል ፍጠር
/save — የመጨረሻ መልስ አስቀምጥ
/saved — የተቀመጡ መልሶች
/id — Telegram ID
/myinfo — የአንተ መረጃ

🎤 Voice message ላክ።
🎨 /imagine a beautiful landscape

Owner:
/panel /stats /broadcast <message>
/ai_on /ai_off
/maintenance_on /maintenance_off
""")
        return True

    if command in ("/mode", "/modes"):
        items = list(MODE_LABELS.items())
        rows = []
        for i in range(0, len(items), 2):
            rows.append([
                {"text": MODE_LABELS[key], "callback_data": f"mube:mode:{key}"}
                for key, _ in items[i:i + 2]
            ])
        send_message(chat_id, "🎛 የAI ሁነታ ምረጥ", reply_markup={"inline_keyboard": rows})
        return True

    if command == "/newchat":
        user_memory[user_id] = []
        save_memory()
        send_message(chat_id, "✎ አዲስ ውይይት ተጀምሯል።")
        return True

    if command == "/clear":
        user_memory.pop(user_id, None)
        save_memory()
        send_message(chat_id, "🧹 Memory ተጠርጓል።")
        return True

    if command == "/id":
        send_message(chat_id, f"🆔 Your Telegram ID:\n{user_id}")
        return True

    if command == "/myinfo":
        info = users.get(user_id, {})
        mode = MODE_LABELS.get(features["modes"].get(str(user_id), "smart"), "Smart")
        send_message(chat_id, (
            "👤 My Information\n\n"
            f"Name: {info.get('first_name', user.get('first_name', 'Unknown'))}\n"
            f"Username: @{info.get('username') or 'None'}\n"
            f"ID: {user_id}\nMessages: {info.get('messages', 0)}\nMode: {mode}"
        ))
        return True

    if command in ("/imagine", "/image"):
        if not bot_settings.get("image_enabled", True):
            send_message(chat_id, "🎨 Image generation አሁን ተዘግቷል።")
            return True
        if not check_daily_limit(user_id, "image"):
            send_message(chat_id, f"🎨 ዛሬ {MAX_IMAGE_PER_USER_DAY} ስዕል ገደብ ደርሰሃል።")
            return True
        prompt = arg or "a beautiful Ethiopian landscape"
        send_typing(chat_id)
        send_message(chat_id, "🎨 ስዕል እየፈጠርኩ...")
        image_url = generate_image(prompt)
        if image_url:
            send_photo(chat_id, image_url, caption=f"🎨 {prompt[:200]}")
        else:
            send_message(chat_id, "⚠️ ስዕል መፍጠር አልተቻለም።")
        return True

    if command == "/save":
        last = features["last"].get(str(user_id))
        if not last:
            send_message(chat_id, "📋 ለማስቀመጥ መልስ እስኪኖር ጠብቅ።")
        else:
            saved = features["saved"].setdefault(str(user_id), [])
            saved.append(last)
            features["saved"][str(user_id)] = saved[-40:]
            save_features()
            send_message(chat_id, "💎 መልሱ ተቀምጧል። /saved ብለህ አይተው።")
        return True

    if command == "/saved":
        saved = features["saved"].get(str(user_id), [])
        if not saved:
            send_message(chat_id, "💎 ገና የተቀመጠ መልስ የለም።")
        else:
            lines = ["💎 የተቀመጡ መልሶች"]
            for index, item in enumerate(saved[-8:], 1):
                lines.append(f"\n{index}. {item.get('question', '')[:90]}")
                lines.append(f"   ↳ {item.get('answer', '')[:180]}")
            send_message(chat_id, "\n".join(lines))
        return True

    # Owner-only commands
    if command == "/panel":
        if not is_owner(user_id):
            send_message(chat_id, "⛔ Owner-only command.")
            return True
        status = "🟢 ON" if bot_settings["ai_enabled"] else "🔴 OFF"
        maintenance = "🔴 ON" if bot_settings["maintenance_mode"] else "🟢 OFF"
        send_message(chat_id, (
            "👑 MUBE AI OWNER PANEL\n\n"
            f"🧠 AI: {status}\n🔧 Maintenance: {maintenance}\n"
            f"🎨 Image: {'🟢' if bot_settings['image_enabled'] else '🔴'}\n"
            f"🎤 Voice: {'🟢' if bot_settings['voice_enabled'] else '🔴'}\n\n"
            f"👥 Users: {len(users)}\n🧠 Memory: {len(user_memory)}\n"
            f"✅ Verified: {len(features['verified_members'])}\n\n"
            "/ai_on /ai_off\n/maintenance_on /maintenance_off\n/stats\n/broadcast <message>"
        ))
        return True

    if command in ("/ai_on", "/ai_off", "/maintenance_on", "/maintenance_off", "/stats", "/broadcast"):
        if not is_owner(user_id):
            send_message(chat_id, "⛔ Owner-only command.")
            return True
        if command == "/ai_on":
            bot_settings["ai_enabled"] = True
            save_features()
            send_message(chat_id, "🧠 AI በርቷል 🟢")
        elif command == "/ai_off":
            bot_settings["ai_enabled"] = False
            save_features()
            send_message(chat_id, "🧠 AI ጠፍቷል 🔴")
        elif command == "/maintenance_on":
            bot_settings["maintenance_mode"] = True
            save_features()
            send_message(chat_id, "🔧 Maintenance Mode ON")
        elif command == "/maintenance_off":
            bot_settings["maintenance_mode"] = False
            save_features()
            send_message(chat_id, "🔧 Maintenance Mode OFF")
        elif command == "/stats":
            send_message(chat_id, (
                "📊 Statistics\n\n"
                f"Users: {len(users)}\nMemory: {len(user_memory)}\n"
                f"Verified: {len(features['verified_members'])}\n"
                f"Saved replies: {sum(len(value) for value in features['saved'].values())}"
            ))
        elif command == "/broadcast":
            if not arg:
                send_message(chat_id, "Usage:\n/broadcast Your message")
            else:
                count = 0
                for uid in list(users.keys()):
                    try:
                        result = send_message(uid, f"📢 From MUBE AI Owner:\n\n{arg}")
                        if result and result.get("ok"):
                            count += 1
                        time.sleep(0.05)
                    except Exception as exc:
                        print("Broadcast error:", exc)
                send_message(chat_id, f"✅ Broadcast sent to {count} users.")
        return True

    return False


# ============================================================
# 10. CALLBACK HANDLER
# ============================================================

def handle_callback(callback):
    data = callback.get("data", "")
    message = callback.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    user = callback.get("from", {})
    user_id = user.get("id")
    callback_id = callback.get("id")

    if data == "mube:verify":
        ok, reason = verify_membership(user_id)
        if ok:
            answer_callback(callback_id, "Membership verified!")
            if chat_id:
                send_message(chat_id, "✅ አባልነትህ ተረጋግጧል! እንኳን ደህና መጣህ ✧")
                send_home_menu(chat_id, user.get("first_name", "Friend"))
        else:
            answer_callback(callback_id, reason, show_alert=True)
            if chat_id:
                send_join_gate(chat_id)
        return

    answer_callback(callback_id)

    if not chat_id or not user_id:
        return

    # Enforce membership for callback actions, except owner and verify.
    if not is_owner(user_id) and not is_verified(user_id):
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
            rows.append([
                {"text": MODE_LABELS[key], "callback_data": f"mube:mode:{key}"}
                for key, _ in items[i:i + 2]
            ])
        send_message(chat_id, "🎛 የAI ሁነታ ምረጥ", reply_markup={"inline_keyboard": rows})
        return
    if data == "mube:imagine":
        send_message(chat_id, "🎨 ስዕል ለመፍጠር እንዲህ ጻፍ፦\n/imagine a beautiful Ethiopian landscape")
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
        action, target_id = parts[1], parts[2]
        if target_id != str(user_id):
            answer_callback(callback_id, "This button belongs to another user.", show_alert=True)
            return
        last = features["last"].get(str(user_id))
        if not last:
            send_message(chat_id, "⚠️ የቀድሞ መልስ አልተገኘም።")
            return
        if action == "save":
            saved = features["saved"].setdefault(str(user_id), [])
            saved.append(last)
            features["saved"][str(user_id)] = saved[-40:]
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
                send_message(OWNER_ID, f"Feedback: {action}\nUser: {user_id}\nQ: {last.get('question', '')[:200]}")
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
    text = (message.get("text") or "").strip()

    if not user_id or not chat_id:
        return

    users[user_id] = {
        "id": user_id,
        "username": user.get("username", ""),
        "first_name": user.get("first_name", ""),
        "messages": users.get(user_id, {}).get("messages", 0) + 1,
    }
    save_memory()

    now = time.time()
    if now - last_message_time[user_id] < RATE_LIMIT_SECONDS and not is_owner(user_id):
        send_message(chat_id, "⏳ ትንሽ ቆይተህ እንደገና ሞክር።")
        return
    last_message_time[user_id] = now

    if text.startswith("/"):
        if handle_command(chat_id, user, text):
            return

    # Owner is allowed through. Other users must verify membership.
    if not is_owner(user_id) and not is_verified(user_id):
        send_join_gate(chat_id)
        return

    if bot_settings["maintenance_mode"] and not is_owner(user_id):
        send_message(chat_id, "🔧 MUBE AI በmaintenance ላይ ነው። ትንሽ ቆይተህ ሞክር።")
        return

    # Voice message
    if "voice" in message and bot_settings.get("voice_enabled", True):
        if not check_daily_limit(user_id, "voice"):
            send_message(chat_id, f"🎤 ዛሬ {MAX_VOICE_PER_USER_DAY} ድምጽ ገደብ ደርሰሃል።")
            return
        send_typing(chat_id)
        voice_bytes = download_telegram_file(message["voice"].get("file_id", ""))
        if not voice_bytes:
            send_message(chat_id, "⚠️ ድምጹን ማውረድ አልተቻለም።")
            return
        transcript = transcribe_voice(voice_bytes)
        if not transcript:
            send_message(chat_id, "⚠️ ድምጹን መተርጎም አልተቻለም። OPENAI_API_KEY እና Whisper API ፈትሽ።")
            return
        send_message(chat_id, f"🎤 ሰምቻለሁ፦\n\n{transcript}")
        thinking_id = send_animated_thinking(chat_id)
        answer = ask_ai(user_id, transcript, chat_type)
        delete_message(chat_id, thinking_id)
        send_answer_with_actions(chat_id, user_id, answer)
        return

    if not text:
        return

    # Quick image trigger
    lower = text.lower()
    triggers = ("ስዕል", "ፎቶ ፍጠር", "image create", "draw ")
    for trigger in triggers:
        if lower.startswith(trigger):
            prompt = text[len(trigger):].strip()
            if prompt:
                handle_command(chat_id, user, f"/imagine {prompt}")
                return

    thinking_id = send_animated_thinking(chat_id)
    answer = ask_ai(user_id, text, chat_type)
    delete_message(chat_id, thinking_id)
    send_answer_with_actions(chat_id, user_id, answer)


# ============================================================
# 12. MAIN POLLING LOOP
# ============================================================

def main():
    print("=" * 60)
    print("🤖 MUBE AI — Render Ready")
    print("=" * 60)

    if not BOT_TOKEN or BOT_TOKEN.lower() in ("enter your bot token", "paste_your_bot_token"):
        print("❌ BOT_TOKEN missing. Add it in Render → Environment.")
        return

    me = telegram_api("getMe")
    if not me or not me.get("ok"):
        print("❌ Telegram connection failed. Check BOT_TOKEN and network.")
        return
    print(f"✅ Bot connected: @{me['result'].get('username', 'unknown')}")

    load_memory()
    load_features()

    print("🚀 MUBE AI is ONLINE")
    print("   • Multi-AI fallback")
    print("   • Image generation (Pollinations URL)")
    print("   • Voice-to-text (OpenAI Whisper)")
    print("   • Owner panel + broadcast")
    print("   • Animated thinking")
    print("   • Membership gate")
    print("   • AI modes, memory, saved answers, feedback")
    print("=" * 60)

    offset = None
    while True:
        try:
            # Telegram long polling. Only one running process should poll this bot.
            data = {"timeout": 30}
            if offset is not None:
                data["offset"] = offset
            updates = telegram_api("getUpdates", data, timeout=40)
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
            print("\n🛑 MUBE AI stopped.")
            break
        except Exception as exc:
            print("⚠️ Polling loop error:", exc)
            time.sleep(5)


if __name__ == "__main__":
    main()
