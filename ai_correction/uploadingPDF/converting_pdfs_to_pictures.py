"""这个程序需要在https://github.com/oschwartz10612/poppler-windows/releases下载poppler才能运行"""
from pdf2image import convert_from_path
import os

# Define your PDF and output folder
pdf_path = "D:/Git/project/test/ap23-frq-calculus-bc.pdf"
output_folder = r"D:/Git/project/test/pictures"

# Make sure the output folder exists
os.makedirs(output_folder, exist_ok=True)

# Convert PDF to images
images = convert_from_path(pdf_path, poppler_path=r"D:/Git/project/poppler-24.08.0/Library\bin")

# Save each image to the output folder
for i, img in enumerate(images):
    img_path = os.path.join(output_folder, f"page_{i + 1}.png")
    img.save(img_path, "PNG")
    print(f"Saved: {img_path}")