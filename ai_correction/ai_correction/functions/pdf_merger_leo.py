import os
from PIL import Image
import streamlit as st # type: ignore
from PyPDF2 import PdfReader, PdfWriter
from fpdf import FPDF
from pathlib import Path

class ImageToPDFConverter:
    def __init__(self, upload_dir=None):
        self.upload_dir = upload_dir or Path("uploads")
        self.upload_dir.mkdir(exist_ok=True)
        
    def convert_image_to_pdf(self, image_path):
        """Convert a single image to PDF."""
        try:
            # Get image file name without extension
            image_name = os.path.splitext(os.path.basename(image_path))[0]
            
            # Create PDF
            pdf = FPDF()
            pdf.add_page()
            
            # Open image and get dimensions
            img = Image.open(image_path)
            width, height = img.size
            
            # Calculate image size to fit on PDF page (maintaining aspect ratio)
            pdf_width = pdf.w - 20  # Margins
            pdf_height = pdf.h - 20  # Margins
            
            ratio = min(pdf_width/width, pdf_height/height)
            new_width = width * ratio
            new_height = height * ratio
            
            # Add image to PDF
            pdf.image(image_path, x=10, y=10, w=new_width, h=new_height)
            
            # Output path
            output_path = os.path.join(os.path.dirname(image_path), f"{image_name}.pdf")
            pdf.output(output_path)
            
            return output_path
        
        except Exception as e:
            raise Exception(f"Error converting image to PDF: {str(e)}")
    
    def convert_multiple_images_to_pdf(self, image_paths, output_path=None):
        """Convert multiple images to a single PDF."""
        try:
            # Create PDF
            pdf = FPDF()
            
            for img_path in image_paths:
                pdf.add_page()
                
                # Open image and get dimensions
                img = Image.open(img_path)
                width, height = img.size
                
                # Calculate image size to fit on PDF page (maintaining aspect ratio)
                pdf_width = pdf.w - 20  # Margins
                pdf_height = pdf.h - 20  # Margins
                
                ratio = min(pdf_width/width, pdf_height/height)
                new_width = width * ratio
                new_height = height * ratio
                
                # Add image to PDF
                pdf.image(img_path, x=10, y=10, w=new_width, h=new_height)
            
            # Output path
            if output_path is None:
                output_path = os.path.join(self.upload_dir, "converted_images.pdf")
            
            pdf.output(output_path)
            return output_path
            
        except Exception as e:
            raise Exception(f"Error converting images to PDF: {str(e)}")
    
    def add_annotations_to_pdf(self, pdf_path, answer_text, annotation_text):
        """Add answer and annotation text to an existing PDF."""
        try:
            # Create PDF for annotations
            temp_pdf = FPDF()
            
            # Add answer section
            temp_pdf.add_page()
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
            temp_path = os.path.join(self.upload_dir, "temp_annotations.pdf")
            temp_pdf.output(temp_path)

            # Merge PDFs
            merger = PdfWriter()
            
            # Add original PDF
            original_pdf = PdfReader(pdf_path)
            for page in original_pdf.pages:
                merger.add_page(page)
            
            # Add annotations PDF
            annotations_pdf = PdfReader(temp_path)
            for page in annotations_pdf.pages:
                merger.add_page(page)

            # Get output filename from original PDF
            output_filename = f"annotated_{os.path.basename(pdf_path)}"
            output_path = os.path.join(self.upload_dir, output_filename)
            
            # Write the merged PDF
            with open(output_path, "wb") as output_file:
                merger.write(output_file)
            
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            return output_path
            
        except Exception as e:
            # Clean up temporary file in case of error
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
            raise Exception(f"Error adding annotations to PDF: {str(e)}")

def streamlit_image_to_pdf_converter():
    """Streamlit interface for the image to PDF converter."""
    st.title("Image to PDF Converter")
    
    # File upload section
    uploaded_images = st.file_uploader("Upload images", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    
    if uploaded_images:
        # Create converter instance
        converter = ImageToPDFConverter()
        
        # Save uploaded images
        image_paths = []
        for img in uploaded_images:
            img_path = os.path.join(converter.upload_dir, img.name)
            with open(img_path, "wb") as f:
                f.write(img.getbuffer())
            image_paths.append(img_path)
        
        # Convert button
        if st.button("Convert to PDF"):
            with st.spinner("Converting images to PDF..."):
                try:
                    output_path = converter.convert_multiple_images_to_pdf(image_paths)
                    
                    # Provide download link
                    with open(output_path, "rb") as f:
                        st.download_button(
                            label="Download PDF",
                            data=f.read(),
                            file_name=os.path.basename(output_path),
                            mime="application/pdf"
                        )
                    
                    st.success(f"Successfully converted {len(image_paths)} images to PDF!")
                    
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        
        # Optional annotation section
        with st.expander("Add Annotations"):
            answer_text = st.text_area("Answer Text", "", height=200)
            annotation_text = st.text_area("Annotation Text", "", height=200)
            
            if st.button("Add Annotations to PDF"):
                with st.spinner("Adding annotations..."):
                    try:
                        # First convert images if not already converted
                        pdf_path = os.path.join(converter.upload_dir, "converted_images.pdf")
                        if not os.path.exists(pdf_path):
                            pdf_path = converter.convert_multiple_images_to_pdf(image_paths, pdf_path)
                        
                        # Add annotations
                        output_path = converter.add_annotations_to_pdf(pdf_path, answer_text, annotation_text)
                        
                        # Provide download link
                        with open(output_path, "rb") as f:
                            st.download_button(
                                label="Download Annotated PDF",
                                data=f.read(),
                                file_name=os.path.basename(output_path),
                                mime="application/pdf"
                            )
                        
                        st.success("Successfully added annotations to PDF!")
                        
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    streamlit_image_to_pdf_converter()