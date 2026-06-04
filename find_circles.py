from PIL import Image
import cv2
import numpy as np

img = Image.open('assets/poster3_template.png').convert('RGB')
cv_img = np.array(img)
gray = cv2.cvtColor(cv_img, cv2.COLOR_RGB2GRAY)

# Threshold to find white boxes
_, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)

# Detect circles using HoughCircles
circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, dp=1.2, minDist=20, param1=50, param2=30, minRadius=5, maxRadius=50)

if circles is not None:
    circles = np.round(circles[0, :]).astype("int")
    for (x, y, r) in circles:
        print(f"Circle found at X:{x}, Y:{y}, Radius:{r}")
else:
    print("No circles found.")
