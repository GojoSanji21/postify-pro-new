import os
import aiohttp
import asyncio
import re
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageChops, ImageEnhance
import textwrap
import io
import numpy as np
import urllib.parse
import cv2

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

def colorize_template_2(template_img, color_hex):
    arr = np.array(template_img)
    target_hex = color_hex.lstrip('#')
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
        pass

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
        if not bbox:
            bbox = (0, 0, 1920, 1080)

        mask_h = bbox[3] - bbox[1]
        mask_w = bbox[2] - bbox[0]

        if crop_state == 1:
            v_center = 0.0
        elif crop_state == 2:
            v_center = 1.0
        else:
            v_center = 0.5

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
            elif os.path.exists(logo_url):
                logo_img = Image.open(logo_url).convert('RGBA')
        except Exception:
            pass

    genres_caps = genres.upper() if genres else ""

    if small_caps:
        genres_caps = apply_small_caps(genres_caps)
        synopsis = apply_small_caps(synopsis)
        username = apply_small_caps(username)

    try:
        if template_version == 2:
            font_main_white = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Bold.ttf"), 85)
            font_colored_title = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Black.ttf"), 65)
        else:
            font_main_white = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Bold.ttf"), 85)
            font_colored_title = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Black.ttf"), 65)
    except:
        font_main_white = font_colored_title = ImageFont.load_default()

    try:
        font_genres = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Medium.ttf"), 35)
        font_synopsis = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Medium.ttf"), 30)
        font_brand = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Medium.ttf"), 40)
    except:
        try:
            font_genres = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Bold.ttf"), 35)
            font_synopsis = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Bold.ttf"), 30)
            font_brand = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Bold.ttf"), 40)
        except:
            font_genres = font_synopsis = font_brand = ImageFont.load_default()

    title = title.upper()
    title = re.sub(r'(?i)\bSEASON\s+(\d+)', r'S\1', title)

    wrapped_title = textwrap.fill(title, width=17)
    title_lines = wrapped_title.split('\n')

    if len(title_lines) > 2:
        title_lines = title_lines[:2]
        if len(title_lines[1]) > 14:
            title_lines[1] = title_lines[1][:14] + "..."
        else:
            title_lines[1] = title_lines[1] + "..."

    x_offset = 80
    y_dynamic_offset = 280

    try:
        font_colored_title_enlarged = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Black.ttf"), 75)
    except:
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

    brand_x = 80
    brand_y = 60

    if logo_img:
        try:
            logo_img = clean_logo(logo_img)
            logo_img.thumbnail((95, 95), Image.Resampling.LANCZOS)
            logo_img = logo_img.convert('RGBA')
            final_img.paste(logo_img, (brand_x, brand_y), logo_img)
            brand_x += 115
        except Exception:
            pass

    brand_color = color_hex if template_version == 2 else "white"
    draw.text((brand_x, brand_y + 15), username, font=font_brand, fill=brand_color)

    buf = io.BytesIO()
    final_img.save(buf, format='PNG')
    buf.seek(0)
    return buf


