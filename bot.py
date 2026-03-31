import os, asyncio
from pyrogram import Client, filters

# ── Config ────────────────────────────────────────────────────────────────────
API_ID    = int(os.environ["API_ID"])
API_HASH  = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

app = Client("kenshin_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ── Global State ──────────────────────────────────────────────────────────────
SET_STICKER = None 
VIDEO_QUEUE = []
IS_FORMATTING = False

# ══════════════════════════════════════════════════════════════════════════════
#  COMMANDS
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("setsticker") & filters.reply)
async def set_sticker_h(_, msg):
    global SET_STICKER
    if msg.reply_to_message.sticker:
        SET_STICKER = msg.reply_to_message.sticker.file_id
        await msg.reply("✅ Sticker set ho gaya! Har 3 video ke baad yahi jayega.")

@app.on_message(filters.command("format"))
async def format_h(_, msg):
    global IS_FORMATTING, VIDEO_QUEUE
    IS_FORMATTING = True
    VIDEO_QUEUE = []
    await msg.reply("📥 **Queue Start!** Ab line se videos bhejo. Bot thumbnail ko haath bhi nahi lagayega.")

@app.on_message(filters.video & filters.private)
async def collect_videos(_, msg):
    if not IS_FORMATTING: return
    # Poora message object queue mein daal rahe hain bina kisi badlav ke
    VIDEO_QUEUE.append(msg)
    await msg.reply(f"✅ Queued Video: {len(VIDEO_QUEUE)}", quote=True)

@app.on_message(filters.command("process"))
async def process_h(_, msg):
    global IS_FORMATTING, VIDEO_QUEUE
    if not VIDEO_QUEUE: 
        return await msg.reply("❌ Queue khaali hai bahi!")
    
    await msg.reply("⚙️ Sending videos exactly as received...")
    IS_FORMATTING = False
    
    count = 0
    for v_msg in VIDEO_QUEUE:
        # v_msg.copy() ka matlab hai original message ka carbon copy bhejna
        # Isse thumbnail (cover) 100% wahi rehta hai jo tune bheja tha
        await v_msg.copy(chat_id=msg.chat.id)
        count += 1
        
        # Har 3 videos ke baad sticker bhejna
        if count % 3 == 0 and SET_STICKER:
            await msg.reply_sticker(SET_STICKER)
            
        await asyncio.sleep(1.5) # Anti-flood delay

    await msg.reply(f"✅ Kaam ho gaya! Total {count} videos bhej di gayi hain.")
    VIDEO_QUEUE = []

@app.on_message(filters.command("clear"))
async def clear_h(_, msg):
    global VIDEO_QUEUE, IS_FORMATTING
    VIDEO_QUEUE = []; IS_FORMATTING = False
    await msg.reply("🗑 Queue saaf kar di gayi hai.")

if __name__ == "__main__":
    app.run()
