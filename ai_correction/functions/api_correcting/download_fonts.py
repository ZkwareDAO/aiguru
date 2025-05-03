import os
import urllib.request
import shutil
from pathlib import Path

def download_font(font_url, save_path):
    """下载字体文件到指定路径"""
    try:
        print(f"Downloading font from {font_url} to {save_path}")
        # 设置User-Agent以避免被服务器拒绝
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        request = urllib.request.Request(font_url, headers=headers)
        with urllib.request.urlopen(request) as response, open(save_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        print(f"Font downloaded successfully: {os.path.basename(save_path)}")
        return True
    except Exception as e:
        print(f"Error downloading font: {str(e)}")
        return False

def main():
    # 创建字体目录
    font_dir = Path(__file__).parent / 'fonts'
    font_dir.mkdir(exist_ok=True)
    
    # 定义要下载的开源中文字体
    fonts = [
        # Google Noto Sans SC - 谷歌思源黑体简体中文
        {
            "name": "Noto Sans SC",
            "url": "https://raw.githubusercontent.com/googlefonts/noto-cjk/main/Sans/OTF/SimplifiedChinese/NotoSansSC-Regular.otf",
            "file_name": "NotoSansSC-Regular.otf"
        },
        # 方正黑体 - 免费可商用的黑体
        {
            "name": "FangZheng-HeiTi",
            "url": "https://raw.githubusercontent.com/Shutdoor/MADFET_res/6db7c76dae41ef1beaf8ade18a09fb82e22bf0e5/font/fzht.ttf",
            "file_name": "fzht.ttf"
        }
    ]
    
    downloaded_any = False
    
    # 下载所有字体
    for font in fonts:
        font_path = font_dir / font["file_name"]
        if not font_path.exists():
            print(f"Downloading {font['name']}...")
            if download_font(font["url"], str(font_path)):
                print(f"{font['name']} downloaded successfully.")
                downloaded_any = True
            else:
                print(f"Failed to download {font['name']}.")
        else:
            print(f"{font['name']} already exists.")
            downloaded_any = True
    
    if not downloaded_any:
        print("\nWARNING: Could not download any fonts. Downloading a fallback font...")
        # 最后的手动方法 - 创建一个简单的测试文件告诉用户如何手动安装字体
        help_file = font_dir / "FONT_INSTALL_HELP.txt"
        with open(help_file, "w", encoding="utf-8") as f:
            f.write("""字体下载失败，要显示中文，请手动执行以下操作:

1. 下载以下任一开源中文字体:
   - 方正黑体: https://www.foundertype.com/ (需注册)
   - 思源黑体: https://github.com/adobe-fonts/source-han-sans/releases/tag/2.004R

2. 将下载的字体文件(.ttf或.otf)复制到此目录中。

3. 重启应用程序。
""")
            print(f"Created help file: {help_file}")
    
    print("\nFont download process completed.")
    print("Font directory:", font_dir)
    print("Available fonts:")
    for f in font_dir.glob("*"):
        if f.is_file():
            print(f"- {f.name} ({f.stat().st_size / 1024:.2f} KB)")

if __name__ == "__main__":
    main() 