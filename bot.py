import os, re, html, asyncio, aiohttp
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps
from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaPhoto
from pyrogram.enums import ParseMode

# ── Config ────────────────────────────────────────────────────────────────────
API_ID    = int(os.environ["API_ID"])
API_HASH  = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_IDS = list(map(int, os.environ.get("ADMIN_IDS", "").split(",")))
MAX_IMAGES = 1000

app = Client("kenshin_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
FONT_BOLD = "OpenSans-Bold.ttf"

# ── Global State ──────────────────────────────────────────────────────────────
SET_STICKER = None 
LOGO_PATH = "kenshin_logo.png"
VIDEO_QUEUE = []
IS_FORMATTING = False
EPISODE_START = 1

# ══════════════════════════════════════════════════════════════════════════════
#  THUMBNAIL & LOGO SYSTEM
# ══════════════════════════════════════════════════════════════════════════════

async def make_kenshin_thumbnail(image_url):
    if not image_url: return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                if resp.status != 200: return None
                img_data = await resp.read()
        
        img = Image.open(BytesIO(img_data)).convert("RGBA")
        img = ImageOps.fit(img, (1280, 720)) 
        
        # 1. Top-Right Logo Watermark
        if os.path.exists(LOGO_PATH):
            logo = Image.open(LOGO_PATH).convert("RGBA")
            logo.thumbnail((120, 120), Image.Resampling.LANCZOS)
            img.paste(logo, (1280 - logo.width - 25, 25), logo)
            
        # 2. Bottom Branding Bar
        img = img.convert("RGB")
        draw = ImageDraw.Draw(img)
        bar_height = 85
        overlay = Image.new('RGBA', (1280, bar_height), (0, 0, 0, 190))
        img.paste(overlay, (0, 720 - bar_height), overlay)
        
        try: font = ImageFont.truetype(FONT_BOLD, 48)
        except: font = ImageFont.load_default()
            
        text = "KENSHIN ANIME"
        w = draw.textlength(text, font=font)
        draw.text(((1280-w)/2, 720 - 70), text, fill="white", font=font)
        
        output = BytesIO()
        output.name = "thumb.jpg"
        img.save(output, "JPEG", quality=95)
        output.seek(0)
        return output
    except Exception as e:
        print(f"Thumb Error: {e}")
        return None

# ══════════════════════════════════════════════════════════════════════════════
#  IMAGE SCRAPING ENGINE (9 SOURCES)
# ══════════════════════════════════════════════════════════════════════════════

async def safe_fetch(coro):
    try:
        res = await coro
        return res if isinstance(res, list) else []
    except: return []

async def src_wallhaven(q, p=5):
    u = []
    async with aiohttp.ClientSession(headers=HEADERS) as s:
        for pg in range(1, p + 1):
            async with s.get("https://wallhaven.cc/api/v1/search", params={"q": q, "categories": "010", "purity": "100", "page": str(pg)}) as r:
                d = await r.json()
                u.extend([x["path"] for x in (d.get("data") or []) if x.get("path")])
    return u

async def src_booru(site, q, tags=""):
    u = []
    tag = re.sub(r"[^a-z0-9_ ]", "", q.lower()).strip().replace(" ", "_")
    async with aiohttp.ClientSession(headers=HEADERS) as s:
        try:
            url = f"https://{site}/index.php"
            params = {"page": "dapi", "s": "post", "q": "index", "tags": f"{tag} {tags}", "json": "1", "limit": "50"}
            async with s.get(url, params=params) as r:
                res = await r.json(content_type=None)
                posts = res if isinstance(res, list) else res.get("post", [])
                for p in posts:
                    img = p.get("sample_url") or p.get("file_url")
                    if img: u.append("https:" + img if img.startswith("//") else img)
        except: pass
    return u

async def src_danbooru(q):
    u = []
    tag = re.sub(r"[^a-z0-9_ ]", "", q.lower()).strip().replace(" ", "_")
    async with aiohttp.ClientSession(headers=HEADERS) as s:
        try:
            async with s.get("https://danbooru.donmai.us/posts.json", params={"tags": f"{tag} rating:g", "limit": "50"}) as r:
                for p in await r.json():
                    img = p.get("large_file_url") or p.get("file_url")
                    if img: u.append(img)
        except: pass
    return u

async def src_jikan(m_id):
    u = []
    async with aiohttp.ClientSession(headers=HEADERS) as s:
        try:
            async with s.get(f"https://api.jikan.moe/v4/anime/{m_id}/pictures") as r:
                d = await r.json()
                u.extend([x["jpg"]["large_image_url"] for x in (d.get("data") or [])])
        except: pass
    return u

# ══════════════════════════════════════════════════════════════════════════════
#  FORMATTING & HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def format_anime_info(media):
    title = (media["title"].get("english") or media["title"].get("romaji") or "Unknown").upper()
    score = f"{(media.get('averageScore') or 0)/10:.1f}/10"
    season = f"{(media.get('season') or 'Unknown').title()} {media.get('seasonYear') or ''}"
    studio = media.get("studios", {}).get("nodes", [{}])[0].get("name", "Unknown")
    tags = ", ".join((media.get("genres") or ["Action"])[:4])
    desc = html.escape(re.sub(r"<[^>]+>", "", media.get('description') or "No Synopsis."))
    
    return (
        f"<b><blockquote>​「 {title} 」</blockquote>\n"
        f"┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"
        f"🌸 Category: Anime\n"
        f"🍥 Season: {season}\n"
        f"🍡 Score: {score}\n"
        f"🍵 Studio: {studio}\n"
        f"🎐 Tags: {tags}\n"
        f"┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"
        f"<blockquote expandable>​📜 SYNOPSIS: ​{desc}</blockquote>\n\n"
        f"<blockquote>POWERED BY:- [@KENSHIN_ANIME]</blockquote></b>"
    )

# ══════════════════════════════════════════════════════════════════════════════
#  CORE COMMANDS
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("start") & filters.private)
async def start(_, msg):
    await msg.reply("🔥 **Kenshin Bot v8 Active!**\nUse /help to see commands.")

