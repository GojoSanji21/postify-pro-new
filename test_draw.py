from PIL import Image, ImageDraw
import cv2

# Draw bounding boxes and circles to visually inspect
img = Image.open('assets/poster3_template.png').convert('RGB')
draw = ImageDraw.Draw(img)

# From our contour search
boxes = [
    (344, 278, 50, 47),
    (67, 278, 49, 47),
    (16, 165, 12, 12),
    (67, 52, 268, 180)
]

for x, y, w, h in boxes:
    draw.rectangle([x, y, x+w, y+h], outline="red", width=2)

img.save('test_boxes.png')
