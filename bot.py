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

app = Client("kenshin_info_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0 Safari/537.36"}

# ══════════════════════════════════════════════════════════════════════════════
#  IMAGE SOURCES (10 sources)
# ══════════════════════════════════════════════════════════════════════════════

# 1. Wallhaven — HD anime wallpapers, multiple pages
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
                    if r.status != 200:
                        break
                    d = await r.json()
                    batch = [p["path"] for p in (d.get("data") or []) if p.get("path")]
                    if not batch:
                        break
                    urls.extend(batch)
                    await asyncio.sleep(0.3)
            except Exception as e:
                print(f"[Wallhaven p{page}] {e}")
                break
    print(f"[Wallhaven] {query!r} → {len(urls)}")
    return urls

# 2. Safebooru — SFW fan art
async def src_safebooru(query: str, limit: int = 100) -> list:
    urls = []
    tag = re.sub(r"[^a-z0-9_ ]", "", query.lower()).strip().replace(" ", "_")
    for pid in range(0, 3):
        try:
            async with aiohttp.ClientSession(headers=HEADERS) as s:
                async with s.get(
                    "https://safebooru.org/index.php",
                    params={"page": "dapi", "s": "post", "q": "index",
                            "tags": tag, "json": "1", "limit": "100", "pid": str(pid)},
                    timeout=aiohttp.ClientTimeout(total=12),
                ) as r:
                    if r.status != 200:
                        break
                    posts = await r.json(content_type=None)
                    if not isinstance(posts, list) or not posts:
                        break
                    for p in posts:
                        img = p.get("sample_url") or p.get("file_url") or ""
                        if img:
                            if img.startswith("//"):
                                img = "https:" + img
                            urls.append(img)
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"[Safebooru] {e}")
            break
    print(f"[Safebooru] {tag!r} → {len(urls)}")
    return urls

# 3. Gelbooru — huge anime image DB, free
async def src_gelbooru(query: str) -> list:
    urls = []
    tag = re.sub(r"[^a-z0-9_ ]", "", query.lower()).strip().replace(" ", "_")
    for pid in range(0, 4):
        try:
            async with aiohttp.ClientSession(headers=HEADERS) as s:
                async with s.get(
                    "https://gelbooru.com/index.php",
                    params={"page": "dapi", "s": "post", "q": "index",
                            "tags": f"{tag} rating:general", "json": "1",
                            "limit": "100", "pid": str(pid)},
                    timeout=aiohttp.ClientTimeout(total=12),
                ) as r:
                    if r.status != 200:
                        break
                    d = await r.json(content_type=None)
                    posts = d.get("post") or []
                    if not posts:
                        break
                    for p in posts:
                        img = p.get("sample_url") or p.get("file_url") or ""
                        if img:
                            if img.startswith("//"):
                                img = "https:" + img
                            urls.append(img)
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"[Gelbooru] {e}")
            break
    print(f"[Gelbooru] {tag!r} → {len(urls)}")
    return urls

# 4. Konachan — high-quality anime wallpapers
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
                    if r.status != 200:
                        break
                    posts = await r.json(content_type=None)
                    if not posts:
                        break
                    for p in posts:
                        img = p.get("sample_url") or p.get("jpeg_url") or ""
                        if img:
                            if img.startswith("//"):
                                img = "https:" + img
                            urls.append(img)
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"[Konachan] {e}")
            break
    print(f"[Konachan] {tag!r} → {len(urls)}")
    return urls

# 5. Yande.re — high-res scans and art
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
                    if r.status != 200:
                        break
                    posts = await r.json(content_type=None)
                    if not posts:
                        break
                    for p in posts:
                        img = p.get("sample_url") or p.get("jpeg_url") or ""
                        if img:
                            if img.startswith("//"):
                                img = "https:" + img
                            urls.append(img)
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"[Yande.re] {e}")
            break
    print(f"[Yande.re] {tag!r} → {len(urls)}")
    return urls

# 6. Zerochan — large anime image board
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
                        if r.status != 200:
                            break
                        d = await r.json(content_type=None)
                        items = d.get("items") or []
                        if not items:
                            break
                        for item in items:
                            img = item.get("src") or item.get("thumbnail") or ""
                            if img:
                                # Convert thumbnail URL to full size
                                img = re.sub(r"\.\d+\.", ".", img)
                                urls.append(img)
                    await asyncio.sleep(0.3)
                except Exception as e:
                    print(f"[Zerochan p{page}] {e}")
                    break
    except Exception as e:
        print(f"[Zerochan] {e}")
    print(f"[Zerochan] {query!r} → {len(urls)}")
    return urls

