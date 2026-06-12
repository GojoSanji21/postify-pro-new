import os
import aiohttp
import asyncio
import re
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageChops, ImageEnhance
import textwrap
import io
import numpy as np

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
    import numpy as np
    arr = np.array(template_img)
    target_hex = new_hex.lstrip('#')
    new_r, new_g, new_b = tuple(int(target_hex[i:i+2], 16) for i in (0, 2, 4))

    max_c = np.max(arr[:,:,:3], axis=2)
    min_c = np.min(arr[:,:,:3], axis=2)
    saturation = max_c - min_c

    mask = saturation > 30

    arr[:,:,0][mask] = new_r
    arr[:,:,1][mask] = new_g
    arr[:,:,2][mask] = new_b

    return Image.fromarray(arr)

async def generate_poster(anime_img_url=None, custom_image_path=None, title="", genres="", synopsis="", username="", logo_url=None, crop_state=0, small_caps=False, template_url=None, color_hex="#FF6B00", template_version=1, custom_bg_path=None):
    if custom_image_path:
        anime_img = Image.open(custom_image_path).convert('RGBA')
    elif anime_img_url:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(anime_img_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}) as resp:
                    anime_img_data = await resp.read()
                    anime_img = Image.open(io.BytesIO(anime_img_data)).convert('RGBA')
            except Exception:
                anime_img = Image.new('RGBA', (1920, 1080), (100, 100, 100, 255))
    else:
        anime_img = Image.new('RGBA', (1920, 1080), (100, 100, 100, 255))

    base_template = None
    if template_url and template_url.startswith("http"):
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
                        template_data = await resp.read()
                        base_template = Image.open(io.BytesIO(template_data)).convert('RGBA')
        except Exception:
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
            except:
                final_img = Image.new('RGBA', base_template.size, (0, 0, 0, 255))
        else:
            final_img = Image.new('RGBA', base_template.size, (0, 0, 0, 255))
        final_img.paste(anime_artwork, (0, 0))
        final_img.paste(base_template, (0, 0), base_template)
    else:
        try:
            fetched_mask = Image.open(HEX_MASK_PATH).convert('L')
        except:
            fetched_mask = Image.new('L', base_template.size, 0)
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
            except:
                final_img = Image.new('RGBA', base_template.size, (0, 0, 0, 255))
        else:
            final_img = Image.new('RGBA', base_template.size, (0, 0, 0, 255))
        final_img.paste(anime_artwork, (0, 0), anime_artwork)
        final_img.paste(base_template, (0, 0), base_template)

    draw = ImageDraw.Draw(final_img)

    logo_img = None
    if logo_url:
        try:
            if logo_url.startswith("http"):
                async with aiohttp.ClientSession() as session:
                    async with session.get(logo_url) as resp:
                        if resp.status == 200:
                            logo_data = await resp.read()
                            logo_img = Image.open(io.BytesIO(logo_data)).convert('RGBA')
            elif os.path.exists(logo_url): logo_img = Image.open(logo_url).convert('RGBA')
        except: pass

    genres_caps = genres.upper() if genres else ""
    if small_caps:
        genres_caps = apply_small_caps(genres_caps)
        synopsis = apply_small_caps(synopsis)
        username = apply_small_caps(username)

    try:
        font_main_white = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Bold.ttf"), 85)
        font_colored_title = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Black.ttf"), 65)
    except:
        font_main_white = font_colored_title = ImageFont.load_default()

    try:
        font_genres = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Medium.ttf"), 35)
        font_synopsis = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Medium.ttf"), 30)
        font_brand = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Medium.ttf"), 40)
    except:
        font_genres = font_synopsis = font_brand = ImageFont.load_default()

    title = title.upper()
    title = re.sub(r'(?i)\bSEASON\s+(\d+)', r'S\1', title)
    wrapped_title = textwrap.fill(title, width=17)
    title_lines = wrapped_title.split('\n')
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
    if custom_image_path:
        anime_img = Image.open(custom_image_path).convert('RGBA')
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

    base_x = (1920 - new_w) // 2 if crop_state == 0 else (1920 - new_w if crop_state == 1 else 0)
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
# CROP & PASTE HELPER (Prevents image bleeding/peeping)
# ==========================================
def paste_with_crop(canvas, img, box, ox, oy, zoom):
    bw = box[2] - box[0]
    bh = box[3] - box[1]
    iw, ih = img.size
    scale = max(bw / iw, bh / ih) * zoom
    nw, nh = int(iw * scale), int(ih * scale)
    resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
    
    temp_box = Image.new("RGBA", (bw, bh), (0,0,0,0))
    px = (bw - nw) // 2 + ox
    py = (bh - nh) // 2 + oy
    temp_box.paste(resized, (px, py))
    canvas.paste(temp_box, (box[0], box[1]), temp_box)