@app.on_message(filters.command("help") & filters.private)
async def help_cmd(_, msg):
    help_text = (
        "**🚀 KENSHIN BOT HELP MENU**\n\n"
        "**Image Commands:**\n"
        "• Just send Anime/Character name.\n"
        "• /setlogo (Reply to photo): Set watermark.\n\n"
        "**Video Batch Commands:**\n"
        "• `/format [ep_start]` : Start queueing videos.\n"
        "• `/process` : Send all queued videos with auto-captions.\n"
        "• `/setsticker` (Reply to sticker): Set post-video sticker.\n"
        "• `/clear` : Clear current video queue."
    )
    await msg.reply(help_text)

@app.on_message(filters.command("setsticker") & filters.reply)
async def set_sticker_handler(_, msg):
    global SET_STICKER
    if msg.reply_to_message.sticker:
        SET_STICKER = msg.reply_to_message.sticker.file_id
        await msg.reply("✅ Sticker Set!")

@app.on_message(filters.command("setlogo") & filters.reply)
async def set_logo_handler(_, msg):
    if msg.reply_to_message.photo:
        await msg.reply_to_message.download(file_name=LOGO_PATH)
        await msg.reply("✅ Logo Set for Watermark!")

# ══════════════════════════════════════════════════════════════════════════════
#  QUEUE & BATCH PROCESSING
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("format"))
async def format_start(_, msg):
    global IS_FORMATTING, VIDEO_QUEUE, EPISODE_START
    IS_FORMATTING = True
    VIDEO_QUEUE = []
    args = msg.text.split()
    EPISODE_START = int(args[1]) if len(args) > 1 else 1
    await msg.reply(f"📥 **Queue Mode ON!** Send videos now. Batch will start from Episode {EPISODE_START}.")

@app.on_message(filters.video & filters.private)
async def collector(_, msg):
    if IS_FORMATTING:
        VIDEO_QUEUE.append(msg)
        await msg.reply(f"✅ Added to Queue! (Total: {len(VIDEO_QUEUE)})", quote=True)

