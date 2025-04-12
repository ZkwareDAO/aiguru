import tkinter as tk
from tkinter import filedialog, messagebox
import os
from fpdf import FPDF

class PDFGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Generator")
        
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
        self.process_button = tk.Button(self.main_frame, text="Generate PDF", command=self.generate_pdf)
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

    def generate_pdf(self):
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
                initialfile="output.pdf"
            )
            
            if output_path:
                # Create PDF
                pdf = FPDF()
                pdf.add_page()
                
                # Add answer section
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(0, 10, "Answers:", ln=True)
                pdf.set_font("Arial", '', 12)
                pdf.multi_cell(0, 10, answer_text)
                
                # Add annotation section
                pdf.add_page()
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(0, 10, "Annotations:", ln=True)
                pdf.set_font("Arial", '', 12)
                pdf.multi_cell(0, 10, annotation_text)
                
                # Save PDF
                pdf.output(output_path)
                messagebox.showinfo("Success", f"PDF saved as: {output_path}")

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFGenerator(root)
    root.mainloop()