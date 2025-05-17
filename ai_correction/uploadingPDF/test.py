import fitz
doc = fitz.open("example.pdf")
for page in doc:
    text = page.get_text()
    print(text)