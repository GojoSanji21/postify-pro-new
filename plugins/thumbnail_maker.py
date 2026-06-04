import os
import aiohttp
import asyncio
import re
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageChops, ImageEnhance
import textwrap
import io

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

    # Very simple color isolation for turquoise & purple on Template 2
    # Adjust this threshold as needed based on actual template colors
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
                async with session.get(anime_img_url) as resp:
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

    # If Poster 2 AND no custom image is sent (i.e. skipped fanart)
    # Then DO NOT punch out the mask. The fanart should sit cleanly below without hexagonal cutout.
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

        # 16:9 Blurred Background Layer
        blurred_bg = ImageOps.fit(anime_img, base_template.size, method=Image.Resampling.LANCZOS)
        blurred_bg = blurred_bg.filter(ImageFilter.GaussianBlur(35))
        blurred_bg = ImageEnhance.Brightness(blurred_bg).enhance(0.5)
        anime_artwork = blurred_bg.convert('RGBA')

        bbox = strict_mask.getbbox()
        if not bbox:
            bbox = (0, 0, 1920, 1080)

        mask_h = bbox[3] - bbox[1]
        mask_w = bbox[2] - bbox[0]

        # Universal Zoom Fit Setup (No blurred sides)
        if crop_state == 1:
            v_center = 0.0 # Top Focus
        elif crop_state == 2:
            v_center = 1.0 # Bottom Focus
        else:
            v_center = 0.5 # Center Focus (Default)

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

    # ==========================================
    # BULLETPROOF FONT LOADER (Direct from your local files)
    # ==========================================
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
            # Agar Medium upload nahi kiya, toh Bold ko chhota karke use kar lega (Lekin microscopic nahi hoga)
            font_genres = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Bold.ttf"), 35)
            font_synopsis = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Bold.ttf"), 30)
            font_brand = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Bold.ttf"), 40)
        except:
            font_genres = font_synopsis = font_brand = ImageFont.load_default()

    # ==========================================
    # TITLE SHORTENER & S2 REPLACER
    # ==========================================
    title = title.upper()
    title = re.sub(r'(?i)\bSEASON\s+(\d+)', r'S\1', title) # Works for "Season 2", "SEASON 2", etc.
    
    wrapped_title = textwrap.fill(title, width=17) 
    title_lines = wrapped_title.split('\n')
    
    # 2-Line Limit Rule!
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
    import numpy as np
    import cv2
    from PIL import Image

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
                async with session.get(anime_img_url) as resp:
                    anime_img_data = await resp.read()
                    anime_img = Image.open(io.BytesIO(anime_img_data)).convert('RGBA')
            except Exception:
                anime_img = Image.new('RGBA', (1920, 1080), (100, 100, 100, 255))
    else:
        anime_img = Image.new('RGBA', (1920, 1080), (100, 100, 100, 255))

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

    if crop_state == 0: # Center
        base_x = (1920 - new_w) // 2
    elif crop_state == 1: # Right
        base_x = 1920 - new_w
    else: # Left
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

    # Strict bounding box for synopsis (light cyan box)
    box_x = 70
    box_y = 640
    box_w = 800
    box_h = 180

    # Calculate word wrap based on exact pixel width
    words = synopsis.split(' ')
    lines = []
    current_line = []

    for word in words:
        current_line.append(word)
        # Check width
        w = draw.textlength(' '.join(current_line), font=font_synopsis)
        if w > box_w:
            current_line.pop()
            lines.append(' '.join(current_line))
            current_line = [word]
    if current_line:
        lines.append(' '.join(current_line))

    # Calculate max lines based on exact pixel height
    # Approximate line height
    line_spacing = 5
    line_h = 35  # Rough height for size 30 font
    max_lines = box_h // (line_h + line_spacing)

    if len(lines) > max_lines:
        lines = lines[:max_lines]
        # Truncate the last line properly
        last_line = lines[-1]
        while draw.textlength(last_line + "...read more", font=font_synopsis) > box_w and len(last_line) > 0:
            last_line = last_line[:-1]
        lines[-1] = last_line.strip() + "...read more"

    wrapped_synopsis = "\n".join(lines)

    # Draw inside the specific box coordinates, completely overriding dynamic Y
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

