import tkinter as tk
from tkinter import filedialog, messagebox
import os
from fpdf import FPDF
from PyPDF2 import PdfReader, PdfWriter

class PDFMerger:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Merger")
        
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
        self.process_button = tk.Button(self.main_frame, text="Merge PDFs", command=self.merge_pdfs)
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

    def merge_pdfs(self):
        if not all([self.pdf_path, self.answer_path, self.annotation_path]):
            messagebox.showerror("Error", "Please select all required files")
            return

        try:
            # Read answer and annotation files
            with open(self.answer_path, 'r', encoding='utf-8') as f:
                answer_text = f.read()
            
            with open(self.annotation_path, 'r', encoding='utf-8') as f:
                annotation_text = f.read()

            # Create temporary PDF with answers and annotations
            temp_pdf = FPDF()
            temp_pdf.add_page()
            
            # Add answer section
            temp_pdf.set_font("Arial", 'B', 14)
            temp_pdf.cell(0, 10, "Answers:", ln=True)
            temp_pdf.set_font("Arial", '', 12)
            temp_pdf.multi_cell(0, 10, answer_text)
            
            # Add annotation section
            temp_pdf.add_page()
            temp_pdf.set_font("Arial", 'B', 14)
            temp_pdf.cell(0, 10, "Annotations:", ln=True)
            temp_pdf.set_font("Arial", '', 12)
            temp_pdf.multi_cell(0, 10, annotation_text)
            
            # Save temporary PDF
            temp_path = "temp_annotations.pdf"
            temp_pdf.output(temp_path)

            # Merge PDFs
            merger = PdfWriter()
            
            # Add original PDF
            original_pdf = PdfReader(self.pdf_path)
            for page in original_pdf.pages:
                merger.add_page(page)
            
            # Add annotations PDF
            annotations_pdf = PdfReader(temp_path)
            for page in annotations_pdf.pages:
                merger.add_page(page)

            # Save the merged PDF
            output_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                initialfile="merged_output.pdf"
            )
            
            if output_path:
                merger.write(output_path)
                merger.close()
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                messagebox.showinfo("Success", f"Merged PDF saved as: {output_path}")

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
            # Clean up temporary file in case of error
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFMerger(root)
    root.mainloop()