# ==========================================
# POSTER 3 ULTIMATE LOGIC
# ==========================================
async def generate_poster_3(anime_img_url=None, custom_image_path=None, title="", genres="", synopsis="", username="", logo_url=None, small_caps=False, offset_x=0, offset_y=0, zoom_scale=1.0, imdb_data=None, custom_ep1_path=None, custom_ep2_path=None, ep1_offset_x=0, ep1_offset_y=0, ep1_zoom=1.0, ep2_offset_x=0, ep2_offset_y=0, ep2_zoom=1.0):
    if imdb_data is None: imdb_data = {}

    template_path = os.path.join(ASSETS_DIR, "poster3_template_1080.png")
    if not os.path.exists(template_path):
        template_path = os.path.join(ASSETS_DIR, "poster3_template.png")
    base_template = Image.open(template_path).convert("RGBA").resize((1920, 1080), Image.Resampling.LANCZOS)

    # SECURE MASKING: Only clear out the pure white backgrounds (leaves Heart & Stream borders perfect)
    template_arr = np.array(base_template)
    white_mask = (template_arr[:,:,0] >= 240) & (template_arr[:,:,1] >= 240) & (template_arr[:,:,2] >= 240)

    region_mask = np.zeros(template_arr.shape[:2], dtype=bool)
    region_mask[156:696, 201:1005] = True   # Main Fanart 
    region_mask[834:975, 201:348] = True    # Ep 1
    region_mask[834:975, 1032:1182] = True  # Ep 2

    # Clean the white blocks out completely
    template_arr[white_mask & region_mask, 3] = 0
    framed_template = Image.fromarray(template_arr)

    # This is the bottom layer where we paste the fanart and episodes
    base_canvas = Image.new("RGBA", (1920, 1080), (30, 30, 30, 255))
    
    try:
        if custom_image_path: char_img = Image.open(custom_image_path).convert("RGBA")
        elif anime_img_url:
            async with aiohttp.ClientSession() as session:
                async with session.get(anime_img_url, headers={'User-Agent': 'Mozilla/5.0'}) as resp:
                    if resp.status == 200: char_img = Image.open(io.BytesIO(await resp.read())).convert("RGBA")
                    else: char_img = Image.new("RGBA", (800, 500), (40, 40, 40, 255))
        else: char_img = Image.new("RGBA", (800, 500), (40, 40, 40, 255))
        
        # Paste Main Fanart with precise boundary protection
        paste_with_crop(base_canvas, char_img, (201, 156, 1005, 696), offset_x, offset_y, zoom_scale)
    except Exception:
        pass

    temp_draw = ImageDraw.Draw(base_template)

    try:
        font_title = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Black.ttf"), 65)
        font_rating = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Black.ttf"), 40) # Rating bada kiya
        font_brand_small = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Black.ttf"), 20) # Anime Fury bada kiya
        font_ep_title = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Black.ttf"), 24) # Ep title bada kiya
        font_season = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Black.ttf"), 22) # Season text
    except:
        font_title = font_rating = font_brand_small = font_ep_title = font_season = ImageFont.load_default()

    try:
        font_genres = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Bold.ttf"), 20) # Genres bada kiya
        font_synopsis = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Medium.ttf"), 20)
        font_ep_sub = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Medium.ttf"), 16)
    except:
        font_genres = font_synopsis = font_ep_sub = ImageFont.load_default()

    disp_title = apply_small_caps(title) if small_caps else title
    title_lines = [disp_title] if disp_title else [""]
    if disp_title:
        title_lines = textwrap.wrap(disp_title, width=22)
        if len(title_lines) > 2:
            title_lines = title_lines[:2]
            title_lines[1] = title_lines[1] + "..."

    genre_list = [g.strip() for g in genres.split(',')] if ',' in genres else [g.strip() for g in genres.split()] if genres else []
    pills = [(1079, 332, 169, 72), (1337, 334, 242, 70), (1598, 332, 216, 71)]
    genre_draw_commands = []
    for i, g in enumerate(genre_list[:3]):
        px, py, pw, ph = pills[i]
        display_g = apply_small_caps(g) if small_caps else g
        text_bbox = temp_draw.textbbox((0, 0), display_g, font=font_genres)
        tw, th = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
        tx = px + (pw - tw) // 2 + 45 # Perfect Right Shift
        ty = py + (ph - th) // 2 - 2
        genre_draw_commands.append(((tx, ty), display_g, font_genres))

    rating = str(imdb_data.get("rating", ""))
    duration = str(imdb_data.get("duration", ""))

    synopsis_draw_commands = []
    if synopsis:
        clean_synopsis = re.sub(r'<[^>]+>', '', synopsis)
        box_x, box_y, box_w = 1100, 645, 640 # Box width thodi kam ki hai taaki overflow na ho

        words = clean_synopsis.split(' ')
        lines, current_line = [], []
        for word in words:
            current_line.append(word)
            w = temp_draw.textlength(' '.join(current_line), font=font_synopsis)
            if w > box_w:
                current_line.pop()
                lines.append(' '.join(current_line))
                current_line = [word]
        if current_line: lines.append(' '.join(current_line))

        if lines: # Only 1 line printed with read more
            synopsis_draw_commands.append(((box_x, box_y), lines[0] + "...read more", font_synopsis))

    season_text = "SEASON 1"
    season_match = re.search(r'(?i)\bseason\s+(\d+)', title)
    if season_match: season_text = f"SEASON {season_match.group(1)}"
    season_x, season_y = 1550, 620 # Fits perfectly inside the dark button

    eps = [
        {"title": imdb_data.get('ep1_title', ""), "rating": imdb_data.get('ep1_rating', ""), "duration": imdb_data.get('ep1_duration', ""), "image": imdb_data.get('ep1_thumb')},
        {"title": imdb_data.get('ep2_title', ""), "rating": imdb_data.get('ep2_rating', ""), "duration": imdb_data.get('ep2_duration', ""), "image": imdb_data.get('ep2_thumb')}
    ]
    
    ep_coords = [
        {"box": (201, 834, 348, 975), "title_pos": (500, 842), "rating_pos": (465, 915), "duration_pos": (565, 915)},
        {"box": (1032, 834, 1182, 975), "title_pos": (1330, 842), "rating_pos": (1290, 915), "duration_pos": (1390, 915)}
    ]

    ep_draw_commands = []
    for i, ep_info in enumerate(ep_coords):
        if i < len(eps):
            ep = eps[i]
            ep_title_text = f"{ep['title']}"
            words = ep_title_text.split()
            if len(words) > 4: ep_title_text = " ".join(words[:4]) + "..."
            
            if ep_title_text:
                ep_draw_commands.append((ep_info["title_pos"], ep_title_text, font_ep_title))
            if ep['rating'] and ep['rating'] != "N/A":
                ep_draw_commands.append((ep_info["rating_pos"], f"{ep['rating']}", font_ep_sub))
            if ep['duration'] and ep['duration'] != "N/A":
                ep_draw_commands.append((ep_info["duration_pos"], f"{ep['duration'].replace(' min', '')}", font_ep_sub))

            thumb_img = None
            if i == 0 and custom_ep1_path:
                try: thumb_img = Image.open(custom_ep1_path).convert("RGBA")
                except: pass
            elif i == 1 and custom_ep2_path:
                try: thumb_img = Image.open(custom_ep2_path).convert("RGBA")
                except: pass

            if not thumb_img and ep.get("image"):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(ep["image"], headers={'User-Agent': 'Mozilla/5.0'}) as resp:
                            if resp.status == 200: thumb_img = Image.open(io.BytesIO(await resp.read())).convert("RGBA")
                except: pass

            if not thumb_img:
                thumb_img = Image.new("RGBA", (200, 200), (60, 60, 60, 255))

            try: # Use the precise crop-paste function for episodes too!
                ox = ep1_offset_x if i == 0 else ep2_offset_x
                oy = ep1_offset_y if i == 0 else ep2_offset_y
                zm = ep1_zoom if i == 0 else ep2_zoom
                paste_with_crop(base_canvas, thumb_img, ep_info["box"], ox, oy, zm)
            except: pass

    # MERGE THE LAYERS
    base = Image.alpha_composite(base_canvas, framed_template)
    draw = ImageDraw.Draw(base)

    # TEXT RENDERING
    if disp_title:
        title_y = 145
        for line in title_lines:
            draw.text((1125, title_y), line, font=font_title, fill=(255, 255, 255, 255), anchor="la")
            title_y += 75

    for pos, text, font in genre_draw_commands:
        draw.text(pos, text, font=font, fill=(255, 255, 255, 255), anchor="la")

    # Ratings/Duration shifted right safely
    if rating and rating != "N/A":
        draw.text((1180, 480), rating, font=font_rating, fill=(255, 255, 255, 255), anchor="la")
    if duration and duration != "N/A":
        draw.text((1480, 480), duration.replace(" min", ""), font=font_rating, fill=(255, 255, 255, 255), anchor="la")

    for pos, text, font in synopsis_draw_commands:
        draw.text(pos, text, font=font, fill=(180, 180, 180, 255), anchor="la")

    if season_text: # Inside the small pill
        draw.text((season_x, season_y), season_text, font=font_season, fill=(255, 255, 255, 255), anchor="lm")

    for pos, text, font in ep_draw_commands:
        draw.text(pos, text, font=font, fill=(255, 255, 255, 255), anchor="la")

    disp_username = apply_small_caps(username) if small_caps else username
    if disp_username: # Left Shifted Branding
        draw.text((155, 56), disp_username, font=font_brand_small, fill=(180, 180, 180, 255), anchor="lm")

    if logo_url:
        try:
            if logo_url.startswith("http"):
                async with aiohttp.ClientSession() as session:
                    async with session.get(logo_url) as resp:
                        if resp.status == 200:
                            logo_img = Image.open(io.BytesIO(await resp.read())).convert("RGBA")
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
        except: pass

    base = enhance_image(base)
    out_bio = io.BytesIO()
    base.convert("RGB").save(out_bio, format="JPEG", quality=95)
    out_bio.name = "poster3.jpg"
    out_bio.seek(0)
    return out_bio