# 7. Danbooru — popular anime art DB (public, no auth for SFW)
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
                    if r.status != 200:
                        break
                    posts = await r.json(content_type=None)
                    if not posts:
                        break
                    for p in posts:
                        img = p.get("large_file_url") or p.get("file_url") or ""
                        if img and any(img.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp")):
                            urls.append(img)
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"[Danbooru] {e}")
            break
    print(f"[Danbooru] {tag!r} → {len(urls)}")
    return urls

# 8. Jikan/MAL pictures
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
                        if lg:
                            urls.append(lg)
    except Exception as e:
        print(f"[Jikan] {e}")
    print(f"[Jikan] → {len(urls)}")
    return urls

# 9. Kitsu
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
                if r.status != 200:
                    return []
                d = await r.json()
        for item in (d.get("data") or []):
            attrs = item.get("attributes", {})
            for key in ("coverImage", "posterImage"):
                img = attrs.get(key) or {}
                for size in ("original", "large"):
                    if img.get(size):
                        urls.append(img[size])
                        break
    except Exception as e:
        print(f"[Kitsu] {e}")
    return urls

# ══════════════════════════════════════════════════════════════════════════════
#  CHARACTER SEARCH (Jikan)
# ══════════════════════════════════════════════════════════════════════════════

async def search_character(name: str) -> dict | None:
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as s:
            async with s.get(
                "https://api.jikan.moe/v4/characters",
                params={"q": name, "limit": "1"},
                timeout=aiohttp.ClientTimeout(total=12),
            ) as r:
                if r.status != 200:
                    return None
                d = await r.json()
                results = d.get("data") or []
                if not results:
                    return None
                return results[0]
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
                        lg = item.get("jpg", {}).get("image_url") or item.get("webp", {}).get("image_url")
                        if lg:
                            urls.append(lg)
    except Exception as e:
        print(f"[CharPics] {e}")
    return urls

# ══════════════════════════════════════════════════════════════════════════════
#  ANILIST
# ══════════════════════════════════════════════════════════════════════════════

ANILIST_Q = """
query($s:String){
  Media(search:$s, type:ANIME){
    idMal
    title{ english romaji }
    genres
    description(asHtml:false)
    averageScore
    episodes
    status
    season
    seasonYear
    studios(isMain:true){ nodes{ name } }
    coverImage{ extraLarge large }
    bannerImage
    trailer{ site id }
  }
}
"""

async def fetch_anilist(name: str) -> dict | None:
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as s:
            async with s.post(
                "https://graphql.anilist.co",
                json={"query": ANILIST_Q, "variables": {"s": name}},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as r:
                if r.status != 200:
                    return None
                d = await r.json()
        return (d.get("data") or {}).get("Media")
    except Exception as e:
        print(f"[AniList] {e}")
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
        f"🎌 **{title}**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎭 **Genres:** `{genres}`\n"
        f"⭐ **Rating:** {stars(rating)} `{rating}/10`\n"
        f"📺 **Episodes:** `{eps}`\n"
        f"📡 **Status:** `{status}`\n"
        f"🗓️ **Season:** `{season}`\n"
        f"🏢 **Studio:** `{studio}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📖 **Synopsis:**\n{desc}"
        f"{trailer}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📺 **KenshinAnime** | @kenshin\\_anime"
    )