@app.on_message(filters.command("process"))
async def process_queue(_, msg):
    global IS_FORMATTING, VIDEO_QUEUE
    if not VIDEO_QUEUE:
        return await msg.reply("❌ Queue khaali hai!")
    
    status = await msg.reply(f"⚙️ Processing {len(VIDEO_QUEUE)} videos...")
    IS_FORMATTING = False 
    
    current_ep = EPISODE_START
    for v_msg in VIDEO_QUEUE:
        h = v_msg.video.height
        res = "480p" if h <= 480 else "720p" if h <= 720 else "1080p" if h <= 1080 else "4K"
        
        cap = f"<b>🚀 Episode {current_ep} | {res}\n\n📺 @KENSHIN_ANIME</b>"
        
        await v_msg.copy(chat_id=msg.chat.id, caption=cap, parse_mode=ParseMode.HTML)
        if SET_STICKER:
            await msg.reply_sticker(SET_STICKER)
        
        current_ep += 1
        await asyncio.sleep(2) # Flood avoidance
        
    await status.edit("✅ Batch Processing Complete!")
    VIDEO_QUEUE = []

@app.on_message(filters.command("clear"))
async def clear_queue(_, msg):
    global VIDEO_QUEUE, IS_FORMATTING
    VIDEO_QUEUE = []
    IS_FORMATTING = False
    await msg.reply("🗑 Queue cleared and formatting mode OFF.")

# ══════════════════════════════════════════════════════════════════════════════
#  ANIME SEARCH ENGINE
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.text & filters.private & ~filters.command(["start", "help", "format", "process", "clear", "setsticker", "setlogo"]))
async def anime_search(_, msg):
    if msg.from_user.id not in ADMIN_IDS: return
    query = msg.text.strip()
    wait = await msg.reply(f"🔍 Fetching details for **{query}**...")

    # Anilist Fetch
    q_anilist = """query($s:String){ Media(search:$s,type:ANIME){ idMal title{english romaji} genres description averageScore season seasonYear studios(isMain:true){nodes{name}} bannerImage coverImage{extraLarge} } }"""
    async with aiohttp.ClientSession() as s:
        async with s.post("https://graphql.anilist.co", json={"query":q_anilist, "variables":{"s":query}}) as r:
            media = (await r.json()).get("data", {}).get("Media")

    if not media:
        return await wait.edit("❌ No Anime Found!")

    title = media["title"].get("english") or media["title"].get("romaji")
    
    # Start Scraping
    await wait.edit("📡 Scraping 9 sources + Generating Watermarked Thumb...")
    
    # Thumbnail logic
    primary_img = media.get("bannerImage") or media.get("coverImage", {}).get("extraLarge")
    thumb = await make_kenshin_thumbnail(primary_img)

    # Scrapers
    wh, sa, ge, da = await asyncio.gather(
        src_wallhaven(title), src_booru("safebooru.org", title),
        src_booru("gelbooru.com", title, "rating:general"), src_danbooru(title)
    )
    jk = await src_jikan(media["idMal"]) if media.get("idMal") else []

    all_urls = list(dict.fromkeys(wh + sa + ge + da + jk))
    
    # Validation
    valid = []
    async with aiohttp.ClientSession(headers=HEADERS) as sess:
        for u in all_urls[:50]: # Check first 50 for speed
            try:
                async with sess.head(u, timeout=3) as rs:
                    if rs.status == 200: valid.append(u)
            except: pass

    await wait.delete()
    cap = format_anime_info(media)
    
    # Send Result
    if thumb: await msg.reply_photo(thumb, caption=cap, parse_mode=ParseMode.HTML)
    elif primary_img: await msg.reply_photo(primary_img, caption=cap, parse_mode=ParseMode.HTML)
    
    if valid:
        for i in range(0, len(valid), 10):
            batch = [InputMediaPhoto(u) for u in valid[i:i+10]]
            try: await msg.reply_media_group(batch); await asyncio.sleep(1)
            except: pass

if __name__ == "__main__":
    app.run()