def colorize_poster_2_template(template_img, color_hex):
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
                async with session.get(anime_img_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}) as resp:
                    anime_img_data = await resp.read()
                    anime_img = Image.open(io.BytesIO(anime_img_data)).convert('RGBA')
            except Exception:
                anime_img = Image.new('RGBA', (1920, 1080), (100, 100, 100, 255))
    else:
        anime_img = Image.new('RGBA', (1920, 1080), (100, 100, 100, 255))

    try:
        import rembg
        anime_img = rembg.remove(anime_img)
    except ImportError:
        raise Exception("Background removal failed due to missing dependencies. Please check rembg and onnxruntime are installed.")
    except Exception as e:
        raise Exception(f"Background removal failed: {str(e)}")

    base_template_url = "https://ibb.co/N6r6n2Fp"
    base_template = None

    try:
        async with aiohttp.ClientSession() as session:
            if "ibb.co" in base_template_url and not base_template_url.endswith(('.png', '.jpg', '.jpeg')):
                async with session.get(base_template_url) as html_resp:
                    if html_resp.status == 200:
                        html = await html_resp.text()
                        match = re.search(r'<meta property="og:image" content="([^"]+)"', html)
                        if match:
                            base_template_url = match.group(1)

            async with session.get(base_template_url) as resp:
                if resp.status == 200:
                    template_data = await resp.read()
                    base_template = Image.open(io.BytesIO(template_data)).convert('RGBA')
    except Exception:
        pass

    if not base_template:
        base_template = Image.open(os.path.join(os.path.dirname(__file__), "assets", "template.png")).convert('RGBA')

    if color_hex:
        base_template = colorize_poster_2_template(base_template, color_hex).convert('RGBA')

    char_w, char_h = anime_img.size
    aspect_ratio = char_w / char_h

    new_h = int(1080 * zoom_scale)
    new_w = int(new_h * aspect_ratio)

    if crop_state == 0:
        base_x = (1920 - new_w) // 2
    elif crop_state == 1:
        base_x = 1920 - new_w
    else:
        base_x = 0

    base_y = (1080 - new_h) // 2

    paste_x = base_x + offset_x
    paste_y = base_y + offset_y

    anime_artwork = anime_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    anime_artwork = enhance_image(anime_artwork)

    final_img = Image.new('RGBA', base_template.size, (0, 0, 0, 255))
    final_img.paste(base_template, (0, 0))
    final_img.paste(anime_artwork, (paste_x, paste_y), anime_artwork if anime_artwork.mode == 'RGBA' else None)

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
            elif os.path.exists(logo_url):
                logo_img = Image.open(logo_url).convert('RGBA')
        except Exception:
            pass

    genres_caps = genres.upper() if genres else ""
    if small_caps:
        genres_caps = apply_small_caps(genres_caps)
        username = apply_small_caps(username)

    try:
        font_main_white = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Bold.ttf"), 100)
        font_colored_title = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Black.ttf"), 110)
    except:
        font_main_white = font_colored_title = ImageFont.load_default()

    try:
        font_genres = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Bold.ttf"), 45)
        font_synopsis = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Medium.ttf"), 30)
        font_brand = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Medium.ttf"), 40)
    except:
        try:
            font_genres = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Bold.ttf"), 45)
            font_synopsis = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Bold.ttf"), 30)
            font_brand = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Bold.ttf"), 40)
        except:
            font_genres = font_synopsis = font_brand = ImageFont.load_default()

    title = title.upper()
    title = re.sub(r'(?i)\bSEASON\s+(\d+)', r'S\1', title)
    wrapped_title = textwrap.fill(title, width=17)
    title_lines = wrapped_title.split('\n')

    if len(title_lines) > 2:
        title_lines = title_lines[:2]
        if len(title_lines[1]) > 14:
            title_lines[1] = title_lines[1][:14] + "..."
        else:
            title_lines[1] = title_lines[1] + "..."

    x_offset = 80
    y_dynamic_offset = 360

    try:
        font_colored_title_enlarged = font_colored_title
    except:
        font_colored_title_enlarged = font_colored_title

    for i, line in enumerate(title_lines):
        if i == 0:
            draw.text((x_offset, y_dynamic_offset), line, font=font_main_white, fill="#333333")
            y_dynamic_offset += 100
        else:
            draw.text((x_offset, y_dynamic_offset), line, font=font_colored_title_enlarged, fill=color_hex)
            y_dynamic_offset += 85

    y_dynamic_offset += 30
    draw.text((x_offset, y_dynamic_offset), genres_caps, font=font_genres, fill=color_hex)

    box_x = 70
    box_y = 640
    box_w = 800
    box_h = 180

    words = synopsis.split(' ')
    lines = []
    current_line = []

    for word in words:
        current_line.append(word)
        w = draw.textlength(' '.join(current_line), font=font_synopsis)
        if w > box_w:
            current_line.pop()
            lines.append(' '.join(current_line))
            current_line = [word]
    if current_line:
        lines.append(' '.join(current_line))

    line_spacing = 5
    line_h = 35  
    max_lines = box_h // (line_h + line_spacing)

    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last_line = lines[-1]
        while draw.textlength(last_line + "...read more", font=font_synopsis) > box_w and len(last_line) > 0:
            last_line = last_line[:-1]
        lines[-1] = last_line.strip() + "...read more"

    wrapped_synopsis = "\n".join(lines)
    draw.text((box_x, box_y), wrapped_synopsis, font=font_synopsis, fill="#333333")

    brand_x = 80
    brand_y = 60

    if logo_img:
        try:
            if logo_img.getextrema()[3][0] < 255:
                logo_img_clean = logo_img
            else:
                white_img = Image.new("RGBA", logo_img.size, (255, 255, 255, 255))
                white_img.putalpha(logo_img.convert("L"))
                logo_img_clean = white_img

            logo_img_clean.thumbnail((95, 95), Image.Resampling.LANCZOS)
            logo_img_clean = logo_img_clean.convert('RGBA')
            final_img.paste(logo_img_clean, (brand_x, brand_y), logo_img_clean)
            brand_x += 115
        except Exception:
            pass

    brand_words = username.split(maxsplit=1)
    if len(brand_words) > 0:
        draw.text((brand_x, brand_y + 15), brand_words[0], font=font_brand, fill="grey")
        if len(brand_words) > 1:
            w1_length = draw.textlength(brand_words[0] + " ", font=font_brand)
            draw.text((brand_x + w1_length, brand_y + 15), brand_words[1], font=font_brand, fill=color_hex)

    buf = io.BytesIO()
    final_img.save(buf, format='PNG')
    buf.seek(0)
    return buf


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

