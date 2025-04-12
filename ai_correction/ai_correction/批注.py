import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
import fitz  # PyMuPDF
from PIL import Image, ImageTk
import io

class PDFEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF 编辑器")
        
        # 初始化变量
        self.pdf_document = None
        self.current_page = 0
        self.tk_images = []  # 保存所有页面的图像引用
        
        # 创建界面
        self.create_widgets()
        
    def create_widgets(self):
        # 顶部按钮栏
        button_frame = tk.Frame(self.root)
        button_frame.pack(fill=tk.X)
        
        tk.Button(button_frame, text="打开PDF", command=self.open_pdf).pack(side=tk.LEFT)
        tk.Button(button_frame, text="上一页", command=self.prev_page).pack(side=tk.LEFT)
        tk.Button(button_frame, text="下一页", command=self.next_page).pack(side=tk.LEFT)
        tk.Button(button_frame, text="添加空白页", command=self.add_blank_page).pack(side=tk.LEFT)
        tk.Button(button_frame, text="添加文本", command=self.add_text).pack(side=tk.LEFT)
        tk.Button(button_frame, text="保存PDF", command=self.save_pdf).pack(side=tk.LEFT)
        
        # 页面显示区域
        self.canvas = tk.Canvas(self.root, bg="white", width=600, height=800)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # 状态栏
        self.status = tk.Label(self.root, text="请打开一个PDF文件", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(fill=tk.X)
    
    def open_pdf(self):
        file_path = filedialog.askopenfilename(filetypes=[("PDF文件", "*.pdf")])
        if file_path:
            try:
                self.pdf_document = fitz.open(file_path)
                self.current_page = 0
                self.tk_images = []  # 清除之前的图像引用
                self.show_page()
                self.update_status(f"已打开: {file_path} | 页数: {len(self.pdf_document)}")
            except Exception as e:
                messagebox.showerror("错误", f"无法打开PDF文件:\n{e}")
    
    def show_page(self):
        if not self.pdf_document:
            return
            
        self.canvas.delete("all")  # 清除画布
        
        # 获取当前页并转换为图像
        page = self.pdf_document.load_page(self.current_page)
        pix = page.get_pixmap()
        img = Image.open(io.BytesIO(pix.tobytes()))
        
        # 调整图像大小以适应画布
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        img_ratio = img.width / img.height
        canvas_ratio = canvas_width / canvas_height
        
        if img_ratio > canvas_ratio:
            new_width = canvas_width
            new_height = int(canvas_width / img_ratio)
        else:
            new_height = canvas_height
            new_width = int(canvas_height * img_ratio)
            
        img = img.resize((new_width, new_height), Image.LANCZOS)
        
        # 显示图像
        self.tk_img = ImageTk.PhotoImage(img)
        self.tk_images.append(self.tk_img)  # 保存引用防止被垃圾回收
        self.canvas.create_image(
            canvas_width//2, canvas_height//2,
            anchor=tk.CENTER, image=self.tk_img
        )
        
        self.update_status(f"当前页: {self.current_page + 1}/{len(self.pdf_document)}")
    
    def prev_page(self):
        if self.pdf_document and self.current_page > 0:
            self.current_page -= 1
            self.show_page()
    
    def next_page(self):
        if self.pdf_document and self.current_page < len(self.pdf_document) - 1:
            self.current_page += 1
            self.show_page()
    
    def add_blank_page(self):
        if not self.pdf_document:
            messagebox.showwarning("警告", "请先打开一个PDF文件")
            return
            
        # 在当前页后插入空白页
        new_page = self.pdf_document.new_page(-1, width=595, height=842)  # A4尺寸
        
        # 更新显示
        self.current_page = len(self.pdf_document) - 1
        self.show_page()
        messagebox.showinfo("成功", "已添加空白页")
    
    def add_text(self):
        if not self.pdf_document:
            messagebox.showwarning("警告", "请先打开一个PDF文件")
            return
            
        # 获取文本内容和位置
        text = simpledialog.askstring("添加文本", "输入要添加的文本:")
        if not text:
            return
            
        # 获取鼠标点击位置
        messagebox.showinfo("提示", "请在页面上点击要添加文本的位置")
        self.canvas.bind("<Button-1>", lambda e: self.insert_text(e, text))
    
    def insert_text(self, event, text):
        self.canvas.unbind("<Button-1>")
        
        # 将画布坐标转换为PDF坐标
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # 获取当前页的实际显示尺寸
        page = self.pdf_document.load_page(self.current_page)
        pdf_width = page.rect.width
        pdf_height = page.rect.height
        
        # 计算PDF坐标
        x = (event.x / canvas_width) * pdf_width
        y = (event.y / canvas_height) * pdf_height
        
        # 在PDF中添加文本
        page.insert_text(
            point=(x, y),
            text=text,
            fontsize=12,
            color=(0, 0, 0),  # 黑色
            fontname="helv"   # 标准字体
        )
        
        # 刷新显示
        self.show_page()
        messagebox.showinfo("成功", "文本已添加")
    
    def save_pdf(self):
        if not self.pdf_document:
            messagebox.showwarning("警告", "没有可保存的PDF")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF文件", "*.pdf")]
        )
        
        if file_path:
            try:
                self.pdf_document.save(file_path)
                messagebox.showinfo("成功", f"PDF已保存到:\n{file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败:\n{e}")
    
    def update_status(self, message):
        self.status.config(text=message)
        self.root.update()

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFEditor(root)
    root.geometry("800x900")
    root.mainloop()