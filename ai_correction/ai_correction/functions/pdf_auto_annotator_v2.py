import tkinter as tk
from tkinter import filedialog, messagebox
import os
import sys
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import black

class PDFAutoAnnotator:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Auto Annotator")
        
        # Create main frame
        self.main_frame = tk.Frame(root)
        self.main_frame.pack(padx=10, pady=10)
        
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
        self.answer_path = None
        self.annotation_path = None

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
        if not all([self.answer_path, self.annotation_path]):
            messagebox.showerror("Error", "Please select all required files")
            return

        try:
            # Read answer and annotation files
            with open(self.answer_path, 'r', encoding='utf-8') as f:
                answer_text = f.read()
            
            with open(self.annotation_path, 'r', encoding='utf-8') as f:
                annotation_text = f.read()

            # Save the new PDF
            output_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                initialfile="annotated_output.pdf"
            )
            
            if output_path:
                # Create PDF
                c = canvas.Canvas(output_path, pagesize=letter)
                width, height = letter

                # Add answer page
                c.setFont("Helvetica-Bold", 14)
                c.drawString(50, height - 50, "Answers:")
                c.setFont("Helvetica", 12)
                y = height - 80
                for line in answer_text.split('\n'):
                    c.drawString(50, y, line)
                    y -= 20
                    if y < 50:  # New page if needed
                        c.showPage()
                        y = height - 50
                
                # Add annotation page
                c.showPage()
                c.setFont("Helvetica-Bold", 14)
                c.drawString(50, height - 50, "Annotations:")
                c.setFont("Helvetica", 12)
                y = height - 80
                for line in annotation_text.split('\n'):
                    c.drawString(50, y, line)
                    y -= 20
                    if y < 50:  # New page if needed
                        c.showPage()
                        y = height - 50

                c.save()
                messagebox.showinfo("Success", f"Annotated PDF saved as: {output_path}")

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = PDFAutoAnnotator(root)
        root.mainloop()
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        sys.exit(1)