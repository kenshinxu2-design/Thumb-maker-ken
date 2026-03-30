import os, re, html, asyncio
import aiohttp
from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaPhoto

# ── Config ────────────────────────────────────────────────────────────────────
API_ID    = int(os.environ["API_ID"])
API_HASH  = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_IDS = list(map(int, os.environ.get("ADMIN_IDS", "").split(",")))
MAX_IMAGES = 1000

app = Client("kenshin_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0 Safari/537.36"}

# ══════════════════════════════════════════════════════════════════════════════
#  ABBREVIATIONS + ROLE KEYWORDS
# ══════════════════════════════════════════════════════════════════════════════
ABBR = {
    "jjk": "Jujutsu Kaisen", "aot": "Attack on Titan", "snk": "Attack on Titan",
    "bnha": "My Hero Academia", "mha": "My Hero Academia",
    "hxh": "Hunter x Hunter", "fmab": "Fullmetal Alchemist Brotherhood",
    "fma": "Fullmetal Alchemist Brotherhood",
    "op": "One Piece", "sl": "Solo Leveling", "dbs": "Dragon Ball Super",
    "dbz": "Dragon Ball Z", "kny": "Demon Slayer", "ds": "Demon Slayer",
    "tpn": "The Promised Neverland", "rezero": "Re:Zero", "re zero": "Re:Zero",
    "sao": "Sword Art Online", "cote": "Classroom of the Elite",
    "mp100": "Mob Psycho 100", "opm": "One Punch Man",
    "nnt": "Seven Deadly Sins", "sds": "Seven Deadly Sins",
    "tg": "Tokyo Ghoul", "bsd": "Bungo Stray Dogs", "bc": "Black Clover",
    "csm": "Chainsaw Man", "cm": "Chainsaw Man",
    "jojo": "JoJo's Bizarre Adventure", "jjba": "JoJo's Bizarre Adventure",
    "nge": "Neon Genesis Evangelion", "eva": "Neon Genesis Evangelion",
    "tensura": "That Time I Got Reincarnated as a Slime",
    "slime": "That Time I Got Reincarnated as a Slime",
    "konosuba": "KonoSuba", "trigun": "Trigun Stampede",
    "onk": "Oshi no Ko", "blue lock": "Blue Lock",
    "bocchi": "Bocchi the Rock", "lycoris": "Lycoris Recoil", "dr": "Dandadan",
}

ROLE_KEYWORDS = {
    "main character": "main", "main char": "main", "main chara": "main",
    "protagonist": "main", "mc": "main",
    "villain": "villain", "antagonist": "villain",
    "female lead": "female_lead", "heroine": "female_lead",
    "best girl": "female_lead", "waifu": "female_lead",
}

# ══════════════════════════════════════════════════════════════════════════════
#  CORE UTILS
# ══════════════════════════════════════════════════════════════════════════════

def get_safe_name(char_obj: dict, query: str = "Unknown") -> str:
    """Extracts name safely whether it's a dict or a string from Jikan API."""
    raw = char_obj.get("name")
    if not raw: return query
    if isinstance(raw, dict):
        return raw.get("full") or raw.get("first") or query
    return str(raw)

def parse_query(raw: str):
    q = raw.strip().lower()
    detected_role = None
    for kw in sorted(ROLE_KEYWORDS.keys(), key=len, reverse=True):
        if kw in q:
            detected_role = ROLE_KEYWORDS[kw]
            q = q.replace(kw, "").strip(" ,.-")
            break
    anime_resolved = None
    for abbr in sorted(ABBR.keys(), key=len, reverse=True):
        if q == abbr or q.startswith(abbr + " ") or q.endswith(" " + abbr):
            anime_resolved = ABBR[abbr]
            break
    clean = anime_resolved or raw.strip()
    return anime_resolved, detected_role, clean

# ══════════════════════════════════════════════════════════════════════════════
#  IMAGE SOURCES (Safe Fetching)
# ══════════════════════════════════════════════════════════════════════════════

async def safe_fetch(coro) -> list:
    try:
        result = await coro
        return result if isinstance(result, list) else []
    except Exception as e:
        print(f"[safe_fetch] {e}")
        return []

async def src_wallhaven(query: str, pages: int = 8) -> list:
    urls = []
    async with aiohttp.ClientSession(headers=HEADERS) as s:
        for page in range(1, pages + 1):
            try:
                async with s.get(
                    "https://wallhaven.cc/api/v1/search",
                    params={"q": query, "categories": "010", "purity": "100",
                            "sorting": "relevance", "page": str(page)},
                    timeout=aiohttp.ClientTimeout(total=12),
                ) as r:
                    if r.status != 200: break
                    d = await r.json()
                    batch = [p["path"] for p in (d.get("data") or []) if p.get("path")]
                    if not batch: break
                    urls.extend(batch)
                    await asyncio.sleep(0.3)
            except: break
    return urls

