# Python版本切换指南 - 从Anaconda Python 3.7到Python 3.13.5

## 🔍 问题诊断

您的系统中已经正确安装了Python 3.13.5，但当前终端仍在使用Anaconda的Python 3.7.0。

### 当前状态
- ✅ **Python 3.13.5已安装**: `C:\Users\Administrator\AppData\Local\Programs\Python\Python313\`
- ✅ **PATH环境变量已设置**: Python 3.13路径已添加到系统PATH
- ❌ **终端仍使用旧版本**: 当前终端会话仍指向Anaconda Python 3.7

## 🛠️ 解决方案

### 方案1：重启终端/命令提示符（推荐）

1. **关闭所有当前的终端窗口**
2. **重新打开命令提示符或PowerShell**
3. **验证Python版本**：
   ```cmd
   python --version
   ```
   应该显示：`Python 3.13.5`

### 方案2：在当前会话中临时切换

如果不想重启终端，可以在当前会话中临时设置：

```cmd
# 设置临时PATH，将Python 3.13放在最前面
set PATH=C:\Users\Administrator\AppData\Local\Programs\Python\Python313;C:\Users\Administrator\AppData\Local\Programs\Python\Python313\Scripts;%PATH%

# 验证版本
python --version
```

### 方案3：直接使用完整路径

```cmd
# 直接使用Python 3.13
C:\Users\Administrator\AppData\Local\Programs\Python\Python313\python.exe --version

# 使用Python 3.13的pip
C:\Users\Administrator\AppData\Local\Programs\Python\Python313\python.exe -m pip --version
```

### 方案4：创建批处理文件（永久解决）

创建一个批处理文件来自动设置环境：

```batch
@echo off
echo 切换到Python 3.13.5环境...
set PATH=C:\Users\Administrator\AppData\Local\Programs\Python\Python313;C:\Users\Administrator\AppData\Local\Programs\Python\Python313\Scripts;%PATH%
echo Python版本:
python --version
echo pip版本:
pip --version
echo 环境设置完成！
cmd /k
```

## 🚀 解决批改系统问题的完整步骤

### 步骤1：切换到Python 3.13.5

使用上述任一方案切换到Python 3.13.5

### 步骤2：安装必要的库

```cmd
# 安装最新版本的OpenAI库
pip install openai

# 安装文档处理库（多模态大模型支持）
pip install python-docx pillow

# 安装其他必要库
pip install streamlit pillow requests
```

### 步骤3：验证安装

```cmd
# 测试OpenAI库
python -c "from openai import OpenAI; print('OpenAI库安装成功')"

# 测试文档处理库
python -c "import docx; print('python-docx安装成功')"
python -c "from PIL import Image; print('Pillow安装成功')"
```

### 步骤4：运行批改系统

```cmd
# 运行测试脚本
python test_grading_function.py

# 或运行主程序
python streamlit_simple.py
```

## 🔧 故障排除

### 问题1：仍然显示Python 3.7

**解决方案**：
1. 完全关闭VSCode和所有终端
2. 重新打开
3. 或者使用完整路径运行

### 问题2：pip安装失败

**解决方案**：
```cmd
# 升级pip
python -m pip install --upgrade pip

# 使用国内镜像
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/ openai
```

### 问题3：权限问题

**解决方案**：
```cmd
# 以管理员身份运行命令提示符
# 或使用用户安装
pip install --user openai
```

## 📋 验证清单

完成切换后，请验证以下项目：

- [ ] `python --version` 显示 `Python 3.13.5`
- [ ] `pip --version` 显示对应Python 3.13的pip
- [ ] OpenAI库可以正常导入
- [ ] 文档处理库可以正常工作
- [ ] 批改系统可以正常运行

## 🎯 预期结果

切换成功后，您将能够：

1. ✅ 使用最新版本的OpenAI库
2. ✅ 使用多模态大模型处理文档
3. ✅ 运行完整的批改功能
4. ✅ 享受Python 3.13的新特性和性能提升

## 💡 小贴士

- **环境隔离**：考虑使用虚拟环境来管理不同项目的依赖
- **版本管理**：可以使用pyenv-win来更方便地管理多个Python版本
- **IDE设置**：记得在VSCode中也切换Python解释器到3.13.5

---

如果按照以上步骤操作后仍有问题，请提供具体的错误信息，我会进一步协助解决。