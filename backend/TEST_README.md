# AI Grading Test Files

This directory contains essential test files for the AI grading functionality.

## Test Files

### 🚀 Core Functionality Tests

#### [`simple_ai_grading_test.py`](./simple_ai_grading_test.py)
**Purpose**: Essential test for core AI grading functionality
- Tests direct AI grading calls
- Tests file-based grading workflow  
- Tests PDF report generation
- **Usage**: `python simple_ai_grading_test.py`
- **Status**: ✅ Ready for production testing

#### [`test_real_documents.py`](./test_real_documents.py)  
**Purpose**: Comprehensive test with real student documents
- Tests document detection and processing
- Tests complete AI grading workflow
- Tests real-world scenarios
- **Usage**: 
  1. Place your documents in `real_test_documents/` folder
  2. Run: `python test_real_documents.py`
- **Status**: ✅ Ready for real document testing

## Core AI Grading Components

The migrated AI grading system includes:

- **🧠 AI Grading Engine**: [`app/core/ai_grading_engine.py`](./app/core/ai_grading_engine.py)
- **📝 Grading Prompts**: [`app/core/grading_prompts.py`](./app/core/grading_prompts.py)  
- **⚡ Batch Processor**: [`app/core/intelligent_batch_processor.py`](./app/core/intelligent_batch_processor.py)
- **📄 PDF Generator**: [`app/core/pdf_generator.py`](./app/core/pdf_generator.py)
- **🎯 Templates**: [`app/core/grading_templates.json`](./app/core/grading_templates.json)

## Quick Start

1. **Configure API key** in [`.env`](./.env) file
2. **Run basic test**: `python simple_ai_grading_test.py`
3. **Test with your documents**: Use `test_real_documents.py`

## Requirements

- OpenRouter/OpenAI/Anthropic/Google API key
- Python packages: `pip install -r requirements.txt`
- Optional: `pip install reportlab` for PDF generation

---

All unnecessary test files have been removed. Only essential testing functionality remains.