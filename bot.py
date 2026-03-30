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
#  IMAGE SOURCES
# ══════════════════════════════════════════════════════════════════════════════

async def safe_fetch(coro) -> list:
    """Run a coroutine, always return a list (never raise)."""
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
            except Exception as e:
                print(f"[Wallhaven] {e}"); break
    print(f"[Wallhaven] '{query}' → {len(urls)}")
    return urls

async def src_safebooru(query: str) -> list:
    urls = []
    tag = re.sub(r"[^a-z0-9_ ]", "", query.lower()).strip().replace(" ", "_")
    for pid in range(3):
        try:
            async with aiohttp.ClientSession(headers=HEADERS) as s:
                async with s.get(
                    "https://safebooru.org/index.php",
                    params={"page": "dapi", "s": "post", "q": "index",
                            "tags": tag, "json": "1", "limit": "100", "pid": str(pid)},
                    timeout=aiohttp.ClientTimeout(total=12),
                ) as r:
                    if r.status != 200: break
                    posts = await r.json(content_type=None)
                    if not isinstance(posts, list) or not posts: break
                    for p in posts:
                        img = p.get("sample_url") or p.get("file_url") or ""
                        if img:
                            urls.append("https:" + img if img.startswith("//") else img)
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"[Safebooru] {e}"); break
    print(f"[Safebooru] '{tag}' → {len(urls)}")
    return urls

async def src_gelbooru(query: str) -> list:
    urls = []
    tag = re.sub(r"[^a-z0-9_ ]", "", query.lower()).strip().replace(" ", "_")
    for pid in range(4):
        try:
            async with aiohttp.ClientSession(headers=HEADERS) as s:
                async with s.get(
                    "https://gelbooru.com/index.php",
                    params={"page": "dapi", "s": "post", "q": "index",
                            "tags": f"{tag} rating:general", "json": "1",
                            "limit": "100", "pid": str(pid)},
                    timeout=aiohttp.ClientTimeout(total=12),
                ) as r:
                    if r.status != 200: break
                    d = await r.json(content_type=None)
                    posts = d.get("post") or []
                    if not posts: break
                    for p in posts:
                        img = p.get("sample_url") or p.get("file_url") or ""
                        if img:
                            urls.append("https:" + img if img.startswith("//") else img)
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"[Gelbooru] {e}"); break
    print(f"[Gelbooru] '{tag}' → {len(urls)}")
    return urls

async def src_konachan(query: str) -> list:
    urls = []
    tag = re.sub(r"[^a-z0-9_ ]", "", query.lower()).strip().replace(" ", "_")
    for page in range(1, 5):
        try:
            async with aiohttp.ClientSession(headers=HEADERS) as s:
                async with s.get(
                    "https://konachan.net/post.json",
                    params={"tags": f"{tag} rating:s", "limit": "50", "page": str(page)},
                    timeout=aiohttp.ClientTimeout(total=12),
                ) as r:
                    if r.status != 200: break
                    posts = await r.json(content_type=None)
                    if not posts: break
                    for p in posts:
                        img = p.get("sample_url") or p.get("jpeg_url") or ""
                        if img:
                            urls.append("https:" + img if img.startswith("//") else img)
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"[Konachan] {e}"); break
    print(f"[Konachan] '{tag}' → {len(urls)}")
    return urls

async def src_yandere(query: str) -> list:
    urls = []
    tag = re.sub(r"[^a-z0-9_ ]", "", query.lower()).strip().replace(" ", "_")
    for page in range(1, 5):
        try:
            async with aiohttp.ClientSession(headers=HEADERS) as s:
                async with s.get(
                    "https://yande.re/post.json",
                    params={"tags": f"{tag} rating:s", "limit": "50", "page": str(page)},
                    timeout=aiohttp.ClientTimeout(total=12),
                ) as r:
                    if r.status != 200: break
                    posts = await r.json(content_type=None)
                    if not posts: break
                    for p in posts:
                        img = p.get("sample_url") or p.get("jpeg_url") or ""
                        if img:
                            urls.append("https:" + img if img.startswith("//") else img)
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"[Yandere] {e}"); break
    print(f"[Yandere] '{tag}' → {len(urls)}")
    return urls