async def src_safebooru(query: str) -> list:
    urls = []
    tag = re.sub(r"[^a-z0-9_ ]", "", query.lower()).strip().replace(" ", "_")
    async with aiohttp.ClientSession(headers=HEADERS) as s:
        for pid in range(3):
            try:
                async with s.get("https://safebooru.org/index.php",
                    params={"page": "dapi", "s": "post", "q": "index", "tags": tag, "json": "1", "limit": "100", "pid": str(pid)},
                    timeout=aiohttp.ClientTimeout(total=12)) as r:
                    if r.status != 200: break
                    posts = await r.json(content_type=None)
                    if not posts or not isinstance(posts, list): break
                    for p in posts:
                        img = p.get("sample_url") or p.get("file_url")
                        if img: urls.append("https:" + img if img.startswith("//") else img)
                await asyncio.sleep(0.3)
            except: break
    return urls

async def src_gelbooru(query: str) -> list:
    urls = []
    tag = re.sub(r"[^a-z0-9_ ]", "", query.lower()).strip().replace(" ", "_")
    async with aiohttp.ClientSession(headers=HEADERS) as s:
        for pid in range(4):
            try:
                async with s.get("https://gelbooru.com/index.php",
                    params={"page": "dapi", "s": "post", "q": "index", "tags": f"{tag} rating:general", "json": "1", "limit": "100", "pid": str(pid)},
                    timeout=aiohttp.ClientTimeout(total=12)) as r:
                    if r.status != 200: break
                    d = await r.json(content_type=None)
                    posts = d.get("post") or []
                    for p in posts:
                        img = p.get("sample_url") or p.get("file_url")
                        if img: urls.append("https:" + img if img.startswith("//") else img)
                await asyncio.sleep(0.3)
            except: break
    return urls

async def src_konachan(query: str) -> list:
    urls = []
    tag = re.sub(r"[^a-z0-9_ ]", "", query.lower()).strip().replace(" ", "_")
    async with aiohttp.ClientSession(headers=HEADERS) as s:
        for page in range(1, 5):
            try:
                async with s.get("https://konachan.net/post.json", params={"tags": f"{tag} rating:s", "limit": "50", "page": str(page)}) as r:
                    posts = await r.json()
                    if not posts: break
                    for p in posts:
                        img = p.get("sample_url") or p.get("jpeg_url")
                        if img: urls.append("https:" + img if img.startswith("//") else img)
                await asyncio.sleep(0.3)
            except: break
    return urls

async def src_yandere(query: str) -> list:
    urls = []
    tag = re.sub(r"[^a-z0-9_ ]", "", query.lower()).strip().replace(" ", "_")
    async with aiohttp.ClientSession(headers=HEADERS) as s:
        for page in range(1, 5):
            try:
                async with s.get("https://yande.re/post.json", params={"tags": f"{tag} rating:s", "limit": "50", "page": str(page)}) as r:
                    posts = await r.json()
                    if not posts: break
                    for p in posts:
                        img = p.get("sample_url") or p.get("jpeg_url")
                        if img: urls.append("https:" + img if img.startswith("//") else img)
                await asyncio.sleep(0.3)
            except: break
    return urls

async def src_zerochan(query: str) -> list:
    urls = []
    async with aiohttp.ClientSession(headers={**HEADERS, "Accept": "application/json"}) as s:
        for page in range(1, 4):
            try:
                async with s.get(f"https://www.zerochan.net/{query.replace(' ', '+')}", params={"json": "1", "l": "50", "p": str(page)}) as r:
                    d = await r.json()
                    items = d.get("items") or []
                    for item in items:
                        img = item.get("src") or item.get("thumbnail")
                        if img: urls.append(re.sub(r"\.\d+\.", ".", img))
                await asyncio.sleep(0.3)
            except: break
    return urls

async def src_danbooru(query: str) -> list:
    urls = []
    tag = re.sub(r"[^a-z0-9_ ]", "", query.lower()).strip().replace(" ", "_")
    async with aiohttp.ClientSession(headers=HEADERS) as s:
        for page in range(1, 6):
            try:
                async with s.get("https://danbooru.donmai.us/posts.json", params={"tags": f"{tag} rating:g", "limit": "100", "page": str(page)}) as r:
                    posts = await r.json()
                    for p in posts:
                        img = p.get("large_file_url") or p.get("file_url")
                        if img: urls.append(img)
                await asyncio.sleep(0.3)
            except: break
    return urls

