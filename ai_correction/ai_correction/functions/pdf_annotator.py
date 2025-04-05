import fitz  # PyMuPDF
import streamlit as st
import io
from PIL import Image
import os

class PDFAnnotator:
    def __init__(self):
        self.pdf_document = None
        self.current_page = 0
        self.annotations = []
        self.text_entries = []
        self.annotating = False
        self.start_x = None
        self.start_y = None

    def open_pdf(self, file_path):
        """打开PDF文件"""
        try:
            self.pdf_document = fitz.open(file_path)
            return True
        except Exception as e:
            st.error(f"无法打开PDF文件: {str(e)}")
            return False

    def get_page_image(self, page_number):
        """获取指定页面的图像"""
        if self.pdf_document and 0 <= page_number < len(self.pdf_document):
            page = self.pdf_document.load_page(page_number)
            pix = page.get_pixmap()
            img_bytes = pix.tobytes()
            img = Image.open(io.BytesIO(img_bytes))
            return img
        return None

    def add_annotation(self, page_number, start_x, start_y, end_x, end_y, annotation_type="line", text="", color=(1, 0, 0)):
        """添加标注"""
        if annotation_type == "line":
            self.annotations.append((page_number, start_x, start_y, end_x, end_y, color))
        elif annotation_type == "text":
            self.text_entries.append((page_number, start_x, start_y, text, color))

    def save_annotations(self, output_path):
        """保存带有标注的PDF"""
        if not self.pdf_document:
            st.error("没有打开的PDF文件")
            return False

        try:
            # 处理每个页面上的标注
            for page_num, start_x, start_y, end_x, end_y, color in self.annotations:
                if 0 <= page_num < len(self.pdf_document):
                    page = self.pdf_document.load_page(page_num)
                    page.draw_line((start_x, start_y), (end_x, end_y), color=color, width=2)

            # 处理文本标注
            for page_num, x, y, text, color in self.text_entries:
                if 0 <= page_num < len(self.pdf_document):
                    page = self.pdf_document.load_page(page_num)
                    page.insert_text((x, y), text, fontsize=12, color=color)

            # 保存文件
            self.pdf_document.save(output_path)
            return True
        except Exception as e:
            st.error(f"保存标注时出错: {str(e)}")
            return False

def streamlit_pdf_annotator(pdf_file, user_dir):
    """Streamlit界面的PDF标注功能"""
    st.subheader("PDF标注工具")
    
    # 初始化标注器
    if 'pdf_annotator' not in st.session_state:
        st.session_state.pdf_annotator = PDFAnnotator()
        st.session_state.current_page = 0
        st.session_state.annotations = []
        st.session_state.text_entries = []
    
    # 保存上传的PDF文件
    if pdf_file:
        timestamp = pdf_file.name
        pdf_path = os.path.join(user_dir, timestamp)
        with open(pdf_path, "wb") as f:
            f.write(pdf_file.getbuffer())
        
        # 打开PDF文件
        if st.session_state.pdf_annotator.open_pdf(pdf_path):
            st.success(f"成功打开PDF文件: {pdf_file.name}")
            
            # 显示PDF页面
            total_pages = len(st.session_state.pdf_annotator.pdf_document)
            st.session_state.current_page = st.slider("选择页面", 0, max(0, total_pages-1), st.session_state.current_page)
            
            # 获取当前页面图像
            img = st.session_state.pdf_annotator.get_page_image(st.session_state.current_page)
            if img:
                st.image(img, caption=f"第 {st.session_state.current_page+1} 页，共 {total_pages} 页")
            
            # 标注控制
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("添加线条标注"):
                    st.session_state.annotating = True
                    st.session_state.annotation_type = "line"
                    st.info("请在图像上点击并拖动来添加线条标注")
            
            with col2:
                if st.button("添加文本标注"):
                    st.session_state.annotating = True
                    st.session_state.annotation_type = "text"
                    st.info("请在图像上点击来添加文本标注")
            
            with col3:
                if st.button("保存标注"):
                    output_path = os.path.join(user_dir, f"annotated_{timestamp}")
                    if st.session_state.pdf_annotator.save_annotations(output_path):
                        st.success(f"标注已保存到: {output_path}")
                        # 提供下载链接
                        with open(output_path, "rb") as f:
                            st.download_button(
                                label="下载标注后的PDF",
                                data=f,
                                file_name=f"annotated_{pdf_file.name}",
                                mime="application/pdf"
                            )
            
            # 模拟标注功能（在Streamlit中无法直接在图像上交互，这里简化处理）
            if st.session_state.annotating:
                if st.session_state.annotation_type == "line":
                    col1, col2 = st.columns(2)
                    with col1:
                        start_x = st.number_input("起始X坐标", 0, 1000, 100)
                        start_y = st.number_input("起始Y坐标", 0, 1000, 100)
                    with col2:
                        end_x = st.number_input("结束X坐标", 0, 1000, 200)
                        end_y = st.number_input("结束Y坐标", 0, 1000, 200)
                    
                    if st.button("添加此线条"):
                        st.session_state.pdf_annotator.add_annotation(
                            st.session_state.current_page, start_x, start_y, end_x, end_y, "line"
                        )
                        st.session_state.annotations.append(
                            (st.session_state.current_page, start_x, start_y, end_x, end_y, (1, 0, 0))
                        )
                        st.success("线条标注已添加")
                
                elif st.session_state.annotation_type == "text":
                    col1, col2 = st.columns(2)
                    with col1:
                        text_x = st.number_input("文本X坐标", 0, 1000, 100)
                        text_y = st.number_input("文本Y坐标", 0, 1000, 100)
                    with col2:
                        annotation_text = st.text_input("输入标注文本")
                    
                    if st.button("添加此文本"):
                        st.session_state.pdf_annotator.add_annotation(
                            st.session_state.current_page, text_x, text_y, 0, 0, "text", annotation_text
                        )
                        st.session_state.text_entries.append(
                            (st.session_state.current_page, text_x, text_y, annotation_text, (0, 0, 1))
                        )
                        st.success("文本标注已添加")
        else:
            st.error("无法打开PDF文件")
    else:
        st.info("请上传PDF文件进行标注")