async def src_zerochan(query: str) -> list:
    urls = []
    try:
        async with aiohttp.ClientSession(headers={**HEADERS, "Accept": "application/json"}) as s:
            for page in range(1, 4):
                try:
                    async with s.get(
                        f"https://www.zerochan.net/{query.replace(' ', '+')}",
                        params={"json": "1", "l": "50", "p": str(page)},
                        timeout=aiohttp.ClientTimeout(total=12),
                    ) as r:
                        if r.status != 200: break
                        d = await r.json(content_type=None)
                        items = d.get("items") or []
                        if not items: break
                        for item in items:
                            img = item.get("src") or item.get("thumbnail") or ""
                            if img:
                                img = re.sub(r"\.\d+\.", ".", img)
                                urls.append(img)
                    await asyncio.sleep(0.3)
                except Exception as e:
                    print(f"[Zerochan p{page}] {e}"); break
    except Exception as e:
        print(f"[Zerochan] {e}")
    print(f"[Zerochan] '{query}' → {len(urls)}")
    return urls

async def src_danbooru(query: str) -> list:
    urls = []
    tag = re.sub(r"[^a-z0-9_ ]", "", query.lower()).strip().replace(" ", "_")
    for page in range(1, 6):
        try:
            async with aiohttp.ClientSession(headers=HEADERS) as s:
                async with s.get(
                    "https://danbooru.donmai.us/posts.json",
                    params={"tags": f"{tag} rating:g", "limit": "100", "page": str(page)},
                    timeout=aiohttp.ClientTimeout(total=12),
                ) as r:
                    if r.status != 200: break
                    posts = await r.json(content_type=None)
                    if not posts: break
                    for p in posts:
                        img = p.get("large_file_url") or p.get("file_url") or ""
                        if img and any(img.lower().endswith(e) for e in (".jpg", ".jpeg", ".png", ".webp")):
                            urls.append(img)
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"[Danbooru] {e}"); break
    print(f"[Danbooru] '{tag}' → {len(urls)}")
    return urls

async def src_jikan(mal_id: int) -> list:
    urls = []
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as s:
            async with s.get(
                f"https://api.jikan.moe/v4/anime/{mal_id}/pictures",
                timeout=aiohttp.ClientTimeout(total=15),
            ) as r:
                if r.status == 200:
                    d = await r.json()
                    for item in (d.get("data") or []):
                        lg = item.get("jpg", {}).get("large_image_url")
                        if lg: urls.append(lg)
    except Exception as e:
        print(f"[Jikan] {e}")
    return urls

async def src_kitsu(name: str) -> list:
    urls = []
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as s:
            async with s.get(
                "https://kitsu.io/api/edge/anime",
                params={"filter[text]": name, "page[limit]": "5"},
                headers={"Accept": "application/vnd.api+json"},
                timeout=aiohttp.ClientTimeout(total=12),
            ) as r:
                if r.status != 200: return []
                d = await r.json()
        for item in (d.get("data") or []):
            attrs = item.get("attributes", {})
            for key in ("coverImage", "posterImage"):
                img = attrs.get(key) or {}
                for size in ("original", "large"):
                    if img.get(size):
                        urls.append(img[size]); break
    except Exception as e:
        print(f"[Kitsu] {e}")
    return urls

