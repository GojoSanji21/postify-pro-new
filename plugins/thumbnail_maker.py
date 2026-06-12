import os
import aiohttp
import asyncio
import re
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageChops, ImageEnhance
import textwrap
import io
import numpy as np
import urllib.parse

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")

TEMPLATE_PATH = os.path.join(ASSETS_DIR, "template.png")
HEX_MASK_PATH = os.path.join(ASSETS_DIR, "hex_mask.png")

def clean_logo(img):
    img = img.convert("RGBA")
    if img.getextrema()[3][0] < 255:
        return img
    
    tiny = img.convert("RGB").resize((32, 32))
    for r, g, b in tiny.getdata():
        if abs(r-g) > 25 or abs(r-b) > 25:
            return img 
            
    white_img = Image.new("RGBA", img.size, (255, 255, 255, 255))
    white_img.putalpha(img.convert("L"))
    return white_img

def enhance_image(img):
    original_mode = img.mode
    has_alpha = original_mode == "RGBA" or "A" in img.getbands()

    if has_alpha:
        r, g, b, a = img.split()
        rgb_img = Image.merge("RGB", (r, g, b))
    else:
        rgb_img = img.convert("RGB")

    rgb_img = ImageEnhance.Sharpness(rgb_img).enhance(2.0)
    rgb_img = ImageEnhance.Contrast(rgb_img).enhance(1.2)
    rgb_img = ImageEnhance.Color(rgb_img).enhance(1.2)

    if has_alpha:
        r, g, b = rgb_img.split()
        return Image.merge("RGBA", (r, g, b, a))
    return rgb_img.convert("RGBA")

def apply_small_caps(text):
    if not text: return text
    normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    smallcaps = "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ"
    trans = str.maketrans(normal, smallcaps)
    return text.translate(trans)

def colorize_template_2(template_img, new_hex):
    import cv2
    arr = np.array(template_img)
    target_hex = color_hex.lstrip('#')
    new_r, new_g, new_b = tuple(int(target_hex[i:i+2], 16) for i in (0, 2, 4))
    hsv = cv2.cvtColor(arr[:,:,:3], cv2.COLOR_RGB2HSV)
    target_color_img = np.uint8([[[new_r, new_g, new_b]]])
    target_hsv = cv2.cvtColor(target_color_img, cv2.COLOR_RGB2HSV)[0][0]
    target_h = target_hsv[0]
    mask = hsv[:,:,1] > 50
    hsv[:,:,0][mask] = target_h
    arr[:,:,:3] = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
    return Image.fromarray(arr)