def format_char_info(char: dict) -> str:
    name     = (char.get("name") or {})
    fullname = f"{name.get('full') or name.get('first') or 'Unknown'}"
    nick     = name.get("nicknames") or []
    nick_str = f" _({', '.join(nick[:3])})_" if nick else ""
    about    = clean_desc(char.get("about") or "No info available.", 900)
    animes   = char.get("anime") or []
    anime_list = ""
    if animes:
        titles = []
        for a in animes[:5]:
            t = (a.get("anime") or {}).get("title") or {}
            titles.append(t.get("english") or t.get("romaji") or "")
        anime_list = "\n🎌 **Appears in:** " + " | ".join(filter(None, titles))
    fav = char.get("favorites") or 0
    return (
        f"👤 **{fullname}**{nick_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"❤️ **MAL Favorites:** `{fav:,}`"
        f"{anime_list}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📖 **About:**\n{about}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
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

async def send_images(msg: Message, valid_urls: list):
    """Send all images in batches of 10."""
    for i in range(0, len(valid_urls), 10):
        batch = valid_urls[i:i+10]
        if not batch:
            break
        try:
            await msg.reply_media_group([InputMediaPhoto(u) for u in batch])
            await asyncio.sleep(1.2)
        except Exception as e:
            print(f"[MediaGroup] {e}")
            for u in batch:
                try:
                    await msg.reply_photo(u)
                    await asyncio.sleep(0.5)
                except:
                    pass

def dedup(urls: list) -> list:
    seen, out = set(), []
    for u in urls:
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out

# ══════════════════════════════════════════════════════════════════════════════
#  QUERY PARSER — abbreviations + role keywords
# ══════════════════════════════════════════════════════════════════════════════

ABBR = {
    "jjk": "Jujutsu Kaisen", "aot": "Attack on Titan", "snk": "Attack on Titan",
    "bnha": "My Hero Academia", "mha": "My Hero Academia",
    "hxh": "Hunter x Hunter", "fma": "Fullmetal Alchemist Brotherhood",
    "fmab": "Fullmetal Alchemist Brotherhood",
    "op": "One Piece", "sl": "Solo Leveling", "dbs": "Dragon Ball Super",
    "dbz": "Dragon Ball Z", "kny": "Demon Slayer", "ds": "Demon Slayer",
    "tpn": "The Promised Neverland", "rezero": "Re:Zero", "re zero": "Re:Zero",
    "sao": "Sword Art Online", "cote": "Classroom of the Elite",
    "mob": "Mob Psycho 100", "mp100": "Mob Psycho 100", "opm": "One Punch Man",
    "nnt": "Seven Deadly Sins", "sds": "Seven Deadly Sins", "tg": "Tokyo Ghoul",
    "bsd": "Bungo Stray Dogs", "bc": "Black Clover",
    "vinland": "Vinland Saga", "csm": "Chainsaw Man", "cm": "Chainsaw Man",
    "jojo": "JoJo's Bizarre Adventure", "jjba": "JoJo's Bizarre Adventure",
    "nge": "Neon Genesis Evangelion", "eva": "Neon Genesis Evangelion",
    "overlord": "Overlord", "tate": "The Rising of the Shield Hero",
    "tensura": "That Time I Got Reincarnated as a Slime",
    "slime": "That Time I Got Reincarnated as a Slime",
    "konosuba": "KonoSuba", "trigun": "Trigun Stampede",
    "onk": "Oshi no Ko", "oshi no ko": "Oshi no Ko",
    "blue lock": "Blue Lock", "bocchi": "Bocchi the Rock",
    "lycoris": "Lycoris Recoil", "dr": "Dandadan",
    "danmachi": "Is It Wrong to Try to Pick Up Girls in a Dungeon",
}

ROLE_KEYWORDS = {
    "main character": "main", "main char": "main", "main chara": "main",
    "mc": "main", "protagonist": "main", "hero": "main",
    "villain": "villain", "antagonist": "villain",
    "female lead": "female_lead", "heroine": "female_lead",
    "best girl": "female_lead", "waifu": "female_lead",
}

async def get_anime_character_by_role(mal_id: int, role: str) -> dict | None:
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as s:
            async with s.get(
                f"https://api.jikan.moe/v4/anime/{mal_id}/characters",
                timeout=aiohttp.ClientTimeout(total=12),
            ) as r:
                if r.status != 200:
                    return None
                d = await r.json()
                chars = d.get("data") or []
                if not chars:
                    return None
                mains = [c for c in chars if c.get("role") == "Main"]
                supporting = [c for c in chars if c.get("role") == "Supporting"]
                if role == "villain":
                    supporting.sort(key=lambda c: c.get("favorites") or 0, reverse=True)
                    pick = supporting[0] if supporting else chars[0]
                elif role == "female_lead":
                    pick = mains[1] if len(mains) > 1 else (mains[0] if mains else chars[0])
                else:
                    mains.sort(key=lambda c: c.get("favorites") or 0, reverse=True)
                    pick = mains[0] if mains else chars[0]
                char_data = pick.get("character") or {}
                char_id = char_data.get("mal_id")
                if not char_id:
                    return None
                await asyncio.sleep(0.4)
                async with s.get(
                    f"https://api.jikan.moe/v4/characters/{char_id}",
                    timeout=aiohttp.ClientTimeout(total=12),
                ) as r2:
                    if r2.status == 200:
                        cd = await r2.json()
                        return cd.get("data")
    except Exception as e:
        print(f"[RoleChar] {e}")
    return None

def parse_query(raw: str):
    """
    Returns (anime_resolved, role, search_query)
    "jjk main character" -> ("Jujutsu Kaisen", "main", "Jujutsu Kaisen")
    "sung jinwoo"        -> (None, None, "sung jinwoo")
    "jjk"               -> ("Jujutsu Kaisen", None, "Jujutsu Kaisen")
    """
    q = raw.strip().lower()
    detected_role = None
    # Check role keywords (longest first to avoid partial match)
    for kw in sorted(ROLE_KEYWORDS.keys(), key=len, reverse=True):
        if kw in q:
            detected_role = ROLE_KEYWORDS[kw]
            q = q.replace(kw, "").strip(" ,.-")
            break
    # Resolve abbreviation (longest first)
    anime_resolved = None
    for abbr in sorted(ABBR.keys(), key=len, reverse=True):
        if q == abbr or q.startswith(abbr + " ") or q.endswith(" " + abbr) or q == abbr.replace(" ", ""):
            anime_resolved = ABBR[abbr]
            break
    clean_query = anime_resolved or raw.strip()
    return anime_resolved, detected_role, clean_query

# ══════════════════════════════════════════════════════════════════════════════
#  BOT HANDLERS
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("start") & filters.private)
async def cmd_start(_, msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return
    await msg.reply(
        "**🎌 Kenshin Anime Info Bot v5**\n\n"
        "Kuch bhi bhejo:\n"
        "• `Solo Leveling` — Anime info + 1000 images\n"
        "• `Sung Jinwoo` — Character info + images\n"
        "• `Vash the Stampede` — Character info + images\n\n"
        "**10 sources** se images milti hain:\n"
        "Wallhaven • Safebooru • Gelbooru • Konachan\n"
        "Yande.re • Zerochan • Danbooru • MAL • Kitsu • AniList\n\n"
        f"Max images: `{MAX_IMAGES}`"
    )

@app.on_message(filters.text & filters.private & ~filters.command(["start"]))
async def on_search(_, msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return

    raw_query = msg.text.strip()
    anime_resolved, detected_role, query = parse_query(raw_query)
    wait = await msg.reply(
        f"🔍 Searching **{query}**"
        + (f" → role: `{detected_role}`" if detected_role else "")
        + "..."
    )

    # ── Role-based shortcut: "jjk main character" ─────────────────────────────
    if anime_resolved and detected_role:
        # First get anime to find mal_id
        media = await fetch_anilist(anime_resolved)
        if media and media.get("idMal"):
            await wait.edit(f"👤 Fetching {detected_role} character of **{anime_resolved}**...")
            char = await get_anime_character_by_role(media["idMal"], detected_role)
            if char:
                is_char_search = True
                # Jump straight to character mode below
                char_id   = char.get("mal_id")
                char_name = (char.get("name") or {}).get("full") or query
                await wait.edit(f"👤 Found: **{char_name}** | Fetching images...")

                char_img = (char.get("images") or {}).get("jpg", {}).get("image_url") or                            (char.get("images") or {}).get("webp", {}).get("image_url")
                char_pics_task = asyncio.create_task(fetch_character_pictures(char_id)) if char_id else asyncio.create_task(asyncio.sleep(0))
                wh_t = asyncio.create_task(src_wallhaven(char_name, pages=6))
                sb_t = asyncio.create_task(src_safebooru(char_name))
                gb_t = asyncio.create_task(src_gelbooru(char_name))
                kc_t = asyncio.create_task(src_konachan(char_name))
                yd_t = asyncio.create_task(src_yandere(char_name))
                zc_t = asyncio.create_task(src_zerochan(char_name))
                db_t = asyncio.create_task(src_danbooru(char_name))
                res = await asyncio.gather(char_pics_task, wh_t, sb_t, gb_t, kc_t, yd_t, zc_t, db_t, return_exceptions=True)
                cp, wh, sb, gb, kc, yd, zc, db = [r if isinstance(r, list) else [] for r in res]
                all_urls = dedup(([char_img] if char_img else []) + cp + wh + sb + gb + kc + yd + zc + db)
                await wait.edit(f"🖼️ {len(all_urls)} images validate ho rahi hain...")
                valid_urls = []
                for i in range(0, min(len(all_urls), MAX_IMAGES), 50):
                    async with aiohttp.ClientSession(headers=HEADERS) as session:
                        rs = await asyncio.gather(*[is_valid_image(session, u) for u in all_urls[i:i+50]], return_exceptions=True)
                        for u, ok in zip(all_urls[i:i+50], rs):
                            if ok is True: valid_urls.append(u)
                    await asyncio.sleep(0.2)
                await wait.delete()
                info_text = format_char_info(char)
                if valid_urls:
                    try: await msg.reply_photo(valid_urls[0], caption=info_text)
                    except: await msg.reply(info_text)
                    await send_images(msg, valid_urls[1:])
                else:
                    await msg.reply(info_text)
                await msg.reply(f"✅ **{char_name}** — {len(valid_urls)} images bheji! 🔥")
                return

    # ── Normal parallel search ─────────────────────────────────────────────────
    anime_task = asyncio.create_task(fetch_anilist(query))
    char_task  = asyncio.create_task(search_character(query))
    results_gather = await asyncio.gather(anime_task, char_task, return_exceptions=True)
    media = results_gather[0] if isinstance(results_gather[0], dict) else None
    char  = results_gather[1] if isinstance(results_gather[1], dict) else None

    # ── Determine mode ────────────────────────────────────────────────────────
    is_char_search = False
    if char and not media:
        is_char_search = True
    elif char and media:
        char_name_str   = (char.get("name") or {}).get("full") or ""
        anime_title_str = (media.get("title") or {}).get("english") or ""
        def sim(a: str, b: str) -> int:
            a, b = a.lower(), b.lower()
            return sum(1 for w in a.split() if w in b)
        if sim(query, char_name_str) > sim(query, anime_title_str):
            is_char_search = True

    # ══════════════════════════════════════════════════════════════════════════
    #  CHARACTER MODE
    # ══════════════════════════════════════════════════════════════════════════
    if is_char_search and char:
        char_id   = char.get("mal_id")
        char_name = (char.get("name") or {}).get("full") or query
        await wait.edit(f"👤 Character mila: **{char_name}** | Images fetch ho rahi hain...")

        # Character image from MAL
        char_img = (char.get("images") or {}).get("jpg", {}).get("image_url") or \
                   (char.get("images") or {}).get("webp", {}).get("image_url")

        # Run all image sources in parallel
        char_pics_task  = asyncio.create_task(fetch_character_pictures(char_id) if char_id else asyncio.sleep(0))
        wallhaven_task  = asyncio.create_task(src_wallhaven(char_name, pages=6))
        safebooru_task  = asyncio.create_task(src_safebooru(char_name))
        gelbooru_task   = asyncio.create_task(src_gelbooru(char_name))
        konachan_task   = asyncio.create_task(src_konachan(char_name))
        yandere_task    = asyncio.create_task(src_yandere(char_name))
        zerochan_task   = asyncio.create_task(src_zerochan(char_name))
        danbooru_task   = asyncio.create_task(src_danbooru(char_name))

        results = await asyncio.gather(
            char_pics_task, wallhaven_task, safebooru_task, gelbooru_task,
            konachan_task, yandere_task, zerochan_task, danbooru_task,
            return_exceptions=True
        )
        char_pics, wh, sb, gb, kc, yd, zc, db = [
            r if isinstance(r, list) else [] for r in results
        ]

        all_urls = dedup(
            ([char_img] if char_img else []) +
            char_pics + wh + sb + gb + kc + yd + zc + db
        )

        await wait.edit(f"🖼️ {len(all_urls)} images mili! Validate ho rahi hain...")

        valid_urls = []
        check = all_urls[:MAX_IMAGES]
        batch_size = 50
        for i in range(0, len(check), batch_size):
            async with aiohttp.ClientSession(headers=HEADERS) as session:
                res = await asyncio.gather(
                    *[is_valid_image(session, u) for u in check[i:i+batch_size]],
                    return_exceptions=True
                )
                for url, ok in zip(check[i:i+batch_size], res):
                    if ok is True:
                        valid_urls.append(url)
            await asyncio.sleep(0.2)

        await wait.delete()

        info_text = format_char_info(char)
        if valid_urls:
            try:
                await msg.reply_photo(valid_urls[0], caption=info_text)
            except:
                await msg.reply(info_text)
            await send_images(msg, valid_urls[1:])
        else:
            await msg.reply(info_text)

        src_summary = (
            f"📊 **Sources for {char_name}:**\n"
            f"🖼️ Wallhaven: `{len(wh)}`\n"
            f"🎨 Safebooru: `{len(sb)}`\n"
            f"🎨 Gelbooru: `{len(gb)}`\n"
            f"🖼️ Konachan: `{len(kc)}`\n"
            f"🖼️ Yande.re: `{len(yd)}`\n"
            f"🌸 Zerochan: `{len(zc)}`\n"
            f"📌 Danbooru: `{len(db)}`\n"
            f"📺 MAL Char: `{len(char_pics)}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ **Total sent: {len(valid_urls)} images** 🔥"
        )
        await msg.reply(src_summary)
        return

    # ══════════════════════════════════════════════════════════════════════════
    #  ANIME MODE
    # ══════════════════════════════════════════════════════════════════════════
    if not media:
        await wait.edit(
            "❌ Kuch nahi mila!\n"
            "• Anime ke liye English title try kar\n"
            "• Character ke liye full name try kar\n"
            "_Example: `Solo Leveling`, `Sung Jinwoo`_"
        )
        return

    anime_title = (media.get("title") or {}).get("english") or \
                  (media.get("title") or {}).get("romaji") or query
    mal_id = media.get("idMal")
    await wait.edit(f"🎌 **{anime_title}** mila! Images fetch ho rahi hain (10 sources)...")

    # Run all sources in parallel
    wh_task  = asyncio.create_task(src_wallhaven(anime_title, pages=8))
    wh2_task = asyncio.create_task(src_wallhaven(f"{anime_title} season 2", pages=4))
    sb_task  = asyncio.create_task(src_safebooru(anime_title))
    gb_task  = asyncio.create_task(src_gelbooru(anime_title))
    kc_task  = asyncio.create_task(src_konachan(anime_title))
    yd_task  = asyncio.create_task(src_yandere(anime_title))
    zc_task  = asyncio.create_task(src_zerochan(anime_title))
    db_task  = asyncio.create_task(src_danbooru(anime_title))
    jk_task  = asyncio.create_task(src_jikan(mal_id) if mal_id else asyncio.sleep(0))
    kt_task  = asyncio.create_task(src_kitsu(query))

    results = await asyncio.gather(
        wh_task, wh2_task, sb_task, gb_task, kc_task,
        yd_task, zc_task, db_task, jk_task, kt_task,
        return_exceptions=True
    )
    wh, wh2, sb, gb, kc, yd, zc, db, jk, kt = [
        r if isinstance(r, list) else [] for r in results
    ]

    # AniList cover + banner
    cover = media.get("coverImage") or {}
    al_imgs = []
    for key in ("extraLarge", "large"):
        if cover.get(key):
            al_imgs.append(cover[key])
            break
    if media.get("bannerImage"):
        al_imgs.append(media["bannerImage"])

    all_urls = dedup(al_imgs + wh + wh2 + sb + gb + kc + yd + zc + db + jk + kt)
    total_raw = len(all_urls)

    await wait.edit(f"🖼️ {total_raw} images mili! Validate ho rahi hain...")

    valid_urls = []
    check = all_urls[:MAX_IMAGES]
    for i in range(0, len(check), 50):
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            res = await asyncio.gather(
                *[is_valid_image(session, u) for u in check[i:i+50]],
                return_exceptions=True
            )
            for url, ok in zip(check[i:i+50], res):
                if ok is True:
                    valid_urls.append(url)
        await asyncio.sleep(0.2)

    await wait.delete()

    info_text = format_anime_info(media)
    if valid_urls:
        try:
            await msg.reply_photo(valid_urls[0], caption=info_text)
        except:
            await msg.reply(info_text)
        await send_images(msg, valid_urls[1:])
    else:
        await msg.reply(info_text)
        await msg.reply("⚠️ Koi valid image nahi mili.")
        return

    src_summary = (
        f"📊 **Sources for {anime_title}:**\n"
        f"🖼️ Wallhaven: `{len(wh) + len(wh2)}`\n"
        f"🎨 Safebooru: `{len(sb)}`\n"
        f"🎨 Gelbooru: `{len(gb)}`\n"
        f"🖼️ Konachan: `{len(kc)}`\n"
        f"🖼️ Yande.re: `{len(yd)}`\n"
        f"🌸 Zerochan: `{len(zc)}`\n"
        f"📌 Danbooru: `{len(db)}`\n"
        f"📺 MAL: `{len(jk)}`\n"
        f"🌐 Kitsu: `{len(kt)}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ **Total sent: {len(valid_urls)} images** 🔥"
    )
    await msg.reply(src_summary)

# ── Entry ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 Kenshin Anime Info Bot v5 start...")
    app.run()