# ══════════════════════════════════════════════════════════════════════════════
#  ANILIST
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
        async with aiohttp.ClientSession(headers=HEADERS) as s:
            async with s.post(
                "https://graphql.anilist.co",
                json={"query": ANILIST_Q, "variables": {"s": name}},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as r:
                if r.status != 200: return None
                d = await r.json()
        result = (d.get("data") or {}).get("Media")
        return result if isinstance(result, dict) else None
    except Exception as e:
        print(f"[AniList] {e}")
        return None

# ══════════════════════════════════════════════════════════════════════════════
#  CHARACTER SEARCH
# ══════════════════════════════════════════════════════════════════════════════
async def search_character(name: str):
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as s:
            async with s.get(
                "https://api.jikan.moe/v4/characters",
                params={"q": name, "limit": "1"},
                timeout=aiohttp.ClientTimeout(total=12),
            ) as r:
                if r.status != 200: return None
                d = await r.json()
                results = d.get("data") or []
                if not results: return None
                item = results[0]
                if not isinstance(item, dict): return None
                # Jikan v4: fetch full character details for anime list + about
                char_id = item.get("mal_id")
                if char_id:
                    await asyncio.sleep(0.4)
                    async with s.get(
                        f"https://api.jikan.moe/v4/characters/{char_id}",
                        timeout=aiohttp.ClientTimeout(total=12),
                    ) as r2:
                        if r2.status == 200:
                            cd = await r2.json()
                            full = cd.get("data")
                            return full if isinstance(full, dict) else item
                return item
    except Exception as e:
        print(f"[CharSearch] {e}")
        return None

async def fetch_character_pictures(char_id: int) -> list:
    urls = []
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as s:
            async with s.get(
                f"https://api.jikan.moe/v4/characters/{char_id}/pictures",
                timeout=aiohttp.ClientTimeout(total=12),
            ) as r:
                if r.status == 200:
                    d = await r.json()
                    for item in (d.get("data") or []):
                        lg = (item.get("jpg") or {}).get("image_url") or \
                             (item.get("webp") or {}).get("image_url")
                        if lg: urls.append(lg)
    except Exception as e:
        print(f"[CharPics] {e}")
    return urls

async def get_main_character(mal_id: int, role: str):
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as s:
            async with s.get(
                f"https://api.jikan.moe/v4/anime/{mal_id}/characters",
                timeout=aiohttp.ClientTimeout(total=12),
            ) as r:
                if r.status != 200: return None
                d = await r.json()
                chars = d.get("data") or []
                if not chars: return None

                mains = [c for c in chars if isinstance(c, dict) and c.get("role") == "Main"]
                supporting = [c for c in chars if isinstance(c, dict) and c.get("role") == "Supporting"]

                if role == "villain":
                    supporting.sort(key=lambda c: c.get("favorites") or 0, reverse=True)
                    pick = supporting[0] if supporting else (mains[0] if mains else chars[0])
                elif role == "female_lead":
                    pick = mains[1] if len(mains) > 1 else (mains[0] if mains else chars[0])
                else:
                    mains.sort(key=lambda c: c.get("favorites") or 0, reverse=True)
                    pick = mains[0] if mains else chars[0]

                if not isinstance(pick, dict): return None
                char_data = pick.get("character") or {}
                char_id = char_data.get("mal_id")
                if not char_id: return None

                await asyncio.sleep(0.5)
                async with s.get(
                    f"https://api.jikan.moe/v4/characters/{char_id}",
                    timeout=aiohttp.ClientTimeout(total=12),
                ) as r2:
                    if r2.status == 200:
                        cd = await r2.json()
                        result = cd.get("data")
                        return result if isinstance(result, dict) else None
    except Exception as e:
        print(f"[RoleChar] {e}")
    return None

# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def clean_desc(text: str, limit: int = 900) -> str:
    text = re.sub(r"<[^>]+>", "", text or "")
    text = html.unescape(text).strip()
    text = re.sub(r"\(Source:[^)]+\)", "", text).strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0] + "..."
    return text

def stars(rating: float) -> str:
    filled = max(0, min(5, round(rating / 2)))
    return "⭐" * filled + "☆" * (5 - filled)

def format_anime_info(media: dict) -> str:
    title  = media["title"].get("english") or media["title"].get("romaji") or "Unknown"
    genres = " | ".join(media.get("genres") or [])
    score  = media.get("averageScore") or 0
    rating = round(score / 10, 1)
    eps    = media.get("episodes") or "?"
    status = (media.get("status") or "").replace("_", " ").title()
    season = f"{(media.get('season') or '').title()} {media.get('seasonYear') or ''}".strip()
    nodes  = (media.get("studios") or {}).get("nodes") or []
    studio = nodes[0]["name"] if nodes else "Unknown"
    desc   = clean_desc(media.get("description") or "")
    trailer = ""
    tr = media.get("trailer") or {}
    if tr.get("site") == "youtube" and tr.get("id"):
        trailer = f"\n🎬 **Trailer:** https://youtu.be/{tr['id']}"
    return (
        f"🎌 **{title}**\n━━━━━━━━━━━━━━━━━━━━\n"
        f"🎭 **Genres:** `{genres}`\n"
        f"⭐ **Rating:** {stars(rating)} `{rating}/10`\n"
        f"📺 **Episodes:** `{eps}`\n"
        f"📡 **Status:** `{status}`\n"
        f"🗓️ **Season:** `{season}`\n"
        f"🏢 **Studio:** `{studio}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📖 **Synopsis:**\n{desc}{trailer}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📺 **KenshinAnime** | @kenshin\\_anime"
    )

