# bot.py (Version 2.0 - Kenshin God Maker)

import os
import asyncio
from time import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

# --- Configuration (Set these in Railway for safety) ---
API_ID = os.environ.get("API_ID") 
API_HASH = os.environ.get("API_HASH") 
BOT_TOKEN = os.environ.get("BOT_TOKEN") 
ADMIN_ID = os.environ.get("ADMIN_ID") # Sirf tumhara ID, no quotes. E.g., 12345678

# Essential Check
if not ADMIN_ID:
    print("CRITICAL ERROR: ADMIN_ID not set! Bot will not respond to anyone.")
    exit(1)

app = Client("kenshin_maker", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# States Management - Admin ID mapping to current data
session_state = {}

# Layout/Color Constants
CANVAS_WIDTH = 1280
CANVAS_HEIGHT = 720
BRANDING_YELLOW = "#FFD700"
DARK_GRAY = "#222222"
LIGHT_GRAY = "#DDDDDD"

# Font Settings (Make sure fonts are in the 'fonts/' folder)
FONT_TITLE_PATH = "fonts/font.ttf" # Original Title font
FONT_BOLD_PATH = "fonts/DejaVuSansCondensed-Bold.ttf" # Branding font

# --- Helper Functions ---

def is_admin(user_id):
    return str(user_id) == str(ADMIN_ID)

def get_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        print(f"Font not found at {path}, using default.")
        return ImageFont.load_default()

def draw_rounded_rect(draw, pos, size, radius, color):
    x, y = pos
    w, h = size
    draw.rounded_rectangle([(x, y), (x + w, y + h)], radius, fill=color)

# Function to clear state on finish/cancel
def clear_session(admin_id):
    data = session_state.get(admin_id)
    if data and data.get("temp_files"):
        for file in data["temp_files"]:
            if file and os.path.exists(file):
                os.remove(file)
    session_state.pop(admin_id, None)


# ==========================================
# =         IMAGE GENERATION STYLES        =
# ==========================================

# Style 1: Fixed Original (Narrowed Left Panel)
# Needs: Name, BG Image, Left Char Image, Right Visual Image
def create_style_1(name, bg_path, left_path, right_path, admin_id):
    print("Starting creation: Style 1...")
    
    # 1. Base Canvas
    canvas = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 255))
    draw = ImageDraw.Draw(canvas)

    # 2. Background Image (Scaled, Tinted)
    bg_img = Image.open(bg_path).convert("RGBA")
    bg_img = bg_img.resize((CANVAS_WIDTH, CANVAS_HEIGHT), Image.Resampling.LANCZOS)
    bg_tinted = ImageOps.colorize(bg_img.convert("L"), black="black", white="#AAAAAA") 
    canvas.paste(bg_tinted, (0, 0))

    # 3. FIXED: Left Character Panel (Narrowed for better aspect)
    # New Size: 240 width instead of 300
    LEFT_PANEL_SIZE = (240, 660)
    LEFT_PANEL_POS = (40, 30) # Moved slightly right
    
    left_mask = Image.new("L", LEFT_PANEL_SIZE, 0)
    ImageDraw.Draw(left_mask).rounded_rectangle([(0, 0), LEFT_PANEL_SIZE], 15, fill=255)
    
    left_img = Image.open(left_path).convert("RGBA").resize(LEFT_PANEL_SIZE, Image.Resampling.LANCZOS)
    rounded_left = Image.new("RGBA", LEFT_PANEL_SIZE)
    rounded_left.paste(left_img, (0, 0), left_mask)
    canvas.paste(rounded_left, LEFT_PANEL_POS, rounded_left)

    # 4. Right Thumbnail Image (Shifted Left because left panel is narrower)
    RIGHT_POS = (310, 30)
    RIGHT_SIZE = (930, 520) # Adjusted size
    
    right_img = Image.open(right_path).convert("RGBA").resize(RIGHT_SIZE, Image.Resampling.LANCZOS)
    canvas.paste(right_img, RIGHT_POS, right_img)
    
    # Overlay for text contrast
    right_overlay = Image.new("RGBA", RIGHT_SIZE, (0, 0, 0, 150))
    canvas.paste(right_overlay, RIGHT_POS, right_overlay)

    # 5. Text & Buttons (Branding updated)
    font_title = get_font(FONT_TITLE_PATH, 45)
    font_bold = get_font(FONT_BOLD_PATH, 30)
    
    # Anime Title
    draw.text((310, 50), name.upper(), font=font_title, fill="white")
    
    # "KENSHIN ANIME" branding (yellow bold)
    draw.text((310, 120), "KENSHIN ANIME", font=font_bold, fill=BRANDING_YELLOW)

    # Bottom Buttons (Branding updated)
    btn_size = (280, 60)
    btn_y = 610
    
    # Left button (Watch Now)
    draw_rounded_rect(draw, (310, btn_y), btn_size, 8, DARK_GRAY)
    
    # Right button (KENSHIN ANIME - Now static branding)
    draw_rounded_rect(draw, (620, btn_y), btn_size, 8, DARK_GRAY)
    
    # Center Button Text
    draw.text((310 + 60, btn_y + 15), "Watch Now", font=font_bold, fill="white")
    draw.text((620 + 35, btn_y + 15), "KENSHIN ANIME", font=font_bold, fill="white")

    output_path = f"kenshin_s1_{int(time())}.png"
    canvas.save(output_path, "PNG")
    return output_path


