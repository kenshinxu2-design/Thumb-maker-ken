import os, asyncio
from pyrogram import Client, filters

# ── Config ────────────────────────────────────────────────────────────────────
API_ID    = int(os.environ["API_ID"])
API_HASH  = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_IDS = list(map(int, os.environ.get("ADMIN_IDS", "").split(",")))

app = Client("kenshin_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ── Global State ──────────────────────────────────────────────────────────────
SET_STICKER = None 
VIDEO_QUEUE = []
IS_FORMATTING = False

# ══════════════════════════════════════════════════════════════════════════════
#  COMMANDS
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("start") & filters.private)
async def start_cmd(_, msg):
    await msg.reply("🔥 **Bot Ready!**\n\n1. `/setsticker` (Sticker pe reply karo)\n2. `/format` (Queue shuru)\n3. `/process` (Send videos)")

@app.on_message(filters.command("setsticker") & filters.reply)
async def set_sticker_h(_, msg):
    global SET_STICKER
    if msg.reply_to_message.sticker:
        SET_STICKER = msg.reply_to_message.sticker.file_id
        await msg.reply("✅ Sticker set ho gaya!")
    else:
        await msg.reply("❌ Sticker par reply karo.")

@app.on_message(filters.command("format"))
async def format_h(_, msg):
    global IS_FORMATTING, VIDEO_QUEUE
    IS_FORMATTING = True
    VIDEO_QUEUE = []
    await msg.reply("📥 **Queue ON!** Videos bhejo (1, 2, 3...)")

@app.on_message(filters.video & filters.private)
async def collect_videos(_, msg):
    if not IS_FORMATTING: return
    VIDEO_QUEUE.append(msg)
    await msg.reply(f"✅ Queued: Video {len(VIDEO_QUEUE)}", quote=True)

@app.on_message(filters.command("process"))
async def process_h(_, msg):
    global IS_FORMATTING, VIDEO_QUEUE
    if not VIDEO_QUEUE: 
        return await msg.reply("❌ Queue khaali hai!")
    
    st_msg = await msg.reply("⚙️ Sending videos...")
    IS_FORMATTING = False
    
    count = 0
    for v_msg in VIDEO_QUEUE:
        # Bina kisi change ke seedha forward/copy
        await v_msg.copy(chat_id=msg.chat.id)
        count += 1
        
        # Har 3 videos ke baad sticker
        if count % 3 == 0:
            if SET_STICKER:
                await msg.reply_sticker(SET_STICKER)
            await asyncio.sleep(1) # Flood wait safety
            
        await asyncio.sleep(1.5)

    await st_msg.edit(f"✅ Done! Total {count} videos sent.")
    VIDEO_QUEUE = []

@app.on_message(filters.command("clear"))
async def clear_h(_, msg):
    global VIDEO_QUEUE, IS_FORMATTING
    VIDEO_QUEUE = []
    IS_FORMATTING = False
    await msg.reply("🗑 Queue cleared.")

if __name__ == "__main__":
    app.run()