def format_char_info(char: dict) -> str:
    # Jikan v4: "name" is a plain string, not a dict
    raw_name = char.get("name") or "Unknown"
    fullname = raw_name if isinstance(raw_name, str) else (
        raw_name.get("full") or raw_name.get("first") or "Unknown"
    )
    nick     = char.get("nicknames") or []
    nick_str = f" _({', '.join(nick[:3])})_" if isinstance(nick, list) and nick else ""
    about    = clean_desc(char.get("about") or "No info available.")
    animes   = char.get("anime") or []
    anime_list = ""
    if animes:
        titles = []
        for a in animes[:5]:
            if not isinstance(a, dict): continue
            anime_obj = a.get("anime") or {}
            if isinstance(anime_obj, dict):
                title_obj = anime_obj.get("title") or {}
                if isinstance(title_obj, dict):
                    t = title_obj.get("english") or title_obj.get("romaji") or ""
                elif isinstance(title_obj, str):
                    t = title_obj
                else:
                    t = ""
                if t: titles.append(t)
        if titles:
            anime_list = "\n🎌 **Appears in:** " + " | ".join(titles)
    fav = char.get("favorites") or 0
    return (
        f"👤 **{fullname}**{nick_str}\n━━━━━━━━━━━━━━━━━━━━\n"
        f"❤️ **MAL Favorites:** `{fav:,}`"
        f"{anime_list}\n━━━━━━━━━━━━━━━━━━━━\n"
        f"📖 **About:**\n{about}\n━━━━━━━━━━━━━━━━━━━━\n"
        f"📺 **KenshinAnime** | @kenshin\\_anime"
    )

async def is_valid_image(session: aiohttp.ClientSession, url: str) -> bool:
    try:
        async with session.head(
            url, timeout=aiohttp.ClientTimeout(total=7),
            allow_redirects=True, headers=HEADERS
        ) as r:
            ct = r.headers.get("content-type", "")
            ok_ext = any(url.lower().endswith(e) for e in (".jpg", ".jpeg", ".png", ".webp"))
            return r.status == 200 and ("image" in ct or ok_ext)
    except:
        return False

def dedup(urls: list) -> list:
    seen, out = set(), []
    for u in urls:
        if u and isinstance(u, str) and u not in seen:
            seen.add(u); out.append(u)
    return out

async def validate_urls(all_urls: list) -> list:
    valid = []
    check = all_urls[:MAX_IMAGES]
    for i in range(0, len(check), 50):
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            res = await asyncio.gather(
                *[is_valid_image(session, u) for u in check[i:i+50]],
                return_exceptions=True
            )
            for url, ok in zip(check[i:i+50], res):
                if ok is True: valid.append(url)
        await asyncio.sleep(0.2)
    return valid

async def send_images(msg: Message, valid_urls: list):
    for i in range(0, len(valid_urls), 10):
        batch = valid_urls[i:i+10]
        if not batch: break
        try:
            await msg.reply_media_group([InputMediaPhoto(u) for u in batch])
            await asyncio.sleep(1.2)
        except Exception as e:
            print(f"[MediaGroup] {e}")
            for u in batch:
                try:
                    await msg.reply_photo(u)
                    await asyncio.sleep(0.5)
                except: pass

async def fetch_all_images_for(name: str, pages: int = 8) -> dict:
    """Fetch images from all 9 sources in parallel. Returns dict with counts."""
    wh  = asyncio.create_task(safe_fetch(src_wallhaven(name, pages)))
    sb  = asyncio.create_task(safe_fetch(src_safebooru(name)))
    gb  = asyncio.create_task(safe_fetch(src_gelbooru(name)))
    kc  = asyncio.create_task(safe_fetch(src_konachan(name)))
    yd  = asyncio.create_task(safe_fetch(src_yandere(name)))
    zc  = asyncio.create_task(safe_fetch(src_zerochan(name)))
    db  = asyncio.create_task(safe_fetch(src_danbooru(name)))
    kt  = asyncio.create_task(safe_fetch(src_kitsu(name)))
    results = await asyncio.gather(wh, sb, gb, kc, yd, zc, db, kt, return_exceptions=True)
    names   = ["wallhaven", "safebooru", "gelbooru", "konachan", "yandere", "zerochan", "danbooru", "kitsu"]
    return {n: (r if isinstance(r, list) else []) for n, r in zip(names, results)}

