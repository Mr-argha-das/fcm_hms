import cv2
import pytesseract
import re

image_path = "cda059353e798192917fd975f9c413cc.jpg"  # 👈 apni image name

# read image
img = cv2.imread(image_path)

# convert to gray
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# improve clarity
gray = cv2.GaussianBlur(gray, (5,5), 0)
thresh = cv2.adaptiveThreshold(gray,255,
                               cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY,11,2)

# OCR
text = pytesseract.image_to_string(thresh)

print("Full OCR Text:\n", text)

# 12 digit search
pattern = r"\d{4}\s?\d{4}\s?\d{4}"

match = re.search(pattern, text)

if match:
    aadhaar = match.group().replace(" ", "")
    print("\n✅ Aadhaar Number:", aadhaar)
else:
    print("\n❌ Aadhaar not found")