async def generate_poster_3(anime_img_url=None, custom_image_path=None, title="", genres="", synopsis="", username="", logo_url=None, small_caps=False, offset_x=0, offset_y=0, zoom_scale=1.0, imdb_data=None):
    if imdb_data is None:
        imdb_data = {}

    template_path = os.path.join(ASSETS_DIR, "poster3_template.png")
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Poster 3 Template missing at {template_path}")

    base = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(base)

    # 1. Main Fanart (Left Box)
    # Box Coordinates approximate based on 1920x1080 template:
    # Left box bounds: [190, 160] to [1000, 700] -> approx 810x540
    try:
        if custom_image_path:
            char_img = Image.open(custom_image_path).convert("RGBA")
        elif anime_img_url:
            async with aiohttp.ClientSession() as session:
                async with session.get(anime_img_url) as resp:
                    if resp.status == 200:
                        img_data = await resp.read()
                        char_img = Image.open(io.BytesIO(img_data)).convert("RGBA")
                    else:
                        char_img = Image.new("RGBA", (800, 500), (40, 40, 40, 255))
        else:
            char_img = Image.new("RGBA", (800, 500), (40, 40, 40, 255))

        char_w, char_h = char_img.size
        # The target rectangle is roughly (195, 150) to (1010, 695) -> 815x545
        box_rect = (195, 150, 1010, 695)
        box_w = box_rect[2] - box_rect[0]
        box_h = box_rect[3] - box_rect[1]

        scale = max(box_w / char_w, box_h / char_h) * zoom_scale
        new_w, new_h = int(char_w * scale), int(char_h * scale)
        char_img = char_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        paste_x = box_rect[0] + (box_w - new_w) // 2 + offset_x
        paste_y = box_rect[1] + (box_h - new_h) // 2 + offset_y

        temp_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
        temp_layer.paste(char_img, (paste_x, paste_y))

        # Create mask for rounded rectangle
        mask = Image.new("L", base.size, 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.rounded_rectangle(box_rect, radius=30, fill=255)

        base.paste(temp_layer, (0, 0), mask)
    except Exception as e:
        import traceback
        traceback.print_exc()

    # 2. Typography Setup
    try:
        font_title = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto-Black.ttf"), 65)
        font_genres = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto-Bold.ttf"), 28)
        font_rating = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto-Black.ttf"), 55)
        font_synopsis = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto-Medium.ttf"), 25)
        font_brand = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto-Black.ttf"), 30)
        font_ep_title = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto-Black.ttf"), 35)
        font_ep_sub = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto-Medium.ttf"), 30)
    except Exception as e:
        # Fallback to the available font in repo if standard ones are missing
        try:
            fallback = os.path.join(FONTS_DIR, "Montserrat-Black.ttf")
            font_title = font_rating = font_brand = font_ep_title = ImageFont.truetype(fallback, 65)
            font_genres = font_synopsis = font_ep_sub = ImageFont.truetype(fallback, 28)
        except:
            font_title = font_genres = font_rating = font_synopsis = font_brand = font_ep_title = font_ep_sub = ImageFont.load_default()

    # 3. Title (Wrap 2 lines)
    disp_title = apply_small_caps(title) if small_caps else title
    if disp_title:
        title_lines = textwrap.wrap(disp_title, width=22)
        if len(title_lines) > 2:
            title_lines = title_lines[:2]
            title_lines[1] = title_lines[1] + "..."

        title_y = 200
        for line in title_lines:
            draw.text((1125, title_y), line, font=font_title, fill=(255, 255, 255, 255))
            title_y += 75

    # 4. Genres
    # Pill boxes at approx (1125, 380), (1335, 380), (1545, 380) with w~180
    genre_list = [g.strip() for g in genres.split(',')] if genres else []
    genre_coords = [(1125, 335), (1380, 335), (1640, 335)]
    genre_w = 230
    genre_h = 60
    for i, g in enumerate(genre_list[:3]):
        gx, gy = genre_coords[i]
        text_bbox = draw.textbbox((0, 0), apply_small_caps(g) if small_caps else g, font=font_genres)
        tw = text_bbox[2] - text_bbox[0]
        th = text_bbox[3] - text_bbox[1]

        tx = gx + (genre_w - tw) // 2
        ty = gy + (genre_h - th) // 2 - 5
        draw.text((tx, ty), apply_small_caps(g) if small_caps else g, font=font_genres, fill=(255, 255, 255, 255))

    # 5. Rating and Duration
    rating = str(imdb_data.get("rating", "N/A"))
    duration = str(imdb_data.get("duration", "N/A"))
    # Coordinates for text inside rating box: approx Rating (1140, 500), Duration (1340, 500)
    draw.text((1140, 480), rating, font=font_rating, fill=(255, 255, 255, 255))
    draw.text((1340, 480), duration.replace(" min", ""), font=font_rating, fill=(255, 255, 255, 255))

    # 6. Synopsis
    if synopsis:
        clean_synopsis = re.sub(r'<[^>]+>', '', synopsis)
        synopsis_lines = textwrap.wrap(clean_synopsis, width=58)

        max_lines = 4
        if len(synopsis_lines) > max_lines:
            synopsis_lines = synopsis_lines[:max_lines]
            synopsis_lines[-1] = synopsis_lines[-1][: -12] + "...read more"

        syn_y = 590
        for line in synopsis_lines:
            draw.text((1140, syn_y), line, font=font_synopsis, fill=(180, 180, 180, 255))
            syn_y += 35

    # 7. Episodes Section
    eps = imdb_data.get("episodes", [])
    ep_coords = [
        {"box": (198, 830, 345, 965), "title_pos": (390, 830), "sub_pos": (390, 915), "ep_num": "E01"},
        {"box": (1028, 830, 1175, 965), "title_pos": (1220, 830), "sub_pos": (1220, 915), "ep_num": "E02"}
    ]

    for i, ep_info in enumerate(ep_coords):
        if i < len(eps):
            ep = eps[i]

            # Draw EP Title
            ep_title_text = f"{ep_info['ep_num']} • {ep['title']}"
            if len(ep_title_text) > 22:
                ep_title_text = ep_title_text[:20] + "..."
            draw.text(ep_info["title_pos"], ep_title_text, font=font_ep_title, fill=(255, 255, 255, 255))

            # Draw Sub (Rating / Duration)
            ep_sub_text = f"⭐ {ep['rating']}   🕒 {ep['duration']}"
            draw.text(ep_info["sub_pos"], ep_sub_text, font=font_ep_sub, fill=(180, 180, 180, 255))

            # Paste Thumbnail
            thumb_img = None
            if ep.get("image"):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(ep["image"]) as resp:
                            if resp.status == 200:
                                img_data = await resp.read()
                                thumb_img = Image.open(io.BytesIO(img_data)).convert("RGBA")
                except:
                    pass

            if not thumb_img:
                thumb_img = Image.new("RGBA", (200, 200), (80, 80, 80, 255))

            try:
                box_rect = ep_info["box"]
                box_w = box_rect[2] - box_rect[0]
                box_h = box_rect[3] - box_rect[1]

                # Crop to fit square perfectly
                img_w, img_h = thumb_img.size
                scale = max(box_w / img_w, box_h / img_h)
                new_w, new_h = int(img_w * scale), int(img_h * scale)
                thumb_img = thumb_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                # Center crop
                left = (new_w - box_w) // 2
                top = (new_h - box_h) // 2
                thumb_img = thumb_img.crop((left, top, left + box_w, top + box_h))

                # Mask rounded rect
                temp_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
                temp_layer.paste(thumb_img, (box_rect[0], box_rect[1]))

                mask = Image.new("L", base.size, 0)
                draw_mask = ImageDraw.Draw(mask)
                draw_mask.rounded_rectangle(box_rect, radius=20, fill=255)

                base.paste(temp_layer, (0, 0), mask)
            except:
                pass

    # 8. Branding & Logo
    disp_username = apply_small_caps(username) if small_caps else username
    if disp_username:
        # Search bar is approx at (260, 45) to (500, 85)
        text_bbox = draw.textbbox((0, 0), disp_username, font=font_brand)
        tw = text_bbox[2] - text_bbox[0]
        th = text_bbox[3] - text_bbox[1]

        # Center horizontally around 370, vertically around 65
        draw.text((280, 45), disp_username, font=font_brand, fill=(180, 180, 180, 255))

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

            logo_img.thumbnail((70, 70), Image.Resampling.LANCZOS)
            lw, lh = logo_img.size
            # Top right circle approx center is (1820, 65)
            lx = 1795 + (70 - lw) // 2
            ly = 40 + (70 - lh) // 2

            # Mask to circle
            mask = Image.new("L", (lw, lh), 0)
            d_mask = ImageDraw.Draw(mask)
            d_mask.ellipse((0, 0, lw, lh), fill=255)

            base.paste(logo_img, (lx, ly), mask)
        except Exception as e:
            pass

    out_bio = io.BytesIO()
    base.convert("RGB").save(out_bio, format="JPEG", quality=90)
    out_bio.name = "poster3.jpg"
    out_bio.seek(0)
    return out_bio