# ══════════════════════════════════════════════════════════════════════════════
#  BOT HANDLERS
# ══════════════════════════════════════════════════════════════════════════════
@app.on_message(filters.command("start") & filters.private)
async def cmd_start(_, msg: Message):
    if msg.from_user.id not in ADMIN_IDS: return
    await msg.reply(
        "**🎌 Kenshin Anime Info Bot v6**\n\n"
        "Kuch bhi bhejo:\n"
        "• `Solo Leveling` — Anime info + images\n"
        "• `Sung Jinwoo` — Character info + images\n"
        "• `jjk main character` — JJK ka MC\n"
        "• `aot villain` — AOT ka villain\n\n"
        "**9 sources:** Wallhaven • Safebooru • Gelbooru\n"
        "Konachan • Yande.re • Zerochan • Danbooru • MAL • Kitsu\n\n"
        f"Max images: `{MAX_IMAGES}`"
    )

@app.on_message(filters.text & filters.private & ~filters.command(["start"]))
async def on_search(_, msg: Message):
    if msg.from_user.id not in ADMIN_IDS: return
    try:
        await _handle_search(msg)
    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            await msg.reply(f"❌ Unexpected error: `{e}`\nDobara try karo.")
        except: pass

async def _handle_search(msg: Message):
    raw_query = msg.text.strip()
    anime_resolved, detected_role, query = parse_query(raw_query)
    wait = await msg.reply(
        f"🔍 Searching **{query}**"
        + (f" | Role: `{detected_role}`" if detected_role else "")
        + "..."
    )

    # ── CASE 1: "jjk main character" / "aot villain" etc. ─────────────────────
    if anime_resolved and detected_role:
        media = await fetch_anilist(anime_resolved)
        if media and isinstance(media, dict) and media.get("idMal"):
            await wait.edit(f"👤 Finding **{detected_role}** of **{anime_resolved}**...")
            char = await get_main_character(media["idMal"], detected_role)
            if char and isinstance(char, dict):
                await _send_character(msg, wait, char, query)
                return
        # Fallback to anime mode
        await wait.edit(f"⚠️ Character nahi mila, anime mode mein ja raha hoon...")

    # ── CASE 2: Normal search — try anime + character in parallel ──────────────
    media_res, char_res = await asyncio.gather(
        fetch_anilist(query),
        search_character(query),
        return_exceptions=True
    )
    # Ensure both are proper dicts or None
    media = media_res if isinstance(media_res, dict) else None
    char  = char_res  if isinstance(char_res,  dict) else None

    # Decide mode: character if only char found, OR query matches char name better
    is_char = False
    if char and not media:
        is_char = True
    elif char and media:
        raw_cname  = char.get("name") or ""
        char_full  = (raw_cname if isinstance(raw_cname, str) else
                      raw_cname.get("full") or raw_cname.get("first") or "").lower()
        anime_name = ((media.get("title") or {}).get("english") or
                      (media.get("title") or {}).get("romaji") or "").lower()
        q_lower    = query.lower()
        # Count word matches
        char_score  = sum(1 for w in q_lower.split() if w in char_full)
        anime_score = sum(1 for w in q_lower.split() if w in anime_name)
        if char_score > anime_score:
            is_char = True

    if is_char and char:
        await _send_character(msg, wait, char, query)
        return

    if not media:
        await wait.edit(
            "❌ Kuch nahi mila!\n"
            "• Anime ke liye English title try kar\n"
            "• Character ke liye full name try kar\n"
            "_Example: `Solo Leveling`, `Sung Jinwoo`, `jjk mc`_"
        )
        return

    # ── ANIME MODE ─────────────────────────────────────────────────────────────
    anime_title = (media.get("title") or {}).get("english") or \
                  (media.get("title") or {}).get("romaji") or query
    mal_id = media.get("idMal")
    await wait.edit(f"🎌 **{anime_title}** mila! 9 sources se images fetch ho rahi hain...")

    # AniList images
    cover   = media.get("coverImage") or {}
    al_imgs = []
    for key in ("extraLarge", "large"):
        if cover.get(key):
            al_imgs.append(cover[key]); break
    if media.get("bannerImage"):
        al_imgs.append(media["bannerImage"])

    # All sources in parallel
    src_dict = await fetch_all_images_for(anime_title)
    jk_imgs  = await safe_fetch(src_jikan(mal_id)) if mal_id else []

    all_urls = dedup(
        al_imgs +
        src_dict["wallhaven"] + src_dict["safebooru"] + src_dict["gelbooru"] +
        src_dict["konachan"]  + src_dict["yandere"]   + src_dict["zerochan"] +
        src_dict["danbooru"]  + jk_imgs + src_dict["kitsu"]
    )

    await wait.edit(f"🖼️ {len(all_urls)} images mili! Validate ho rahi hain...")
    valid_urls = await validate_urls(all_urls)
    await wait.delete()

    if valid_urls:
        try: await msg.reply_photo(valid_urls[0], caption=format_anime_info(media))
        except: await msg.reply(format_anime_info(media))
        await send_images(msg, valid_urls[1:])
    else:
        await msg.reply(format_anime_info(media))

    await msg.reply(
        f"📊 **{anime_title} — Sources:**\n"
        f"🖼️ Wallhaven: `{len(src_dict['wallhaven'])}`\n"
        f"🎨 Safebooru: `{len(src_dict['safebooru'])}`\n"
        f"🎨 Gelbooru: `{len(src_dict['gelbooru'])}`\n"
        f"🖼️ Konachan: `{len(src_dict['konachan'])}`\n"
        f"🖼️ Yande.re: `{len(src_dict['yandere'])}`\n"
        f"🌸 Zerochan: `{len(src_dict['zerochan'])}`\n"
        f"📌 Danbooru: `{len(src_dict['danbooru'])}`\n"
        f"📺 MAL: `{len(jk_imgs)}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ **Sent: {len(valid_urls)} images** 🔥"
    )