# Style 2: Split Visual (Tall Left, Visual Right Still)
# Needs: Name, Ep Number, Left Char Image, Right Ep Still Image
def create_style_2(name, ep_num, left_path, right_path, admin_id):
    print("Starting creation: Style 2...")
    
    canvas = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (15, 15, 15, 255)) # Almost black
    draw = ImageDraw.Draw(canvas)
    
    # 1. Left Character (Full height fill)
    LEFT_SIZE = (500, 720) # Increased width
    left_img = Image.open(left_path).convert("RGBA").resize(LEFT_SIZE, Image.Resampling.LANCZOS)
    canvas.paste(left_img, (0, 0))
    
    # Small divider shadow
    shadow = Image.new("RGBA", (20, 720), (0, 0, 0, 150))
    canvas.paste(shadow, (500, 0), shadow)

    # 2. Right Text Area
    TEXT_AREA_POS = (530, 0)
    
    font_title = get_font(FONT_TITLE_PATH, 65)
    font_bold = get_font(FONT_BOLD_PATH, 35)
    font_bold_small = get_font(FONT_BOLD_PATH, 28)

    # Anime Title
    draw.text((530, 40), name.upper(), font=font_title, fill="white")
    
    # Branding Subtitle
    draw.text((530, 120), "KENSHIN ANIME", font=font_bold, fill=BRANDING_YELLOW)
    
    # Ep Number branding
    draw.text((530, 180), f"EP. {ep_num}", font=font_bold_small, fill=LIGHT_GRAY)
    
    # 3. Right Visual Image (Episode still, with rounded corners)
    RIGHT_IMG_POS = (530, 260)
    RIGHT_IMG_SIZE = (720, 430)
    
    mask = Image.new("L", RIGHT_IMG_SIZE, 0)
    ImageDraw.Draw(mask).rounded_rectangle([(0, 0), RIGHT_IMG_SIZE], 20, fill=255)
    
    right_img = Image.open(right_path).convert("RGBA").resize(RIGHT_IMG_SIZE, Image.Resampling.LANCZOS)
    rounded_right = Image.new("RGBA", RIGHT_IMG_SIZE)
    rounded_right.paste(right_img, (0, 0), mask)
    canvas.paste(rounded_right, RIGHT_IMG_POS, rounded_right)

    output_path = f"kenshin_s2_{int(time())}.png"
    canvas.save(output_path, "PNG")
    return output_path


