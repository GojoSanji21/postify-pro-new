from PIL import Image
import cv2
import numpy as np

img = Image.open('assets/poster3_template.png').convert('RGB')
cv_img = np.array(img)
gray = cv2.cvtColor(cv_img, cv2.COLOR_RGB2GRAY)

# Threshold to find white boxes
_, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

for c in contours:
    x, y, w, h = cv2.boundingRect(c)
    if w > 10 and h > 10:
        print(f"White Box found at X:{x}, Y:{y}, W:{w}, H:{h}")
