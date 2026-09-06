# ==========================================
# FINAL POSTER 4 GENERATION (PERFECT REMBG & LAYOUT)
# ==========================================
async def generate_poster_4(anime_img_url=None, custom_image_path=None, title="", genres="", synopsis="", username="", logo_url=None, small_caps=False, color_hex="#007BFF", offset_x=0, offset_y=0, zoom_scale=1.0, release_year="", episodes="", seasons=""):
    import numpy as np
    import textwrap
    import io
    import os
    import re
    import aiohttp
    from PIL import Image, ImageDraw, ImageFont

    template_path = 'plugins/assets/poster4.png'
    template_img = Image.open(template_path).convert('RGBA')

    # STEP 1: FAST VIBGYOR THEME CHAMELEON (Fix for black edges on button)
    arr = np.array(template_img, dtype=np.float32)
    target_hex = color_hex.lstrip('#')
    tr, tg, tb = tuple(int(target_hex[i:i+2], 16) for i in (0, 2, 4))

    r, g, b, a = arr[:,:,0], arr[:,:,1], arr[:,:,2], arr[:,:,3]
    # Made the mask slightly more aggressive to catch dark anti-aliased blue edges around buttons
    blue_mask = (b > r + 15) & (b > g + 15) & (a > 10)
    
    arr[blue_mask, 0] = tr
    arr[blue_mask, 1] = tg
    arr[blue_mask, 2] = tb
    template_img = Image.fromarray(arr.astype(np.uint8))

    # STEP 2: HIGH-QUALITY BACKGROUND REMOVAL & ENHANCEMENT
    try:
        if custom_image_path:
            char_img = Image.open(custom_image_path).convert("RGBA")
        elif anime_img_url:
            async with aiohttp.ClientSession() as session:
                async with session.get(anime_img_url, headers={'User-Agent': 'Mozilla/5.0'}) as resp:
                    if resp.status == 200:
                        char_img = Image.open(io.BytesIO(await resp.read())).convert("RGBA")
                    else:
                        char_img = Image.new("RGBA", (100, 100), (0,0,0,0))
        else:
            char_img = Image.new("RGBA", (100, 100), (0,0,0,0))

        # We REMOVED the pre-compression here so the AI doesn't accidentally cut off hands/limbs!
        
        # Process through rembg for PERFECT edges
        try:
            import rembg
            # post_process_mask=True ensures the AI recovers foreground details accurately
            char_img = rembg.remove(char_img, post_process_mask=True)
            char_img = enhance_image(char_img) # Enhance colors & sharpness
        except Exception as e:
            pass 

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
    FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")
    try:
        font_large = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Black.ttf"), 70)
        font_meta = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Bold.ttf"), 26) 
        font_synopsis = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto-Medium.ttf"), 24)
        font_brand = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto Bold.ttf"), 35)
    except Exception as e:
        raise Exception("Failed to load required custom fonts.")

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

    # STEP 4: TYPOGRAPHY & LAYOUT (Left Side)
    disp_title = apply_small_caps(title) if small_caps else title
    title_words = disp_title.split() if disp_title else []

    def draw_colored_text(draw_obj, text_words, start_x, start_y, font, highlight_idx):
        cx = start_x
        for i, word in enumerate(text_words):
            color = f"#{target_hex}" if i == highlight_idx else "#000000"
            draw_obj.text((cx, start_y), word + " ", font=font, fill=color)
            w = draw_obj.textlength(word + " ", font=font)
            cx += w

    # The Title (Safely placed at Y=140)
    ty = 140
    if len(title_words) > 3:
        line1_words = title_words[:3]
        if len(title_words) > 7:
            line2_words = title_words[3:7] + ["..."]
        else:
            line2_words = title_words[3:]

        draw_colored_text(draw, line1_words, 100, ty, font_large, -1) 
        ty += 80
        draw_colored_text(draw, line2_words, 100, ty, font_large, len(line2_words) - 1) 
    else:
        draw_colored_text(draw, title_words, 100, ty, font_large, len(title_words) - 1)

    # The Genres & Metadata (Directly below Crunchyroll, around Y=290)
    genres_formatted = ""
    if genres:
        # Title case format: Action • Adventure • Fantasy
        genres_list = [g.strip().capitalize() for g in genres.split(",")]
        genres_formatted = " • ".join(genres_list)
    else:
        genres_formatted = "Unknown"
        
    release_year = release_year if release_year else "N/A"
    episodes = episodes if episodes else "N/A"
    seasons = seasons if seasons else "N/A"

    meta_y = 290
    metadata_text = f"{release_year} | {genres_formatted} | {episodes} (EPS) | {seasons} SEASON"
    draw.text((100, meta_y), metadata_text, font=font_meta, fill=(180, 180, 180, 255))

    # The Synopsis (Directly below Metadata, around Y=340)
    syn_y = 340
    if synopsis:
        clean_synopsis = re.sub(r'<[^>]+>', '', synopsis)
        words = clean_synopsis.split()
        if len(words) > 55: 
            clean_synopsis = " ".join(words[:55]) + "...read more"

        lines = textwrap.wrap(clean_synopsis, width=70) 
        wrapped_synopsis = "\n".join(lines)
        draw.multiline_text((100, syn_y), wrapped_synopsis, font=font_synopsis, fill=(120, 120, 120, 255), spacing=10)

    out_bio = io.BytesIO()
    base.convert("RGB").save(out_bio, format="JPEG", quality=100)
    out_bio.name = "poster4.jpg"
    out_bio.seek(0)
    return out_bio