async def async_fetch_jikan_episodes(anime_title):
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

async def generate_poster_3(anime_img_url=None, custom_image_path=None, title="", genres="", synopsis="", username="", logo_url=None, small_caps=False, offset_x=0, offset_y=0, zoom_scale=1.0, imdb_data=None, custom_ep1_path=None, custom_ep2_path=None, ep1_offset_x=0, ep1_offset_y=0, ep1_zoom=1.0, ep2_offset_x=0, ep2_offset_y=0, ep2_zoom=1.0):
    if imdb_data is None: imdb_data = {}

    template_path = os.path.join(ASSETS_DIR, "poster3_template_1080.png")
    if not os.path.exists(template_path):
        template_path = os.path.join(ASSETS_DIR, "poster3_template.png")
    base_template = Image.open(template_path).convert("RGBA").resize((1920, 1080), Image.Resampling.LANCZOS)

    template_arr = np.array(base_template)
    white_mask = (template_arr[:,:,0] >= 240) & (template_arr[:,:,1] >= 240) & (template_arr[:,:,2] >= 240)

    region_mask = np.zeros(template_arr.shape[:2], dtype=bool)
    region_mask[140:710, 180:1030] = True   
    region_mask[820:990, 180:370] = True    
    region_mask[820:990, 1010:1200] = True  
    region_mask[5:130, 1740:1900] = True    

    template_arr[white_mask & region_mask, 3] = 0
    framed_template = Image.fromarray(template_arr)

    base_canvas = Image.new("RGBA", (1920, 1080), (30, 30, 30, 255))
    
    try:
        if logo_url:
            if logo_url.startswith("http"):
                async with aiohttp.ClientSession() as session:
                    async with session.get(logo_url) as resp:
                        if resp.status == 200:
                            logo_img = Image.open(io.BytesIO(await resp.read())).convert("RGBA")
            else:
                logo_img = Image.open(logo_url).convert("RGBA")

            logo_size = 110 
            logo_img = ImageOps.fit(logo_img, (logo_size, logo_size), method=Image.Resampling.LANCZOS)
            base_canvas.paste(logo_img, (1780, 10), logo_img if logo_img.mode == 'RGBA' else None)
    except Exception:
        pass

    try:
        if custom_image_path:
            char_img = Image.open(custom_image_path).convert("RGBA")
        elif anime_img_url:
            async with aiohttp.ClientSession() as session:
                async with session.get(anime_img_url, headers={'User-Agent': 'Mozilla/5.0'}) as resp:
                    if resp.status == 200:
                        char_img = Image.open(io.BytesIO(await resp.read())).convert("RGBA")
                    else:
                        char_img = Image.new("RGBA", (800, 500), (40, 40, 40, 255))
        else:
            char_img = Image.new("RGBA", (800, 500), (40, 40, 40, 255))

        paste_with_crop(base_canvas, char_img, (201, 156, 1005, 696), offset_x, offset_y, zoom_scale)
    except Exception as e:
        pass

    base = Image.alpha_composite(base_canvas, framed_template)
    base = enhance_image(base)
    
    draw = ImageDraw.Draw(base)
    temp_draw = ImageDraw.Draw(Image.new("RGBA", (10, 10)))

    sn_x1, sn_y1 = 235, 575
    sn_x2, sn_y2 = 475, 645
    draw.rounded_rectangle([sn_x1, sn_y1, sn_x2, sn_y2], radius=18, fill=(35, 35, 40, 255), outline=(180, 180, 180, 200), width=2)
    try:
        sn_font = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Medium.ttf"), 28)
    except:
        sn_font = ImageFont.load_default()
    draw.text((280, 595), "Stream Now", font=sn_font, fill=(255, 255, 255, 255))
    px, py = 425, 600
    draw.polygon([(px, py), (px, py+20), (px+15, py+10)], outline=(255, 255, 255, 255), width=2)

    try:
        font_title = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Black.ttf"), 80) 
        font_rating = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Black.ttf"), 58) 
        font_brand_small = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Black.ttf"), 24) 
        font_ep_title = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Black.ttf"), 32) 
        font_season = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Black.ttf"), 24) 
    except:
        font_title = font_rating = font_brand_small = font_ep_title = font_season = ImageFont.load_default()

    try:
        font_genres = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Black.ttf"), 26) 
        font_synopsis = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Black.ttf"), 24) 
        font_ep_dur = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Black.ttf"), 30) 
    except:
        font_genres = font_synopsis = font_ep_dur = ImageFont.load_default()

    disp_title = apply_small_caps(title) if small_caps else title
    title_words = disp_title.split() if disp_title else []
    title_lines = []
    
    if len(title_words) > 2:
        title_lines.append(" ".join(title_words[:2]))
        if len(title_words) > 5:
            title_lines.append(" ".join(title_words[2:5]) + "...")
        else:
            title_lines.append(" ".join(title_words[2:]))
    else:
        title_lines.append(disp_title if disp_title else "")

    genre_list = [g.strip() for g in genres.split(',')] if ',' in genres else [g.strip() for g in genres.split()] if genres else []
    pills = [(1079, 332, 169, 72), (1337, 334, 242, 70), (1598, 332, 216, 71)]
    genre_draw_commands = []
    for i, g in enumerate(genre_list[:3]):
        px, py, pw, ph = pills[i]
        display_g = apply_small_caps(g) if small_caps else g
        text_bbox = temp_draw.textbbox((0, 0), display_g, font=font_genres)
        tw, th = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
        tx = px + (pw - tw) // 2 + 55 
        ty = py + (ph - th) // 2 - 2
        genre_draw_commands.append(((tx, ty), display_g, font_genres))

    rating = str(imdb_data.get("rating", ""))
    duration = str(imdb_data.get("duration", ""))

    synopsis_draw_commands = []
    if synopsis:
        clean_synopsis = re.sub(r'<[^>]+>', '', synopsis)
        words = clean_synopsis.split()
        final_synopsis = " ".join(words[:8]) + " ...read more"
        synopsis_draw_commands.append(((1100, 650), final_synopsis, font_synopsis))

    season_text = "SEASON 1"
    season_match = re.search(r'(?i)\bseason\s+(\d+)', title)
    if season_match: season_text = f"SEASON {season_match.group(1)}"
    season_x, season_y = 1715, 758 

    jikan_data = {}
    if not imdb_data.get('ep1_thumb'):
        jikan_data = await async_fetch_jikan_episodes(title)

    eps = [
        {"title": imdb_data.get('ep1_title') or jikan_data.get('ep1_title') or "", "rating": imdb_data.get('ep1_rating', ""), "duration": imdb_data.get('ep1_duration', ""), "image": imdb_data.get('ep1_thumb') or jikan_data.get('ep1_thumb')},
        {"title": imdb_data.get('ep2_title') or jikan_data.get('ep2_title') or "", "rating": imdb_data.get('ep2_rating', ""), "duration": imdb_data.get('ep2_duration', ""), "image": imdb_data.get('ep2_thumb') or jikan_data.get('ep2_thumb')}
    ]
    
    ep_coords = [
        {"box": (201, 834, 348, 975), "title_pos": (550, 850), "duration_pos": (610, 915)}, 
        {"box": (1032, 834, 1182, 975), "title_pos": (1380, 850), "duration_pos": (1440, 915)} 
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
            if ep['duration'] and ep['duration'] != "N/A":
                ep_draw_commands.append((ep_info["duration_pos"], f"{ep['duration'].replace(' min', '')}", font_ep_dur))

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

            try: 
                thumb_img = enhance_image(thumb_img)

                ox = ep1_offset_x if i == 0 else ep2_offset_x
                oy = ep1_offset_y if i == 0 else ep2_offset_y
                zm = ep1_zoom if i == 0 else ep2_zoom
                
                bw = ep_info["box"][2] - ep_info["box"][0]
                bh = ep_info["box"][3] - ep_info["box"][1]
                iw, ih = thumb_img.size
                sc = max(bw / iw, bh / ih) * zm
                nw, nh = int(iw * sc), int(ih * sc)
                resized = thumb_img.resize((nw, nh), Image.Resampling.LANCZOS)
                
                temp_box = Image.new("RGBA", (bw, bh), (0,0,0,0))
                px = (bw - nw) // 2 + ox
                py = (bh - nh) // 2 + oy
                temp_box.paste(resized, (px, py))
                base.paste(temp_box, (ep_info["box"][0], ep_info["box"][1]), temp_box)
            except: pass

    if disp_title:
        title_y = 125
        for line in title_lines:
            draw.text((1125, title_y), line, font=font_title, fill=(255, 255, 255, 255), anchor="la")
            title_y += 90

    for pos, text, font in genre_draw_commands:
        draw.text(pos, text, font=font, fill=(255, 255, 255, 255), anchor="la")

    if rating and rating != "N/A":
        draw.text((1200, 490), rating, font=font_rating, fill=(255, 255, 255, 255), anchor="la")
    if duration and duration != "N/A":
        draw.text((1520, 490), duration.replace(" min", ""), font=font_rating, fill=(255, 255, 255, 255), anchor="la")

    for pos, text, font in synopsis_draw_commands:
        draw.text(pos, text, font=font, fill=(180, 180, 180, 255), anchor="la")

    if season_text: 
        draw.text((season_x, season_y), season_text, font=font_season, fill=(255, 255, 255, 255), anchor="mm")

    for pos, text, font in ep_draw_commands:
        draw.text(pos, text, font=font, fill=(255, 255, 255, 255), anchor="la")

    disp_username = apply_small_caps(username) if small_caps else username
    if disp_username: 
        draw.text((360, 56), disp_username, font=font_brand_small, fill=(180, 180, 180, 255), anchor="lm")

    out_bio = io.BytesIO()
    base.convert("RGB").save(out_bio, format="JPEG", quality=100)
    out_bio.name = "poster3.jpg"
    out_bio.seek(0)
    return out_bio


# ==========================================
# FINAL POSTER 4 GENERATION (100% FIXED)
# ==========================================
async def generate_poster_4(anime_img_url=None, custom_image_path=None, title="", genres="", synopsis="", username="", logo_url=None, small_caps=False, color_hex="#007BFF", offset_x=0, offset_y=0, zoom_scale=1.0, release_year="", episodes="", seasons=""):
    template_path = 'plugins/assets/poster4.png'
    template_img = Image.open(template_path).convert('RGBA')

    # STEP 1: FAST VIBGYOR THEME CHAMELEON (Only colors blue areas)
    arr = np.array(template_img, dtype=np.float32)
    target_hex = color_hex.lstrip('#')
    tr, tg, tb = tuple(int(target_hex[i:i+2], 16) for i in (0, 2, 4))

    r, g, b, a = arr[:,:,0], arr[:,:,1], arr[:,:,2], arr[:,:,3]
    # Blue detection mask (Strictly isolates blue without bleeding into white/grey)
    blue_mask = (b > r + 30) & (b > g + 30) & (a > 0)
    
    arr[blue_mask, 0] = tr
    arr[blue_mask, 1] = tg
    arr[blue_mask, 2] = tb
    template_img = Image.fromarray(arr.astype(np.uint8))

    # STEP 2: FAST BACKGROUND REMOVAL (Custom vs Fetched)
    try:
        if custom_image_path:
            char_img = Image.open(custom_image_path).convert("RGBA")
            c_arr = np.array(char_img)
            cr, cg, cb, ca = c_arr[:,:,0], c_arr[:,:,1], c_arr[:,:,2], c_arr[:,:,3]

            # Fast Black/White Eraser (Also zeros RGB to stop edge bleeding on resize)
            white_mask = (cr > 240) & (cg > 240) & (cb > 240)
            black_mask = (cr < 25) & (cg < 25) & (cb < 25)
            
            c_arr[white_mask] = [0, 0, 0, 0]
            c_arr[black_mask] = [0, 0, 0, 0]
            char_img = Image.fromarray(c_arr)

        elif anime_img_url:
            async with aiohttp.ClientSession() as session:
                async with session.get(anime_img_url, headers={'User-Agent': 'Mozilla/5.0'}) as resp:
                    if resp.status == 200:
                        char_img = Image.open(io.BytesIO(await resp.read())).convert("RGBA")
                    else:
                        char_img = Image.new("RGBA", (100, 100), (0,0,0,0))

            cw, ch = char_img.size
            if ch > 1080:
                scale = 1080 / ch
                new_w = int(cw * scale)
                char_img = char_img.resize((new_w, 1080), Image.Resampling.LANCZOS)

            try:
                import rembg
                char_img = rembg.remove(char_img)
            except ImportError:
                raise Exception("Background removal failed due to missing dependencies. Please check rembg and onnxruntime are installed.")
            except Exception as e:
                raise Exception(f"Background removal failed: {str(e)}")
        else:
            char_img = Image.new("RGBA", (100, 100), (0,0,0,0))
    except Exception:
        char_img = Image.new("RGBA", (100, 100), (0,0,0,0))

    # Base Canvas
    base_canvas = Image.new("RGBA", template_img.size, (0, 0, 0, 255))
    base_canvas.paste(template_img, (0, 0), template_img)

    # Paste Character on the RIGHT side
    try:
        iw, ih = char_img.size
        bw, bh = 1000, 941
        sc = max(bw / iw, bh / ih) * zoom_scale
        nw, nh = int(iw * sc), int(ih * sc)
        resized = char_img.resize((nw, nh), Image.Resampling.LANCZOS)

        px = 850 + offset_x
        py = (bh - nh) // 2 + offset_y

        base_canvas.paste(resized, (px, py), mask=resized if resized.mode == 'RGBA' else None)
    except Exception:
        pass

    base = base_canvas
    draw = ImageDraw.Draw(base)

    # Load Fonts
    try:
        font_large = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Black.ttf"), 70)
        font_meta = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Bold.ttf"), 30)
        font_synopsis = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Medium.ttf"), 24)
        font_brand = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Bold.ttf"), 35)
    except Exception as e:
        raise Exception("Failed to load required custom fonts. DO NOT use Pillow's default font.")

    # STEP 3: BRANDING LOGO & TEXT (Top Right)
    try:
        if logo_url:
            if logo_url.startswith('http'):
                async with aiohttp.ClientSession() as session:
                    async with session.get(logo_url) as resp:
                        if resp.status == 200:
                            logo_img = Image.open(io.BytesIO(await resp.read())).convert("RGBA")
            else:
                logo_img = Image.open(logo_url).convert("RGBA")

            logo_img.thumbnail((150, 150), Image.Resampling.LANCZOS)
            lw, lh = logo_img.size
            base.paste(logo_img, (1672 - lw - 50, 50), mask=logo_img if logo_img.mode == 'RGBA' else None)

            text_x = 1672 - (lw//2) - 50
            text_y = 50 + lh + 20
        else:
            text_x = 1672 - 75 - 50
            text_y = 50 + 150 + 20
    except:
        text_x = 1672 - 75 - 50
        text_y = 50 + 150 + 20

    disp_username = apply_small_caps(username) if small_caps else username
    draw.text((text_x, text_y), disp_username, font=font_brand, fill=(255,255,255,255), anchor="mm")

    # STEP 4: TYPOGRAPHY & LAYOUT (Left Side, Below Crunchyroll)
    disp_title = apply_small_caps(title) if small_caps else title
    title_words = disp_title.split() if disp_title else []

    def draw_colored_text(draw_obj, text_words, start_x, start_y, font, highlight_idx):
        cx = start_x
        for i, word in enumerate(text_words):
            color = f"#{target_hex}" if i == highlight_idx else "#000000"
            draw_obj.text((cx, start_y), word + " ", font=font, fill=color)
            w = draw_obj.textlength(word + " ", font=font)
            cx += w

    # The Title (Safely placed at Y=100, leaving space for Crunchyroll at Y=250-280)
    ty = 100
    if len(title_words) > 3:
        line1_words = title_words[:3]
        if len(title_words) > 7:
            line2_words = title_words[3:7] + ["..."]
        else:
            line2_words = title_words[3:]

        draw_colored_text(draw, line1_words, 100, ty, font_large, -1) 
        ty += 90
        draw_colored_text(draw, line2_words, 100, ty, font_large, len(line2_words) - 1) 
    else:
        draw_colored_text(draw, title_words, 100, ty, font_large, len(title_words) - 1)

    # The Genres & Metadata (Below Crunchyroll, Placed at Y=380)
    genres_formatted = ""
    if genres:
        genres_list = [g.strip() for g in genres.split(",")]
        genres_formatted = " | ".join(genres_list).upper()
    else:
        genres_formatted = "UNKNOWN"
        
    release_year = release_year if release_year else "2026"
    episodes = episodes if episodes else "?"
    seasons = seasons if seasons else "1"

    meta_y = 380
    metadata_text = f"{release_year} | {genres_formatted} | {episodes} (EPS) | {seasons} SEASON"
    draw.text((100, meta_y), metadata_text, font=font_meta, fill=(180, 180, 180, 255))

    # The Synopsis (Placed at Y=450)
    syn_y = 450
    if synopsis:
        clean_synopsis = re.sub(r'<[^>]+>', '', synopsis)
        words = clean_synopsis.split()
        if len(words) > 65:
            clean_synopsis = " ".join(words[:65]) + "...read more"

        lines = textwrap.wrap(clean_synopsis, width=75)
        wrapped_synopsis = "\n".join(lines)
        draw.multiline_text((100, syn_y), wrapped_synopsis, font=font_synopsis, fill=(100, 100, 100, 255), spacing=10)

    out_bio = io.BytesIO()
    base.convert("RGB").save(out_bio, format="JPEG", quality=100)
    out_bio.name = "poster4.jpg"
    out_bio.seek(0)
    return out_bio