async def generate_poster(anime_img_url=None, custom_image_path=None, title="", genres="", synopsis="", username="", logo_url=None, crop_state=0, small_caps=False, template_url=None, color_hex="#FF6B00", template_version=1, custom_bg_path=None):
    if custom_image_path:
        anime_img = Image.open(custom_image_path).convert('RGBA')
    elif anime_img_url:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(anime_img_url, headers={'User-Agent': 'Mozilla/5.0'}) as resp:
                    anime_img = Image.open(io.BytesIO(await resp.read())).convert('RGBA')
            except:
                anime_img = Image.new('RGBA', (1920, 1080), (100, 100, 100, 255))
    else:
        anime_img = Image.new('RGBA', (1920, 1080), (100, 100, 100, 255))

    base_template_url = "https://ibb.co/N6r6n2Fp"
    base_template = None

    try:
        async with aiohttp.ClientSession() as session:
            if "ibb.co" in template_url and not template_url.endswith(('.png', '.jpg', '.jpeg')):
                async with session.get(template_url) as html_resp:
                    if html_resp.status == 200:
                        html = await html_resp.text()
                        match = re.search(r'<meta property="og:image" content="([^"]+)"', html)
                        if match:
                            template_url = match.group(1)
            async with session.get(template_url) as resp:
                if resp.status == 200:
                    base_template = Image.open(io.BytesIO(await resp.read())).convert('RGBA')
    except:
        pass

    if not base_template:
        base_template = Image.open(TEMPLATE_PATH).convert('RGBA')

    if template_version == 2 and color_hex:
        base_template = colorize_template_2(base_template, color_hex).convert('RGBA')

    if template_version == 2 and not custom_image_path:
        anime_artwork = ImageOps.fit(anime_img, base_template.size, method=Image.Resampling.LANCZOS)
        anime_artwork = enhance_image(anime_artwork)
        if custom_bg_path:
            try:
                bg_img = Image.open(custom_bg_path).convert('RGBA')
                bg_img = ImageOps.fit(bg_img, base_template.size, method=Image.Resampling.LANCZOS)
                final_img = bg_img
            except: final_img = Image.new('RGBA', base_template.size, (0, 0, 0, 255))
        else: final_img = Image.new('RGBA', base_template.size, (0, 0, 0, 255))
        final_img.paste(anime_artwork, (0, 0))
        final_img.paste(base_template, (0, 0), base_template)
    else:
        try: fetched_mask = Image.open(HEX_MASK_PATH).convert('L')
        except: fetched_mask = Image.new('L', base_template.size, 0)
        fetched_mask = fetched_mask.resize(base_template.size, Image.Resampling.LANCZOS)
        strict_mask = fetched_mask.point(lambda p: 255 if p > 128 else 0)
        expanded_mask = strict_mask.filter(ImageFilter.MaxFilter(7))
        inverse_mask = ImageOps.invert(expanded_mask)
        r, g, b, a = base_template.split()
        punched_alpha = ImageChops.darker(a, inverse_mask)
        base_template.putalpha(punched_alpha)
        blurred_bg = ImageOps.fit(anime_img, base_template.size, method=Image.Resampling.LANCZOS)
        blurred_bg = blurred_bg.filter(ImageFilter.GaussianBlur(35))
        blurred_bg = ImageEnhance.Brightness(blurred_bg).enhance(0.5)
        anime_artwork = blurred_bg.convert('RGBA')
        bbox = strict_mask.getbbox()
        if not bbox: bbox = (0, 0, 1920, 1080)
        mask_h, mask_w = bbox[3] - bbox[1], bbox[2] - bbox[0]
        v_center = 0.0 if crop_state == 1 else (1.0 if crop_state == 2 else 0.5)
        fitted = ImageOps.fit(anime_img, (mask_w, mask_h), method=Image.Resampling.LANCZOS, centering=(0.5, v_center))
        anime_artwork.paste(fitted, (bbox[0], bbox[1]))
        anime_artwork = enhance_image(anime_artwork)
        if custom_bg_path:
            try:
                bg_img = Image.open(custom_bg_path).convert('RGBA')
                bg_img = ImageOps.fit(bg_img, base_template.size, method=Image.Resampling.LANCZOS)
                final_img = bg_img
            except: final_img = Image.new('RGBA', base_template.size, (0, 0, 0, 255))
        else: final_img = Image.new('RGBA', base_template.size, (0, 0, 0, 255))
        final_img.paste(anime_artwork, (0, 0), anime_artwork)
        final_img.paste(base_template, (0, 0), base_template)

    draw = ImageDraw.Draw(final_img)

    logo_img = None
    if logo_url:
        try:
            if logo_url.startswith("http"):
                async with aiohttp.ClientSession() as session:
                    async with session.get(logo_url) as resp:
                        if resp.status == 200: logo_img = Image.open(io.BytesIO(await resp.read())).convert('RGBA')
            elif os.path.exists(logo_url): logo_img = Image.open(logo_url).convert('RGBA')
        except: pass

    genres_caps = apply_small_caps(genres.upper()) if small_caps and genres else (genres.upper() if genres else "")
    if small_caps:
        synopsis = apply_small_caps(synopsis)
        username = apply_small_caps(username)

    try:
        font_main_white = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Bold.ttf"), 85)
        font_colored_title = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Black.ttf"), 65)
        font_genres = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Medium.ttf"), 35)
        font_synopsis = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Medium.ttf"), 30)
        font_brand = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Medium.ttf"), 40)
    except:
        font_main_white = font_colored_title = font_genres = font_synopsis = font_brand = ImageFont.load_default()

    title = title.upper()
    title = re.sub(r'(?i)\bSEASON\s+(\d+)', r'S\1', title)
    title_lines = textwrap.fill(title, width=17).split('\n')
    if len(title_lines) > 2:
        title_lines = title_lines[:2]
        title_lines[1] = title_lines[1][:14] + "..." if len(title_lines[1]) > 14 else title_lines[1] + "..."

    x_offset, y_dynamic_offset = 80, 280
    font_colored_title_enlarged = font_colored_title
    for i, line in enumerate(title_lines):
        if i == 0:
            fill_color = "grey" if template_version == 2 else "white"
            draw.text((x_offset, y_dynamic_offset), line, font=font_main_white, fill=fill_color)
            y_dynamic_offset += 100
        else:
            draw.text((x_offset, y_dynamic_offset), line, font=font_colored_title_enlarged, fill=color_hex)
            y_dynamic_offset += 85

    y_dynamic_offset += 30 if template_version == 2 else 20
    draw.text((x_offset, y_dynamic_offset), genres_caps, font=font_genres, fill=color_hex)

    synopsis_dynamic_max_chars = 220 - ((len(title_lines) - 1) * 60)
    if len(synopsis) > synopsis_dynamic_max_chars:
        synopsis = synopsis[:synopsis_dynamic_max_chars].rsplit(' ', 1)[0] + "...read more"
    wrapped_synopsis = textwrap.fill(synopsis, width=45)
    y_dynamic_offset += 70 if template_version == 2 else 60
    draw.text((x_offset, y_dynamic_offset), wrapped_synopsis, font=font_synopsis, fill="#D3D3D3")

    brand_x, brand_y = 80, 60
    if logo_img:
        try:
            logo_img = clean_logo(logo_img)
            logo_img.thumbnail((95, 95), Image.Resampling.LANCZOS)
            final_img.paste(logo_img.convert('RGBA'), (brand_x, brand_y), logo_img.convert('RGBA'))
            brand_x += 115
        except: pass
    brand_color = color_hex if template_version == 2 else "white"
    draw.text((brand_x, brand_y + 15), username, font=font_brand, fill=brand_color)

    buf = io.BytesIO()
    final_img.save(buf, format='PNG')
    buf.seek(0)
    return buf

