# 🎓 智能批量批改系统使用指南

## 🚀 系统特性

### 核心功能
1. **🎯 智能识别**：AI自动识别题目编号、内容和学生信息
2. **📦 分批处理**：每批最多10道题，避免超时
3. **⚡ 并发批改**：多批次同时处理，提升效率3-5倍
4. **📊 学生总结**：为每个学生生成个性化总结报告
5. **🔄 自动重试**：失败批次自动重试，确保完整性

### 技术优势
- 基于 [asyncio 并发技术](https://python.useinstructor.com/blog/2023/11/13/learn-async/)
- 智能任务调度，最大化资源利用
- 支持多种文件格式（图片、PDF、Word、文本）
- 自动处理大批量作业，无需人工分割

## 📋 使用流程

### 1. 准备文件
- **题目文件**（可选）：包含题目内容
- **学生答案**（必需）：学生的作答文件
- **批改标准**（可选）：评分标准文件

文件命名建议：
- 题目：`questions.pdf` 或 `题目.docx`
- 答案：`student_张三_answers.pdf` 或 `答案_李四.txt`
- 标准：`marking_scheme.pdf` 或 `评分标准.docx`

### 2. 上传文件
1. 进入"📝 批改"页面
2. 分别上传对应类型的文件
3. 系统会自动添加类别前缀（QUESTION_、ANSWER_、MARKING_）

### 3. 开始批改
1. 确保"启用智能批改系统"已勾选
2. 点击"🚀 开始AI批改"
3. 系统将显示以下进度：
   - 🔍 AI正在智能分析文件内容...
   - 📦 创建批次任务...
   - ⚡ 并发批改进行中...
   - 📊 生成学生总结...

### 4. 查看结果
批改完成后，系统自动跳转到结果页面，显示：
- 每个批次的详细批改结果
- 每个学生的总结报告
- 总体统计信息

## 🎯 智能识别示例

### 输入文件内容
```
学生：张三
1. 什么是机器学习？
答：机器学习是人工智能的一个分支...

2. 解释深度学习的概念
答：深度学习是机器学习的子集...

学生：李四
1. 什么是机器学习？
答：机器学习让计算机从数据中学习...
```

### AI识别结果
```json
{
  "students": [
    {
      "id": "张三",
      "name": "张三",
      "questions": [
        {
          "number": 1,
          "content": "什么是机器学习？",
          "max_score": 10,
          "student_answer": "机器学习是人工智能的一个分支..."
        },
        {
          "number": 2,
          "content": "解释深度学习的概念",
          "max_score": 10,
          "student_answer": "深度学习是机器学习的子集..."
        }
      ]
    },
    {
      "id": "李四",
      "name": "李四",
      "questions": [...]
    }
  ],
  "total_questions": 2,
  "has_marking_scheme": false
}
```

## 📊 批改结果格式

### 1. 批次批改结果
```
## 学生: 张三 - 第1-10题

### 题目1：什么是机器学习？
**得分：8/10**
**评语：**
- 定义准确，理解到位
- 建议补充具体应用案例

### 题目2：解释深度学习的概念
**得分：9/10**
**评语：**
- 概念解释清晰
- 层次结构说明准确
...
```

### 2. 学生总结报告
```
## 🎯 学生 张三 总结

### 总体表现评价
张三同学在本次测试中表现优秀，对基础概念理解扎实...

### 各题得分汇总
- 题目1：8/10
- 题目2：9/10
- ...
- **总分：85/100**
- **等级：B+**

### 主要优点
1. 概念理解准确
2. 表达清晰有条理
3. 能够举例说明

### 需要改进的地方
1. 部分专业术语使用不够准确
2. 缺少实际应用案例

### 学习建议
1. 加强专业词汇的学习
2. 多阅读相关案例研究
3. 练习将理论与实践结合
```

## ⚙️ 高级设置

### 批改参数
- **每批题目数量**：默认10道（可调整5-15）
- **最大并发数**：默认3个批次同时处理
- **跳过缺失文件**：自动跳过找不到答案的题目
- **生成总结**：批改完成后生成整体分析

### 性能优化
- 文件较多时，系统自动优化处理顺序
- 大文件自动分页处理
- 智能缓存，避免重复分析

## 🔧 常见问题

### Q1: 系统如何识别多个学生？
A: AI会分析文件内容中的学生标识（如姓名、学号），或根据文件名区分。建议在文件名或内容中明确标注学生信息。

### Q2: 如果题目很多怎么办？
A: 系统会自动分批处理，每批10道题。例如50道题会分成5批并发处理，大大提升效率。

### Q3: 批改失败怎么办？
A: 系统有自动重试机制。如果某批次失败，会自动重试。最终结果会标注失败的批次。

### Q4: 支持哪些文件格式？
A: 支持txt、pdf、jpg、png、doc、docx等常见格式。图片会自动OCR识别。

### Q5: 如何提高识别准确率？
A: 
- 文件命名规范（包含学生姓名）
- 内容格式清晰（题号明确）
- 答案完整（避免截断）

## 📈 性能对比

| 处理方式 | 50道题耗时 | 并发数 | 优势 |
|---------|-----------|--------|------|
| 传统串行 | ~10分钟 | 1 | 稳定 |
| 智能批量 | ~2-3分钟 | 3-5 | 快速、智能分组 |

## 🎉 使用建议

1. **批量作业**：特别适合处理班级作业、考试批改
2. **多学生场景**：自动区分不同学生，分别评分
3. **长篇答案**：智能分批避免超时
4. **混合格式**：同时处理图片、PDF等多种格式

## 💡 提示

- 首次使用建议先用少量文件测试
- 批改标准越详细，评分越准确
- 保持文件命名规范有助于识别
- 定期查看批改日志了解处理细节

---

**技术支持**：如遇到问题，请查看 `logs/api_debug.log` 获取详细信息。 