async def src_jikan(mal_id: int) -> list:
    urls = []
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as s:
            async with s.get(f"https://api.jikan.moe/v4/anime/{mal_id}/pictures") as r:
                d = await r.json()
                for item in (d.get("data") or []):
                    lg = item.get("jpg", {}).get("large_image_url")
                    if lg: urls.append(lg)
    except: pass
    return urls

async def src_kitsu(name: str) -> list:
    urls = []
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as s:
            async with s.get("https://kitsu.io/api/edge/anime", params={"filter[text]": name, "page[limit]": "5"}, headers={"Accept": "application/vnd.api+json"}) as r:
                d = await r.json()
                for item in (d.get("data") or []):
                    attrs = item.get("attributes", {})
                    for key in ("coverImage", "posterImage"):
                        img = attrs.get(key) or {}
                        if img.get("original"): urls.append(img["original"])
    except: pass
    return urls

# ══════════════════════════════════════════════════════════════════════════════
#  ANILIST + CHARACTER LOGIC
# ══════════════════════════════════════════════════════════════════════════════
ANILIST_Q = """
query($s:String){
  Media(search:$s,type:ANIME){
    idMal title{english romaji} genres description(asHtml:false)
    averageScore episodes status season seasonYear
    studios(isMain:true){nodes{name}}
    coverImage{extraLarge large} bannerImage trailer{site id}
  }
}"""

async def fetch_anilist(name: str):
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post("https://graphql.anilist.co", json={"query": ANILIST_Q, "variables": {"s": name}}) as r:
                d = await r.json()
                return d.get("data", {}).get("Media")
    except: return None

async def search_character(name: str):
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as s:
            async with s.get("https://api.jikan.moe/v4/characters", params={"q": name, "limit": "1"}) as r:
                d = await r.json()
                results = d.get("data") or []
                if not results: return None
                char_id = results[0].get("mal_id")
                if char_id:
                    await asyncio.sleep(0.5)
                    async with s.get(f"https://api.jikan.moe/v4/characters/{char_id}") as r2:
                        cd = await r2.json()
                        return cd.get("data")
                return results[0]
    except: return None

async def get_main_character(mal_id: int, role: str):
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"https://api.jikan.moe/v4/anime/{mal_id}/characters") as r:
                d = await r.json()
                chars = d.get("data") or []
                mains = [c for c in chars if c.get("role") == "Main"]
                supp = [c for c in chars if c.get("role") == "Supporting"]
                
                if role == "villain": pick = supp[0] if supp else (mains[0] if mains else None)
                elif role == "female_lead": pick = mains[1] if len(mains) > 1 else (mains[0] if mains else None)
                else: pick = mains[0] if mains else (chars[0] if chars else None)

                if pick:
                    char_id = pick.get("character", {}).get("mal_id")
                    await asyncio.sleep(0.5)
                    async with s.get(f"https://api.jikan.moe/v4/characters/{char_id}") as r2:
                        cd = await r2.json()
                        return cd.get("data")
    except: return None

# ══════════════════════════════════════════════════════════════════════════════
#  FORMATTING & VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

def clean_desc(text: str, limit: int = 900) -> str:
    if not text: return "No description."
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text).strip()
    if len(text) > limit: text = text[:limit].rsplit(" ", 1)[0] + "..."
    return text

def format_anime_info(media: dict) -> str:
    title = media["title"].get("english") or media["title"].get("romaji") or "Unknown"
    genres = " | ".join(media.get("genres") or [])
    score = media.get("averageScore") or 0
    rating = round(score / 10, 1)
    eps = media.get("episodes") or "?"
    status = (media.get("status") or "").replace("_", " ").title()
    studio = media.get("studios", {}).get("nodes", [{}])[0].get("name", "Unknown")
    desc = clean_desc(media.get("description"))
    return (
        f"🎌 **{title}**\n━━━━━━━━━━━━━━━━━━━━\n"
        f"🎭 **Genres:** `{genres}`\n"
        f"⭐ **Rating:** `{rating}/10`\n"
        f"📺 **Episodes:** `{eps}` | **Status:** `{status}`\n"
        f"🏢 **Studio:** `{studio}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📖 **Synopsis:**\n{desc}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📺 **KenshinAnime** | @kenshin_anime"
    )

def format_char_info(char: dict) -> str:
    fullname = get_safe_name(char)
    nick = char.get("nicknames") or []
    nick_str = f" _({', '.join(nick[:3])})_" if nick else ""
    about = clean_desc(char.get("about"), limit=700)
    fav = char.get("favorites") or 0
    return (
        f"👤 **{fullname}**{nick_str}\n━━━━━━━━━━━━━━━━━━━━\n"
        f"❤️ **MAL Favorites:** `{fav:,}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📖 **About:**\n{about}\n━━━━━━━━━━━━━━━━━━━━\n"
        f"📺 **KenshinAnime** | @kenshin_anime"
    )