def colorize_poster_2_template(template_img, color_hex):
    import cv2
    arr = np.array(template_img)
    target_hex = color_hex.lstrip('#')
    new_r, new_g, new_b = tuple(int(target_hex[i:i+2], 16) for i in (0, 2, 4))
    hsv = cv2.cvtColor(arr[:,:,:3], cv2.COLOR_RGB2HSV)
    target_color_img = np.uint8([[[new_r, new_g, new_b]]])
    target_hsv = cv2.cvtColor(target_color_img, cv2.COLOR_RGB2HSV)[0][0]
    target_h = target_hsv[0]
    mask = hsv[:,:,1] > 50
    hsv[:,:,0][mask] = target_h
    arr[:,:,:3] = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
    return Image.fromarray(arr)

async def generate_poster_2(anime_img_url=None, custom_image_path=None, title="", genres="", synopsis="", username="", logo_url=None, crop_state=0, small_caps=False, template_url=None, color_hex="#FF6B00", offset_x=0, offset_y=0, zoom_scale=1.0):
    if custom_image_path: anime_img = Image.open(custom_image_path).convert('RGBA')
    elif anime_img_url:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(anime_img_url, headers={'User-Agent': 'Mozilla/5.0'}) as resp:
                    anime_img = Image.open(io.BytesIO(await resp.read())).convert('RGBA')
            except: anime_img = Image.new('RGBA', (1920, 1080), (100, 100, 100, 255))
    else: anime_img = Image.new('RGBA', (1920, 1080), (100, 100, 100, 255))

    base_template_url = "https://ibb.co/N6r6n2Fp"
    base_template = Image.open(os.path.join(ASSETS_DIR, "template.png")).convert('RGBA')
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(base_template_url) as resp:
                if resp.status == 200: base_template = Image.open(io.BytesIO(await resp.read())).convert('RGBA')
    except: pass

    if color_hex: base_template = colorize_poster_2_template(base_template, color_hex).convert('RGBA')

    char_w, char_h = anime_img.size
    aspect_ratio = char_w / char_h
    new_h = int(1080 * zoom_scale)
    new_w = int(new_h * aspect_ratio)

    if crop_state == 0: base_x = (1920 - new_w) // 2
    elif crop_state == 1: base_x = 1920 - new_w
    else: base_x = 0

    paste_x = base_x + offset_x
    paste_y = (1080 - new_h) // 2 + offset_y

    anime_artwork = enhance_image(anime_img.resize((new_w, new_h), Image.Resampling.LANCZOS))
    final_img = Image.new('RGBA', base_template.size, (0, 0, 0, 255))
    final_img.paste(base_template, (0, 0))
    final_img.paste(anime_artwork, (paste_x, paste_y), anime_artwork if anime_artwork.mode == 'RGBA' else None)

    draw = ImageDraw.Draw(final_img)
    buf = io.BytesIO()
    final_img.save(buf, format='PNG')
    buf.seek(0)
    return buf

