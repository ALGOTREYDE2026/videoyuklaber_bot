import html
import logging
import mimetypes
import os
import random
import re
import tempfile
import uuid
from pathlib import Path
from urllib.parse import urlparse

import requests
import telebot
import yt_dlp

# ================== SOZLAMALAR ==================
TOKEN = "7952291017:AAH2jiBdDjDRSSNIbQnAFggQJJmsHTeCAdA"
CHANNEL = "@Algo_Treyde"
# ================== LOG ==================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

bot = telebot.TeleBot(TOKEN, parse_mode="HTML", threaded=True)

URL_RE = re.compile(r"^https?://", re.IGNORECASE)

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
AUDIO_EXTS = {".mp3", ".m4a", ".aac", ".ogg", ".opus", ".wav", ".flac"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

START_TEXTS = [
    "Silka yubor 😎\nMen faylni sudrayman.\n\n👉 {channel} kanalga obuna bo‘l\nHayotingni o‘zgartir 🔥",
    "Silka tashla jigar 😈\nMen download qilaman.\n\n👉 {channel} kanalga obuna bo‘l\nYorqin kelajak kutyapti 🔥",
    "Men tayyorman 😎\nSilka yubor.\n\n👉 {channel} kanalga obuna bo‘l\nHayotingni o‘zgartir 🔥",
]

INVALID_URL_TEXTS = [
    "Silka yubor jigar 😄",
    "Bu link emas jigar 😂",
    "Menga silka kerak, gap emas 😎",
]

ERROR_TEXTS = [
    "Bir tinga qimmat video yuklanmadi 😂",
    "Link ishlamadi shekilli 😅",
    "Faylni olib bo‘lmadi 😔",
    "Bir joyda to‘siq chiqdi 😅",
]

PROCESSING_TEXTS = {
    "youtube": [
        "YouTube serveriga bostirib kirdim 😈🏹",
        "Google amaki bilan mushtlashyapman 😂",
        "Qo‘riqchilar ushlashidan oldin videongni olib chiqaman 🏃",
    ],
    "tiktok": [
        "TikTok miyani eritadigan videoni qidiryapman 🧠😂",
        "TikTok serverini talayapman 😈",
        "Trend videongni qopga solib olib chiqyapman 😎",
    ],
    "instagram": [
        "Instagram reels oviga chiqdim 😎",
        "Meta qo‘riqchilari sezmasin 😂",
        "Reelsni chamadonga joylayapman 😈🧳",
    ],
    "direct": [
        "Kut jigar... faylni sudrayapman 😈",
        "Video serveriga bostirib kirdim 😎",
        "Fayl qidiryapman... Google amaki bilan urishyapman 😂",
        "Hozir olib beraman, sabr qil 😈",
    ],
}

DONE_HEADERS = {
    "youtube": [
        "YouTube serveridan videongni olib chiqdim 😎🏹",
        "Google amaki yiqildi, video men tomonda 😈",
        "Qo‘riqchilar yetib kelguncha videongni olib chiqdim 😂",
    ],
    "tiktok": [
        "TikTokdan videongni qopga solib olib keldim 😎",
        "TikTok serveri charchab qoldi 😂",
        "Trend videong tayyor 😈",
    ],
    "instagram": [
        "Instagram reelsni chamadonga joylab keldim 😎",
        "Meta amaki gaplashmay qoldi 😂",
        "Reelsni olib chiqdim 😈",
    ],
    "direct": [
        "Mana ol 😎",
        "Olib keldim jigar 🔥",
        "Tayyor 😈",
        "Sudrab keldim 😎",
    ],
}


# ================== YORDAMCHI FUNKSIYALAR ==================
def is_url(text: str) -> bool:
    return bool(URL_RE.match((text or "").strip()))


def platform_from_url(url: str) -> str:
    host = urlparse(url).netloc.lower()

    if "youtube.com" in host or "youtu.be" in host:
        return "youtube"
    if "tiktok.com" in host:
        return "tiktok"
    if "instagram.com" in host:
        return "instagram"
    return "direct"


def ext_from_url(url: str) -> str:
    return os.path.splitext(urlparse(url).path)[1].lower()


def ext_from_content_type(content_type: str) -> str:
    if not content_type:
        return ""
    ctype = content_type.split(";")[0].strip().lower()
    ext = mimetypes.guess_extension(ctype) or ""
    if ext == ".jpe":
        ext = ".jpg"
    return ext


def resolve_ffmpeg_location(path: str) -> str:
    # Agar exe yo'li berilsa, papkaga aylantiramiz.
    if path.lower().endswith(".exe"):
        return os.path.dirname(path)
    return path


def random_start_text() -> str:
    return random.choice(START_TEXTS).format(channel=CHANNEL)


def random_invalid_text() -> str:
    return random.choice(INVALID_URL_TEXTS)


def random_error_text() -> str:
    return random.choice(ERROR_TEXTS)


def random_processing_text(platform: str) -> str:
    return random.choice(PROCESSING_TEXTS.get(platform, PROCESSING_TEXTS["direct"]))


def random_done_header(platform: str) -> str:
    return random.choice(DONE_HEADERS.get(platform, DONE_HEADERS["direct"]))


def promo_caption(title: str, platform: str) -> str:
    safe_title = html.escape(title or "Video")
    header = html.escape(random_done_header(platform))
    return (
        f"{header}\n\n"
        f"🎬 <b>{safe_title}</b>\n\n"
        f"👉 <b>{CHANNEL}</b> kanalga obuna bo‘l\n"
        f"Hayotingni o‘zgartir 🔥"
    )


# ================== DOWNLOAD ==================
def download_direct_file(url: str, workdir: str):
    r = requests.get(url, stream=True, timeout=60, headers=HEADERS)
    r.raise_for_status()

    content_type = r.headers.get("content-type", "").split(";")[0].lower().strip()
    ext = ext_from_url(url) or ext_from_content_type(content_type) or ".bin"

    path = os.path.join(workdir, f"file_{uuid.uuid4().hex}{ext}")

    with open(path, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)

    return path, content_type, ext


def download_ytdlp_media(url: str, workdir: str):
    outtmpl = os.path.join(
        workdir,
        "%(title).80s_%(id)s.%(ext)s"
    )

    ydl_opts = {
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "retries": 3,
        "fragment_retries": 3,
        "socket_timeout": 30,
        "windowsfilenames": True,
        "format": "best[ext=mp4]/best",
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get("title") or "Video"

    files = [
        p for p in Path(workdir).iterdir()
        if p.is_file() and not p.name.endswith(".part")
    ]

    if not files:
        raise FileNotFoundError("Downloaded file not found")

    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    final_path = str(files[0])
    ext = Path(final_path).suffix.lower()

    return final_path, title, ext


# ================== SEND ==================
def send_downloaded_file(chat_id: int, path: str, platform: str, title: str, content_type: str = ""):
    ext = Path(path).suffix.lower()

    with open(path, "rb") as f:
        if content_type.startswith("video/") or ext in VIDEO_EXTS:
            try:
                bot.send_video(chat_id, f, supports_streaming=True, caption=promo_caption(title, platform))
            except Exception:
                f.seek(0)
                bot.send_document(chat_id, f, caption=promo_caption(title, platform))

        elif content_type.startswith("audio/") or ext in AUDIO_EXTS:
            try:
                bot.send_audio(chat_id, f, caption=promo_caption(title, platform))
            except Exception:
                f.seek(0)
                bot.send_document(chat_id, f, caption=promo_caption(title, platform))

        elif content_type.startswith("image/") or ext in IMAGE_EXTS:
            try:
                bot.send_photo(chat_id, f, caption=promo_caption(title, platform))
            except Exception:
                f.seek(0)
                bot.send_document(chat_id, f, caption=promo_caption(title, platform))

        else:
            bot.send_document(chat_id, f, caption=promo_caption(title, platform))


# ================== HANDLERS ==================
@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id, random_start_text())


@bot.message_handler(content_types=["text"])
def handle_text(message):
    text = (message.text or "").strip()

    if not text or text.startswith("/"):
        return

    if not is_url(text):
        bot.reply_to(message, random_invalid_text())
        return

    platform = platform_from_url(text)
    status = bot.reply_to(message, random_processing_text(platform))

    with tempfile.TemporaryDirectory() as workdir:
        try:
            if platform in {"youtube", "tiktok", "instagram"}:
                path, title, ext = download_ytdlp_media(text, workdir)
                content_type = "video/" if ext in VIDEO_EXTS else ""
            else:
                path, content_type, ext = download_direct_file(text, workdir)
                title = Path(path).stem

            try:
                bot.delete_message(message.chat.id, status.message_id)
            except Exception:
                pass

            send_downloaded_file(message.chat.id, path, platform, title, content_type)

        except Exception as e:
            logging.exception(e)
            try:
                bot.edit_message_text(
                    random_error_text(),
                    chat_id=message.chat.id,
                    message_id=status.message_id
                )
            except Exception:
                bot.send_message(message.chat.id, random_error_text())


# ================== START ==================
if __name__ == "__main__":
    logging.info("Bot started")
    bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)