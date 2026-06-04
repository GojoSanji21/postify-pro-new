from PIL import Image

# The original poster3_template.png we downloaded was 640x360 which is tiny. We need to resize it to 1920x1080
# to have high quality output like Poster 1 and 2, but let's just make sure we are editing the existing file
# correctly. Wait, if it's 640x360, scaling it to 1920x1080 is exactly 3x. Let's do that to get good text resolution!
img = Image.open('assets/poster3_template.png')
img = img.resize((1920, 1080), Image.Resampling.LANCZOS)
img.save('assets/poster3_template_1080.png')