async def validate_urls(all_urls: list) -> list:
    valid = []
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        for i in range(0, min(len(all_urls), MAX_IMAGES), 50):
            batch = all_urls[i:i+50]
            async def check(u):
                try:
                    async with session.head(u, timeout=5, allow_redirects=True) as r:
                        return u if r.status == 200 else None
                except: return None
            res = await asyncio.gather(*[check(u) for u in batch])
            valid.extend([u for u in res if u])
    return valid

# ══════════════════════════════════════════════════════════════════════════════
#  HANDLERS
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("start") & filters.private)
async def cmd_start(_, msg: Message):
    if msg.from_user.id not in ADMIN_IDS: return
    await msg.reply("🚀 **Kenshin Anime Bot v6 Online!**\nBhejo koi bhi anime ya character name.")

@app.on_message(filters.text & filters.private & ~filters.command(["start"]))
async def on_search(_, msg: Message):
    if msg.from_user.id not in ADMIN_IDS: return
    raw_query = msg.text.strip()
    anime_res, det_role, query = parse_query(raw_query)
    wait = await msg.reply(f"🔍 Searching **{query}**...")

    # Logic: Search Anime and Character in parallel
    media, char = await asyncio.gather(fetch_anilist(query), search_character(query))
    
    is_char = False
    if char and not media:
        is_char = True
    elif char and media:
        # Score comparison logic safely
        char_full = get_safe_name(char, "").lower()
        anime_title_data = media.get("title") or {}
        anime_name = (anime_title_data.get("english") or anime_title_data.get("romaji") or "").lower()
        
        q_lower = query.lower()
        char_score = sum(1 for w in q_lower.split() if w in char_full)
        anime_score = sum(1 for w in q_lower.split() if w in anime_name)
        if char_score > anime_score: is_char = True

    if is_char:
        await _send_character(msg, wait, char, query)
    elif media:
        await _send_anime(msg, wait, media, query)
    else:
        await wait.edit("❌ Kuch nahi mila! Sahi naam likho.")

async def _send_anime(msg: Message, wait: Message, media: dict, query: str):
    title = media["title"].get("english") or media["title"].get("romaji") or query
    await wait.edit(f"🎌 **{title}** mila! Images fetch ho rahi hain...")
    
    # Fetch from all sources
    wh, sb, gb, kc, yd, zc, db, kt = await asyncio.gather(
        safe_fetch(src_wallhaven(title)), safe_fetch(src_safebooru(title)),
        safe_fetch(src_gelbooru(title)), safe_fetch(src_konachan(title)),
        safe_fetch(src_yandere(title)), safe_fetch(src_zerochan(title)),
        safe_fetch(src_danbooru(title)), safe_fetch(src_kitsu(title))
    )
    jk = await safe_fetch(src_jikan(media.get("idMal"))) if media.get("idMal") else []
    
    all_urls = list(dict.fromkeys(wh + sb + gb + kc + yd + zc + db + kt + jk))
    valid = await validate_urls(all_urls)
    await wait.delete()
    
    if valid:
        try: await msg.reply_photo(valid[0], caption=format_anime_info(media))
        except: await msg.reply(format_anime_info(media))
        # Send batches of 10
        for i in range(1, len(valid), 10):
            batch = [InputMediaPhoto(u) for u in valid[i:i+10]]
            try: await msg.reply_media_group(batch); await asyncio.sleep(1)
            except: pass
    else:
        await msg.reply(format_anime_info(media))

async def _send_character(msg: Message, wait: Message, char: dict, query: str):
    name = get_safe_name(char, query)
    await wait.edit(f"👤 **{name}** mila! Images fetch ho rahi hain...")
    
    wh, sb, gb, db, zc = await asyncio.gather(
        safe_fetch(src_wallhaven(name, pages=5)), safe_fetch(src_safebooru(name)),
        safe_fetch(src_gelbooru(name)), safe_fetch(src_danbooru(name)), safe_fetch(src_zerochan(name))
    )
    
    all_urls = list(dict.fromkeys(wh + sb + gb + db + zc))
    valid = await validate_urls(all_urls)
    await wait.delete()
    
    info = format_char_info(char)
    if valid:
        try: await msg.reply_photo(valid[0], caption=info)
        except: await msg.reply(info)
        for i in range(1, len(valid), 10):
            batch = [InputMediaPhoto(u) for u in valid[i:i+10]]
            try: await msg.reply_media_group(batch); await asyncio.sleep(1)
            except: pass
    else:
        await msg.reply(info)

if __name__ == "__main__":
    app.run()
