import tkinter as tk
from tkinter import filedialog
import fitz  # PyMuPDF
from PIL import Image, ImageTk
import io

class PDFAnnotator:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Annotator")
        
        self.canvas = tk.Canvas(root, cursor="cross")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.open_button = tk.Button(root, text="Open PDF", command=self.open_pdf)
        self.open_button.pack(side=tk.TOP)
        
        self.annotate_button = tk.Button(root, text="Annotate", command=self.start_annotate)
        self.annotate_button.pack(side=tk.TOP)
        
        self.text_button = tk.Button(root, text="Add Text", command=self.add_text)
        self.text_button.pack(side=tk.TOP)
        
        self.save_button = tk.Button(root, text="Save Annotations", command=self.save_annotations)
        self.save_button.pack(side=tk.TOP)
        
        self.pdf_document = None
        self.current_page = 0
        self.annotations = []
        self.text_entries = []
        self.annotating = False
        self.start_x = None
        self.start_y = None

    def open_pdf(self):
        file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if file_path:
            self.pdf_document = fitz.open(file_path)
            self.show_page(0)

    def show_page(self, page_number):
        if self.pdf_document:
            page = self.pdf_document.load_page(page_number)
            pix = page.get_pixmap()
            img = Image.open(io.BytesIO(pix.tobytes()))
            self.tk_img = ImageTk.PhotoImage(image=img)
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)
            self.current_page = page_number

    def start_annotate(self):
        self.annotating = True
        self.canvas.bind("<Button-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

    def on_button_press(self, event):
        self.start_x = event.x
        self.start_y = event.y

    def on_mouse_drag(self, event):
        if self.annotating and self.start_x and self.start_y:
            self.canvas.create_line(self.start_x, self.start_y, event.x, event.y, fill="red", width=2)
            self.start_x = event.x
            self.start_y = event.y

    def on_button_release(self, event):
        self.start_x = None
        self.start_y = None

    def add_text(self):
        self.canvas.bind("<Button-1>", self.add_text_at_position)

    def add_text_at_position(self, event):
        text = tk.simpledialog.askstring("Input", "Enter text:")
        if text:
            self.canvas.create_text(event.x, event.y, text=text, fill="blue", font=("Arial", 12))
            self.text_entries.append((event.x, event.y, text))

    def save_annotations(self):
        if self.pdf_document:
            page = self.pdf_document.load_page(self.current_page)
            for annotation in self.annotations:
                page.draw_line(annotation[0], annotation[1], annotation[2], annotation[3], color=(1, 0, 0), width=2)
            for text_entry in self.text_entries:
                page.insert_text((text_entry[0], text_entry[1]), text_entry[2], fontsize=12, color=(0, 0, 1))
            self.pdf_document.save("annotated.pdf")
            tk.messagebox.showinfo("Info", "Annotations saved to annotated.pdf")

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFAnnotator(root)
    root.mainloop()