# ==========================================
# POSTER 3 ULTIMATE LOGIC
# ==========================================
async def async_fetch_jikan_episodes(anime_title):
    # BULLETPROOF FALLBACK: Fetches from MAL if IMDb scraper fails
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.jikan.moe/v4/anime?q={urllib.parse.quote(anime_title)}&limit=1"
            async with session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('data'):
                        mal_id = data['data'][0]['mal_id']
                        ep_url = f"https://api.jikan.moe/v4/anime/{mal_id}/videos/episodes"
                        async with session.get(ep_url, timeout=5) as ep_resp:
                            if ep_resp.status == 200:
                                ep_data = await ep_resp.json()
                                eps = ep_data.get('data', [])
                                if len(eps) >= 2:
                                    return {
                                        "ep1_title": eps[0].get("title"),
                                        "ep1_thumb": eps[0].get("images", {}).get("jpg", {}).get("image_url"),
                                        "ep2_title": eps[1].get("title"),
                                        "ep2_thumb": eps[1].get("images", {}).get("jpg", {}).get("image_url")
                                    }
    except: pass
    return {}


async def generate_poster_3(anime_img_url=None, custom_image_path=None, title="", genres="", synopsis="", username="", logo_url=None, small_caps=False, offset_x=0, offset_y=0, zoom_scale=1.0, imdb_data=None):
    if imdb_data is None:
        imdb_data = {}

    template_path = os.path.join(ASSETS_DIR, "poster3_template_1080.png")
    if not os.path.exists(template_path):
        template_path = os.path.join(ASSETS_DIR, "poster3_template.png")
    base_template = Image.open(template_path).convert("RGBA").resize((1920, 1080), Image.Resampling.LANCZOS)

    # SECURE MASKING: Only mask the purely white empty areas, completely protecting the Heart/Stream Now icons
    template_arr = np.array(base_template)
    white_mask = (template_arr[:,:,0] >= 250) & (template_arr[:,:,1] >= 250) & (template_arr[:,:,2] >= 250)

    region_mask = np.zeros(template_arr.shape[:2], dtype=bool)
    # Fanart Box Region
    region_mask[156:696, 201:1005] = True
    
    # 🚨 CRITICAL FIX: Explicitly PROTECT the UI buttons by removing them from the mask
    # Heart Icon Region
    region_mask[160:240, 200:280] = False
    # Stream Now Button Region 
    region_mask[580:680, 210:460] = False

    # Episode Boxes
    region_mask[834:975, 201:348] = True    
    region_mask[834:975, 1032:1182] = True  

    template_arr[white_mask & region_mask, 3] = 0
    framed_template = Image.fromarray(template_arr)

    base_canvas = Image.new("RGBA", (1920, 1080), (30, 30, 30, 255))
    
    char_img = None
    try:
        if custom_image_path:
            char_img = Image.open(custom_image_path).convert("RGBA")
        elif anime_img_url:
            async with aiohttp.ClientSession() as session:
                async with session.get(anime_img_url, headers={'User-Agent': 'Mozilla/5.0'}) as resp:
                    if resp.status == 200:
                        img_data = await resp.read()
                        char_img = Image.open(io.BytesIO(img_data)).convert("RGBA")
                    else:
                        char_img = Image.new("RGBA", (800, 500), (40, 40, 40, 255))
        else:
            char_img = Image.new("RGBA", (800, 500), (40, 40, 40, 255))

        char_w, char_h = char_img.size
        box_rect = (201, 156, 1005, 696)
        box_w = box_rect[2] - box_rect[0]
        box_h = box_rect[3] - box_rect[1]

        scale = max(box_w / char_w, box_h / char_h) * zoom_scale
        new_w, new_h = int(char_w * scale), int(char_h * scale)
        scaled_char_img = char_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        paste_x = box_rect[0] + (box_w - new_w) // 2 + offset_x
        paste_y = box_rect[1] + (box_h - new_h) // 2 + offset_y

        base_canvas.paste(scaled_char_img, (paste_x, paste_y))
    except Exception as e:
        pass

    temp_draw = ImageDraw.Draw(base_template)

    try:
        font_title = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto-Black.ttf"), 65)
        font_genres = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto-Bold.ttf"), 16) # Chhota font
        font_rating = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto-Black.ttf"), 35)
        font_synopsis = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto-Regular.ttf"), 20) # Normal font
        font_brand = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto-Black.ttf"), 14) # Very small for search bar
        font_ep_title = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto-Black.ttf"), 22)
        font_ep_sub = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto-Medium.ttf"), 16)
    except:
        font_title = font_genres = font_rating = font_synopsis = font_brand = font_ep_title = font_ep_sub = ImageFont.load_default()

    disp_title = apply_small_caps(title) if small_caps else title
    title_lines = [disp_title]
    if disp_title:
        title_lines = textwrap.wrap(disp_title, width=22)
        if len(title_lines) > 2:
            title_lines = title_lines[:2]
            title_lines[1] = title_lines[1] + "..."

    if genres:
        if ',' in genres:
            genre_list = [g.strip() for g in genres.split(',')]
        else:
            genre_list = [g.strip() for g in genres.split()]
    else:
        genre_list = []

    pills = [
        (1079, 332, 169, 72),
        (1337, 334, 242, 70),
        (1598, 332, 216, 71)
    ]
    genre_draw_commands = []
    for i, g in enumerate(genre_list[:3]):
        px, py, pw, ph = pills[i]
        display_g = apply_small_caps(g) if small_caps else g
        text_bbox = temp_draw.textbbox((0, 0), display_g, font=font_genres)
        tw = text_bbox[2] - text_bbox[0]
        th = text_bbox[3] - text_bbox[1]

        # Shift text Right away from emoji
        tx = px + (pw - tw) // 2 + 35 
        ty = py + (ph - th) // 2 - 2
        genre_draw_commands.append(((tx, ty), display_g, font_genres))

    rating = str(imdb_data.get("rating", ""))
    duration = str(imdb_data.get("duration", ""))

    synopsis_draw_commands = []
    if synopsis:
        clean_synopsis = re.sub(r'<[^>]+>', '', synopsis)
        box_x = 1100 # Shifted right away from "About" text
        box_y = 640  # Shifted down
        box_w = 680 

        words = clean_synopsis.split(' ')
        lines = []
        current_line = []

        for word in words:
            current_line.append(word)
            w = temp_draw.textlength(' '.join(current_line), font=font_synopsis)
            if w > box_w:
                current_line.pop()
                lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))

        # Strict 1 line
        max_lines = 1
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            last_line = lines[-1]
            while temp_draw.textlength(last_line + "...read more", font=font_synopsis) > box_w and len(last_line) > 0:
                last_line = last_line[:-1]
            lines[-1] = last_line.strip() + "...read more"

        synopsis_draw_commands.append(((box_x, box_y), lines[0], font_synopsis))

    season_text = ""
    season_match = re.search(r'(?i)\bseason\s+(\d+)', title)
    if season_match:
        season_text = f"Season {season_match.group(1)}"
    
    season_x = 1630
    season_y = 620 # Fits strictly inside the bottom-right button

    # Fetch Jikan Data if IMDB failed
    jikan_data = {}
    if not imdb_data.get('ep1_thumb'):
        jikan_data = await async_fetch_jikan_episodes(title)

    eps = [
        {
            "title": imdb_data.get('ep1_title') or jikan_data.get('ep1_title') or "",
            "rating": imdb_data.get('ep1_rating', ""),
            "duration": imdb_data.get('ep1_duration', ""),
            "image": imdb_data.get('ep1_thumb') or jikan_data.get('ep1_thumb')
        },
        {
            "title": imdb_data.get('ep2_title') or jikan_data.get('ep2_title') or "",
            "rating": imdb_data.get('ep2_rating', ""),
            "duration": imdb_data.get('ep2_duration', ""),
            "image": imdb_data.get('ep2_thumb') or jikan_data.get('ep2_thumb')
        }
    ]
    
    ep_coords = [
        {
            "box": (201, 834, 348, 975),
            "title_pos": (450, 845),
            "rating_pos": (465, 915),
            "duration_pos": (565, 915) 
        },
        {
            "box": (1032, 834, 1182, 975),
            "title_pos": (1280, 845),
            "rating_pos": (1290, 915),
            "duration_pos": (1390, 915) 
        }
    ]

    ep_draw_commands = []
    for i, ep_info in enumerate(ep_coords):
        if i < len(eps):
            ep = eps[i]

            ep_title_text = f"{ep['title']}"
            words = ep_title_text.split()
            # Strict 3-4 words limit for episode title
            if len(words) > 4:
                ep_title_text = " ".join(words[:4]) + "..."
            
            if ep_title_text:
                ep_draw_commands.append((ep_info["title_pos"], ep_title_text, font_ep_title_small))

            if ep['rating'] and ep['rating'] != "N/A":
                ep_draw_commands.append((ep_info["rating_pos"], f"{ep['rating']}", font_ep_sub_tiny))
            if ep['duration'] and ep['duration'] != "N/A":
                ep_draw_commands.append((ep_info["duration_pos"], f"{ep['duration'].replace(' min', '')}", font_ep_sub_tiny))

            thumb_img = None
            if ep.get("image"):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(ep["image"], headers={'User-Agent': 'Mozilla/5.0'}) as resp:
                            if resp.status == 200:
                                img_data = await resp.read()
                                thumb_img = Image.open(io.BytesIO(img_data)).convert("RGBA")
                except:
                    pass

            # IF NO IMAGE, LEAVE IT AS CLEAN DARK GREY BOX
            if not thumb_img:
                thumb_img = Image.new("RGBA", (200, 200), (60, 60, 60, 255))

            try:
                box_rect = ep_info["box"]
                box_w = box_rect[2] - box_rect[0]
                box_h = box_rect[3] - box_rect[1]

                img_w, img_h = thumb_img.size
                scale = max(box_w / img_w, box_h / img_h)
                new_w, new_h = int(img_w * scale), int(img_h * scale)
                thumb_img = thumb_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                left = (new_w - box_w) // 2
                top = (new_h - box_h) // 2
                thumb_img = thumb_img.crop((left, top, left + box_w, top + box_h))

                base_canvas.paste(thumb_img, (box_rect[0], box_rect[1]))
            except:
                pass

    base = Image.alpha_composite(base_canvas, framed_template)
    draw = ImageDraw.Draw(base)

    if disp_title:
        title_y = 145
        for line in title_lines:
            draw.text((1125, title_y), line, font=font_title, fill=(255, 255, 255, 255), anchor="la")
            title_y += 75

    for pos, text, font in genre_draw_commands:
        draw.text(pos, text, font=font, fill=(255, 255, 255, 255), anchor="la")

    if rating and rating != "N/A":
        draw.text((1140, 495), rating, font=font_rating, fill=(255, 255, 255, 255), anchor="la")
    if duration and duration != "N/A":
        draw.text((1420, 495), duration.replace(" min", ""), font=font_rating, fill=(255, 255, 255, 255), anchor="la")

    for pos, text, font in synopsis_draw_commands:
        draw.text(pos, text, font=font, fill=(180, 180, 180, 255), anchor="la")

    if season_text:
        draw.text((season_x, season_y), season_text, font=font_synopsis, fill=(255, 255, 255, 255), anchor="mm")

    for pos, text, font in ep_draw_commands:
        draw.text(pos, text, font=font, fill=(255, 255, 255, 255), anchor="la")

    disp_username = apply_small_caps(username) if small_caps else username
    if disp_username:
        # Shrink to 14, position perfectly inside the search bar (X=190)
        try:
            font_brand_small = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto-Black.ttf"), 14)
        except:
            font_brand_small = font_brand
        
        draw.text((190, 56), disp_username, font=font_brand_small, fill=(180, 180, 180, 255), anchor="lm")

    if logo_url:
        try:
            if logo_url.startswith("http"):
                async with aiohttp.ClientSession() as session:
                    async with session.get(logo_url) as resp:
                        if resp.status == 200:
                            l_data = await resp.read()
                            logo_img = Image.open(io.BytesIO(l_data)).convert("RGBA")
            else:
                logo_img = Image.open(logo_url).convert("RGBA")

            logo_img.thumbnail((96, 96), Image.Resampling.LANCZOS)
            lw, lh = logo_img.size
            lx = 1794 + (96 - lw) // 2
            ly = 9 + (96 - lh) // 2

            mask = Image.new("L", (lw, lh), 0)
            d_mask = ImageDraw.Draw(mask)
            d_mask.ellipse((0, 0, lw, lh), fill=255)

            base.paste(logo_img, (lx, ly), mask)
        except Exception as e:
            pass

    base = enhance_image(base)

    out_bio = io.BytesIO()
    base.convert("RGB").save(out_bio, format="JPEG", quality=95)
    out_bio.name = "poster3.jpg"
    out_bio.seek(0)
    return out_bio
