import tkinter as tk
from tkinter import filedialog, messagebox
import fitz  # PyMuPDF
import os

class PDFAutoAnnotator:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Auto Annotator")
        
        # Create main frame
        self.main_frame = tk.Frame(root)
        self.main_frame.pack(padx=10, pady=10)
        
        # PDF file selection
        self.pdf_label = tk.Label(self.main_frame, text="Select PDF File:")
        self.pdf_label.pack()
        self.pdf_button = tk.Button(self.main_frame, text="Choose PDF", command=self.select_pdf)
        self.pdf_button.pack(pady=5)
        
        # Answer file selection
        self.answer_label = tk.Label(self.main_frame, text="Select Answer File (.txt):")
        self.answer_label.pack()
        self.answer_button = tk.Button(self.main_frame, text="Choose Answer File", command=self.select_answer)
        self.answer_button.pack(pady=5)
        
        # Annotation file selection
        self.annotation_label = tk.Label(self.main_frame, text="Select Annotation File (.txt):")
        self.annotation_label.pack()
        self.annotation_button = tk.Button(self.main_frame, text="Choose Annotation File", command=self.select_annotation)
        self.annotation_button.pack(pady=5)
        
        # Process button
        self.process_button = tk.Button(self.main_frame, text="Process and Save", command=self.process_files)
        self.process_button.pack(pady=20)
        
        # File paths
        self.pdf_path = None
        self.answer_path = None
        self.annotation_path = None

    def select_pdf(self):
        file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if file_path:
            self.pdf_path = file_path
            self.pdf_label.config(text=f"PDF: {os.path.basename(file_path)}")

    def select_answer(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if file_path:
            self.answer_path = file_path
            self.answer_label.config(text=f"Answer: {os.path.basename(file_path)}")

    def select_annotation(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if file_path:
            self.annotation_path = file_path
            self.annotation_label.config(text=f"Annotation: {os.path.basename(file_path)}")

    def process_files(self):
        if not all([self.pdf_path, self.answer_path, self.annotation_path]):
            messagebox.showerror("Error", "Please select all required files")
            return

        try:
            # Open PDF document
            pdf_document = fitz.open(self.pdf_path)
            
            # Read answer and annotation files
            with open(self.answer_path, 'r', encoding='utf-8') as f:
                answer_text = f.read()
            
            with open(self.annotation_path, 'r', encoding='utf-8') as f:
                annotation_text = f.read()

            # Create a new page for answers and annotations
            new_page = pdf_document.new_page()
            
            # Add answer text
            new_page.insert_text((50, 50), "Answers:", fontsize=14, color=(0, 0, 0))
            new_page.insert_text((50, 80), answer_text, fontsize=12, color=(0, 0, 0))
            
            # Add annotation text
            new_page.insert_text((50, 300), "Annotations:", fontsize=14, color=(0, 0, 0))
            new_page.insert_text((50, 330), annotation_text, fontsize=12, color=(0, 0, 0))

            # Save the new PDF
            output_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                initialfile="annotated_output.pdf"
            )
            
            if output_path:
                pdf_document.save(output_path)
                pdf_document.close()
                messagebox.showinfo("Success", f"Annotated PDF saved as: {output_path}")
            else:
                pdf_document.close()
                messagebox.showinfo("Info", "Operation cancelled")

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFAutoAnnotator(root)
    root.mainloop() 