async def _send_character(msg: Message, wait: Message, char: dict, query: str):
    char_id  = char.get("mal_id")
    raw_name  = char.get("name") or query
    char_name = raw_name if isinstance(raw_name, str) else (
        raw_name.get("full") or raw_name.get("first") or query
    )
    await wait.edit(f"👤 **{char_name}** mila! Images fetch ho rahi hain...")

    char_img = (char.get("images") or {}).get("jpg", {}).get("image_url") or \
               (char.get("images") or {}).get("webp", {}).get("image_url")

    src_dict  = await fetch_all_images_for(char_name, pages=6)
    char_pics = await safe_fetch(fetch_character_pictures(char_id)) if char_id else []

    all_urls = dedup(
        ([char_img] if char_img else []) + char_pics +
        src_dict["wallhaven"] + src_dict["safebooru"] + src_dict["gelbooru"] +
        src_dict["konachan"]  + src_dict["yandere"]   + src_dict["zerochan"] +
        src_dict["danbooru"]
    )

    await wait.edit(f"🖼️ {len(all_urls)} images validate ho rahi hain...")
    valid_urls = await validate_urls(all_urls)
    await wait.delete()

    info = format_char_info(char)
    if valid_urls:
        try: await msg.reply_photo(valid_urls[0], caption=info)
        except: await msg.reply(info)
        await send_images(msg, valid_urls[1:])
    else:
        await msg.reply(info)

    await msg.reply(
        f"📊 **{char_name} — Sources:**\n"
        f"🖼️ Wallhaven: `{len(src_dict['wallhaven'])}`\n"
        f"🎨 Safebooru: `{len(src_dict['safebooru'])}`\n"
        f"🎨 Gelbooru: `{len(src_dict['gelbooru'])}`\n"
        f"📌 Danbooru: `{len(src_dict['danbooru'])}`\n"
        f"📺 MAL Char: `{len(char_pics)}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ **Sent: {len(valid_urls)} images** 🔥"
    )

# ── Entry ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 Kenshin Anime Info Bot v6 start ho raha hai...")
    app.run()