# Style 3: Cinematic Typography
# Needs: Name, Ep Number, Single Background Scene Image
def create_style_3(name, ep_num, bg_path, admin_id):
    print("Starting creation: Style 3...")
    
    # 1. Base Image
    bg_img = Image.open(bg_path).convert("RGBA")
    
    # Fix portrait images to fill landscape correctly
    if bg_img.height > bg_img.width:
        bg_img = ImageOps.fit(bg_img, (CANVAS_WIDTH, CANVAS_HEIGHT), Image.Resampling.LANCZOS)
    else:
        bg_img = bg_img.resize((CANVAS_WIDTH, CANVAS_HEIGHT), Image.Resampling.LANCZOS)
        
    canvas = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 255))
    canvas.paste(bg_img, (0, 0))
    draw = ImageDraw.Draw(canvas)
    
    # 2. Overlay Gradients (Heavy bottom for legibility)
    bottom_overlay = Image.new("RGBA", (CANVAS_WIDTH, 200), (0, 0, 0, 200))
    canvas.paste(bottom_overlay, (0, 520), bottom_overlay)
    
    # Text overlay contrast
    text_overlay = Image.new("RGBA", (CANVAS_WIDTH, 400), (0, 0, 0, 80)) # Subtle darken behind text
    canvas.paste(text_overlay, (0, 160), text_overlay)

    # 3. Massive Typography (Centered)
    font_massive = get_font(FONT_TITLE_PATH, 110)
    font_bold = get_font(FONT_BOLD_PATH, 40)
    font_bold_small = get_font(FONT_BOLD_PATH, 30)
    
    # Center Name
    name_text = name.upper()
    bbox_n = draw.textbbox((0, 0), name_text, font=font_massive)
    text_n_w = bbox_n[2] - bbox_n[0]
    draw.text(((CANVAS_WIDTH - text_n_w) // 2, 280), name_text, font=font_massive, fill="white")
    
    # Center EP Number Subtitle
    ep_text = f"Episode {ep_num}"
    bbox_e = draw.textbbox((0, 0), ep_text, font=font_bold)
    text_e_w = bbox_e[2] - bbox_e[0]
    draw.text(((CANVAS_WIDTH - text_e_w) // 2, 400), ep_text, font=font_bold, fill=LIGHT_GRAY)
    
    # 4. Cinematic "KENSHIN ANIME" branding (Small at very bottom center)
    brand_text = "KENSHIN ANIME"
    bbox_b = draw.textbbox((0, 0), brand_text, font=font_bold_small)
    text_b_w = bbox_b[2] - bbox_b[0]
    draw.text(((CANVAS_WIDTH - text_b_w) // 2, 650), brand_text, font=font_bold_small, fill=LIGHT_GRAY)

    output_path = f"kenshin_s3_{int(time())}.png"
    canvas.save(output_path, "PNG")
    return output_path


# ==========================================
# =           TELEGRAM BOT LOGIC           =
# ==========================================

# State constants
STATE_S1_GET_NAME = "s1_get_name"
STATE_S1_GET_BG = "s1_get_bg"
STATE_S1_GET_LEFT = "s1_get_left"
STATE_S1_GET_RIGHT = "s1_get_right"

STATE_S2_GET_NAME = "s2_get_name"
STATE_S2_GET_EP_NUM = "s2_get_ep_num"
STATE_S2_GET_LEFT = "s2_get_left"
STATE_S2_GET_RIGHT = "s2_get_right"

STATE_S3_GET_NAME = "s3_get_name"
STATE_S3_GET_EP_NUM = "s3_get_ep_num"
STATE_S3_GET_BG = "s3_get_bg"


@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply("Only Kenshin Admin can use this bot.")
    
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Style 1 (Original Fixed)", callback_data="style_1")],
            [InlineKeyboardButton("Style 2 (Split Panel)", callback_data="style_2")],
            [InlineKeyboardButton("Style 3 (Cinematic Typography)", callback_data="style_3")],
            [InlineKeyboardButton("❌ Cancel Session", callback_data="cancel")],
        ]
    )
    
    await message.reply(
        "**KENSHIN ANIME God Maker Version 2.0**\n\nBhai style select kar:",
        reply_markup=keyboard
    )

@app.on_callback_query()
async def callback_handler(client, callback_query: CallbackQuery):
    admin_id = callback_query.from_user.id
    if not is_admin(admin_id): return
    
    command = callback_query.data
    
    await callback_query.message.delete()
    
    if command == "cancel":
        clear_session(admin_id)
        return await client.send_message(admin_id, "❌ Session cancelled.")
        
    # Start different creation flows
    if command == "style_1":
        session_state[admin_id] = {"step": STATE_S1_GET_NAME, "temp_files": []}
        await client.send_message(admin_id, "**Style 1 (Original Fixed)**\n\nSend me the **Anime Name**.")
        
    elif command == "style_2":
        session_state[admin_id] = {"step": STATE_S2_GET_NAME, "temp_files": []}
        await client.send_message(admin_id, "**Style 2 (Split Panel)**\n\nSend me the **Anime Name**.")
        
    elif command == "style_3":
        session_state[admin_id] = {"step": STATE_S3_GET_NAME, "temp_files": []}
        await client.send_message(admin_id, "**Style 3 (Cinematic)**\n\nSend me the **Anime Name**.")


# Handle Text Inputs (Name, EP Numbers)
@app.on_message(filters.text & filters.private & ~filters.command("start"))
async def text_handler(client, message: Message):
    admin_id = message.from_user.id
    if not is_admin(admin_id): return
    
    data = session_state.get(admin_id)
    if not data: return await message.reply("Bhai phle /start daba kar style select kar.")
    
    step = data.get("step")
    text = message.text.strip()
    
    # Flow 1 Handlers
    if step == STATE_S1_GET_NAME:
        session_state[admin_id]["anime_name"] = text
        session_state[admin_id]["step"] = STATE_S1_GET_BG
        await message.reply("Name saved.\n\nAb **Background Image** send kar.")

    # Flow 2 Handlers
    elif step == STATE_S2_GET_NAME:
        session_state[admin_id]["anime_name"] = text
        session_state[admin_id]["step"] = STATE_S2_GET_EP_NUM
        await message.reply("Name saved.\n\nAb **Episode Number** send kar.")
    elif step == STATE_S2_GET_EP_NUM:
        session_state[admin_id]["ep_num"] = text
        session_state[admin_id]["step"] = STATE_S2_GET_LEFT
        await message.reply(f"Ep {text} saved.\n\nAb **Left Character Image** send kar.")

    # Flow 3 Handlers
    elif step == STATE_S3_GET_NAME:
        session_state[admin_id]["anime_name"] = text
        session_state[admin_id]["step"] = STATE_S3_GET_EP_NUM
        await message.reply("Name saved.\n\nAb **Episode Number** send kar.")
    elif step == STATE_S3_GET_EP_NUM:
        session_state[admin_id]["ep_num"] = text
        session_state[admin_id]["step"] = STATE_S3_GET_BG
        await message.reply(f"Ep {text} saved.\n\nAb single landscape **Background Scene Image** send kar.")


# Handle Image Inputs (Photo)
@app.on_message(filters.photo & filters.private)
async def photo_handler(client, message: Message):
    admin_id = message.from_user.id
    if not is_admin(admin_id): return
    
    data = session_state.get(admin_id)
    if not data: return await message.reply("Bhai phle command send kar name or numbers collect karne de.")
    
    step = data.get("step")
    msg = await message.reply("Downloading image...")
    file_path = await message.download()
    
    # Store temporary file for cleanup later
    if not data.get("temp_files"): session_state[admin_id]["temp_files"] = []
    session_state[admin_id]["temp_files"].append(file_path)
    
    try:
        # Style 1 Image Collection Flow
        if step == STATE_S1_GET_BG:
            session_state[admin_id]["bg_path"] = file_path
            session_state[admin_id]["step"] = STATE_S1_GET_LEFT
            await msg.edit("Done! Background recived.\n\nAb **Left Character Image** send kar (Tall portrait/render).")
        elif step == STATE_S1_GET_LEFT:
            session_state[admin_id]["left_path"] = file_path
            session_state[admin_id]["step"] = STATE_S1_GET_RIGHT
            await msg.edit("Done! Left Image recived.\n\nAb **Right Visual Image** send kar (Anime key visual/still).")
        elif step == STATE_S1_GET_RIGHT:
            await msg.edit("Done! All inputs received. God Maker starting...")
            
            # Create final output
            final_path = create_style_1(
                data["anime_name"], 
                data["bg_path"], 
                data["left_path"], 
                file_path, # Right path
                admin_id
            )
            
            # Send result
            await client.send_photo(admin_id, final_path, caption=f"**{data['anime_name']}** fixed Style 1 thumbnail tayar hai, Kenshin.")
            
            # Cleanup
            if os.path.exists(final_path): os.remove(final_path)
            clear_session(admin_id)

        # Style 2 Image Collection Flow
        elif step == STATE_S2_GET_LEFT:
            session_state[admin_id]["left_path"] = file_path
            session_state[admin_id]["step"] = STATE_S2_GET_RIGHT
            await msg.edit("Done! Left Image recived.\n\nAb **Right Episode Still Image** send kar.")
        elif step == STATE_S2_GET_RIGHT:
            await msg.edit("Done! All inputs received. God Maker starting...")
            
            # Create final output
            final_path = create_style_2(
                data["anime_name"],
                data["ep_num"], 
                data["left_path"], 
                file_path, # Right path
                admin_id
            )
            
            # Send result
            await client.send_photo(admin_id, final_path, caption=f"**{data['anime_name']}** Style 2 thumbnail tayar hai, Kenshin.")
            
            # Cleanup
            if os.path.exists(final_path): os.remove(final_path)
            clear_session(admin_id)

        # Style 3 Image Collection Flow
        elif step == STATE_S3_GET_BG:
            await msg.edit("Done! Background Scene received. God Maker starting...")
            
            # Create final output
            final_path = create_style_3(
                data["anime_name"], 
                data["ep_num"], 
                file_path, # BG path
                admin_id
            )
            
            # Send result
            await client.send_photo(admin_id, final_path, caption=f"**{data['anime_name']}** Cinematic Style 3 thumbnail tayar hai, Kenshin.")
            
            # Cleanup
            if os.path.exists(final_path): os.remove(final_path)
            clear_session(admin_id)

    except Exception as e:
        await client.send_message(admin_id, f"ERROR Creation mein issue: {e}")
        clear_session(admin_id)

if __name__ == "__main__":
    print("Bot is running...")
    app.run()
