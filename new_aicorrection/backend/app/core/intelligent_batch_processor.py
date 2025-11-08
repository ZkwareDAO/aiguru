"""
Intelligent Batch Processor - Migrated from ai_correction
High-performance concurrent processing for AI grading with three-step workflow
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import re
from pathlib import Path
import time

from .ai_grading_engine import (
    call_ai_api,
    call_ai_api_async,
    process_file_content,
    convert_latex_to_unicode,
    detect_loop_and_cleanup,
    enforce_strict_format,
    clean_grading_output,
    convert_to_html_markdown,
    pdf_pages_to_base64_images,
    img_to_base64
)

from .grading_prompts import (
    get_core_grading_prompt,
    get_batch_processing_prompt,
    get_summary_generation_prompt,
    get_question_analysis_prompt,
    ULTIMATE_SYSTEM_MESSAGE,
    QUESTION_ANALYSIS_PROMPT,
    MARKING_SCHEME_DEEP_LEARNING_PROMPT,
    MARKING_CONSISTENCY_CHECK_PROMPT
)

logger = logging.getLogger(__name__)

@dataclass
class Question:
    """Question information"""
    number: int
    content: str = ""
    max_score: float = 0
    student_answer: str = ""
    
@dataclass
class Student:
    """Student information"""
    id: str
    name: str
    questions: List[Question]
    total_score: float = 0
    grade: str = ""
    comments: str = ""

@dataclass
class BatchTask:
    """Batch task information"""
    batch_id: int
    student_id: str
    student_name: str
    question_numbers: List[int]
    start_index: int
    end_index: int
    file_content: str

class IntelligentBatchProcessor:
    """Intelligent batch processor with three-step workflow"""
    
    def __init__(self, batch_size: int = 10, max_concurrent: int = 3):
        self.batch_size = min(batch_size, 10)  # Ensure batch size ≤ 10
        self.max_concurrent = max_concurrent
        self.semaphore = None  # Create lazily to avoid event loop issues
    
    def _ensure_semaphore(self):
        """Ensure semaphore is created"""
        if self.semaphore is None:
            try:
                loop = asyncio.get_event_loop()
                self.semaphore = asyncio.Semaphore(self.max_concurrent)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                self.semaphore = asyncio.Semaphore(self.max_concurrent)
        
    async def step0_learn_marking_scheme(self, file_paths: List[str], file_info_list: List[Dict]) -> Dict[str, Any]:
        """Step 0: Deep learning of marking scheme"""
        logger.info("📚 Step 0: Deep learning marking scheme...")
        
        # Extract marking scheme files
        marking_files = []
        for i, info in enumerate(file_info_list):
            file_name = info.get('name', '').upper()
            if any(prefix in file_name for prefix in ['MARKING', '批改标准', '评分标准', '标准答案']):
                marking_files.append(file_paths[i])
                logger.info(f"📋 Found marking scheme file: {info.get('name', '')}")
        
        if not marking_files:
            logger.warning("⚠️ No marking scheme file found, will use general grading principles")
            return {
                "has_marking_scheme": False,
                "learning_result": "No marking scheme provided, will use general math grading principles",
                "learned_standards": {}
            }
        
        # Deep learning of marking scheme
        learning_prompt = f"""🛑 Important: You can directly view PDF image content!

📄 You have received PDF image content of the marking scheme, you can directly view and analyze the text, formulas and grading requirements.

{MARKING_SCHEME_DEEP_LEARNING_PROMPT}

Please carefully study the marking scheme, this will be the absolute basis for subsequent grading."""
        
        try:
            # Use multimedia API to learn marking scheme
            if marking_files and marking_files[0].endswith('.pdf'):
                logger.info("📄 Using multimedia API to learn marking scheme...")
                api_args = [learning_prompt]
                api_args.extend(marking_files)
                
                learning_result = call_ai_api(
                    learning_prompt,
                    system_message="You are a marking scheme learning expert who needs to deeply understand every detail of the grading standards.",
                    files=marking_files
                )
            else:
                # Handle text files
                marking_content = ""
                for file_path in marking_files:
                    content = process_file_content(file_path)
                    marking_content += f"\\n\\n=== {Path(file_path).name} ===\\n{content}"
                
                learning_result = call_ai_api(
                    learning_prompt + f"\\n\\nMarking scheme content:\\n{marking_content}",
                    system_message="You are a marking scheme learning expert who needs to deeply understand every detail of the grading standards."
                )
            
            logger.info("✅ Marking scheme learning completed")
            logger.info(f"📊 Learning result length: {len(learning_result)} characters")
            
            return {
                "has_marking_scheme": True,
                "learning_result": learning_result,
                "learned_standards": self.parse_learned_standards(learning_result),
                "marking_files": marking_files
            }
            
        except Exception as e:
            logger.error(f"❌ Marking scheme learning failed: {e}")
            return {
                "has_marking_scheme": False,
                "learning_result": f"Learning failed: {str(e)}",
                "learned_standards": {}
            }
    
    def parse_learned_standards(self, learning_result: str) -> Dict[str, Any]:
        """Parse learned marking standards"""
        standards = {}
        
        # Extract question analysis
        import re
        question_patterns = re.findall(r'\\*\\*Question(\\d+)Analysis\\*\\*：([^\\*]+)', learning_result)
        for question_num, analysis in question_patterns:
            standards[f"question_{question_num}"] = {
                "analysis": analysis.strip(),
                "extracted": True
            }
        
        # Extract grading principles
        principles_match = re.search(r'\\*\\*Grading Principles Summary\\*\\*：([^\\*]+)', learning_result)
        if principles_match:
            standards["principles"] = principles_match.group(1).strip()
        
        # Extract key memory points
        memory_match = re.search(r'\\*\\*Key Memory Points\\*\\*：([^=]+)', learning_result)
        if memory_match:
            standards["key_points"] = memory_match.group(1).strip()
        
        return standards
    
    async def step1_analyze_structure(self, file_paths: List[str], file_info_list: List[Dict]) -> Dict[str, Any]:
        """Step 1: Analyze file structure and identify questions/students"""
        logger.info("📊 Step 1: Analyzing file structure...")
        
        try:
            analysis_prompt = get_question_analysis_prompt()
            
            # Create analysis prompt with files
            full_prompt = f"""🛑 Important: You can directly view PDF image content!
            
{analysis_prompt}

Please analyze the provided files to identify the total number of questions, student information, and mark allocation."""
            
            # Call API with all files
            analysis_result = call_ai_api(
                full_prompt,
                system_message="You are a document analysis expert specializing in identifying academic assessment structures.",
                files=file_paths
            )
            
            # Parse analysis results
            parsed_result = self.parse_analysis_result(analysis_result, file_info_list)
            
            logger.info("✅ Structure analysis completed")
            logger.info(f"📊 Identified: {parsed_result.get('total_questions', 0)} questions, {parsed_result.get('student_count', 1)} students")
            
            return parsed_result
            
        except Exception as e:
            logger.error(f"❌ Structure analysis failed: {e}")
            return {
                "total_questions": 0,
                "students": [],
                "files_analyzed": len(file_paths),
                "analysis_error": str(e)
            }
    
    def parse_analysis_result(self, analysis_text: str, file_info_list: List[Dict]) -> Dict[str, Any]:
        """Parse structure analysis results"""
        result = {
            "total_questions": 0,
            "students": [],
            "question_details": [],
            "files_analyzed": len(file_info_list),
            "student_count": 1
        }
        
        # Extract total questions
        total_match = re.search(r'Total Questions?[：:]\\s*(\\d+)', analysis_text, re.IGNORECASE)
        if total_match:
            result["total_questions"] = int(total_match.group(1))
        
        # Extract question details
        question_matches = re.findall(r'Question\\s+(\\d+)[：:]\\s*(\\d+)\\s*marks?', analysis_text, re.IGNORECASE)
        for q_num, marks in question_matches:
            result["question_details"].append({
                "number": int(q_num),
                "marks": int(marks)
            })
        
        # Extract student information
        student_info_match = re.search(r'Student Information[：:]\\s*([^\\n]+)', analysis_text, re.IGNORECASE)
        if student_info_match:
            result["student_info"] = student_info_match.group(1).strip()
            
            # Try to extract multiple students
            if "," in result["student_info"] or "；" in result["student_info"]:
                # Multiple students detected
                separators = [",", "；", ";", "、"]
                for sep in separators:
                    if sep in result["student_info"]:
                        students = [s.strip() for s in result["student_info"].split(sep)]
                        result["students"] = students
                        result["student_count"] = len(students)
                        break
            else:
                result["students"] = [result["student_info"]]
                result["student_count"] = 1
        
        return result
    
    async def step2_batch_grade(self, file_paths: List[str], file_info_list: List[Dict], analysis_result: Dict[str, Any], learned_standards: Dict[str, Any]) -> Dict[str, Any]:
        """Step 2: Perform batch grading with concurrency control"""
        logger.info("🎯 Step 2: Performing batch grading...")
        
        self._ensure_semaphore()
        
        try:
            # Prepare grading prompt
            grading_prompt = get_core_grading_prompt(file_info_list, analysis_result)
            
            # Add learned standards to prompt if available
            if learned_standards.get("has_marking_scheme"):
                grading_prompt += f"""\\n\\n【Learned Marking Standards】
{learned_standards.get('learning_result', '')}

Based on the above learned marking standards, please perform strict grading."""
            
            # Perform grading
            grading_result = call_ai_api(
                f"""🛑 Important: You can directly view PDF image content!

{grading_prompt}

Please perform detailed grading based on the marking scheme you learned earlier.""",
                system_message=ULTIMATE_SYSTEM_MESSAGE,
                files=file_paths
            )
            
            # Clean and format results
            cleaned_result = self.clean_grading_result(grading_result)
            
            logger.info("✅ Batch grading completed")
            
            return {
                "grading_successful": True,
                "grading_result": cleaned_result,
                "raw_result": grading_result,
                "questions_processed": analysis_result.get('total_questions', 0)
            }
            
        except Exception as e:
            logger.error(f"❌ Batch grading failed: {e}")
            return {
                "grading_successful": False,
                "error": str(e),
                "questions_processed": 0
            }
    
    def clean_grading_result(self, raw_result: str) -> str:
        """Clean and standardize grading results"""
        # Apply all cleaning functions from the engine
        cleaned = clean_grading_output(raw_result)
        return cleaned
    
    async def step3_generate_summary(self, grading_results: Dict[str, Any], analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Step 3: Generate comprehensive summary"""
        logger.info("📝 Step 3: Generating summary...")
        
        try:
            summary_prompt = get_summary_generation_prompt()
            
            # Prepare summary context
            context = f"""Based on the following grading results, please generate a comprehensive summary:

Grading Results:
{grading_results.get('grading_result', '')}

Analysis Information:
- Total Questions: {analysis_result.get('total_questions', 0)}
- Students: {analysis_result.get('student_count', 1)}
- Files Processed: {analysis_result.get('files_analyzed', 0)}

{summary_prompt}"""
            
            summary_result = call_ai_api(
                context,
                system_message="You are an educational assessment specialist who creates comprehensive grading summaries."
            )
            
            logger.info("✅ Summary generation completed")
            
            return {
                "summary_successful": True,
                "summary": summary_result,
                "statistics": self.extract_statistics(grading_results, analysis_result)
            }
            
        except Exception as e:
            logger.error(f"❌ Summary generation failed: {e}")
            return {
                "summary_successful": False,
                "error": str(e),
                "summary": "Summary generation failed"
            }
    
    def extract_statistics(self, grading_results: Dict[str, Any], analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract statistical information from grading results"""
        grading_text = grading_results.get('grading_result', '')
        
        # Extract scores using regex
        score_pattern = r'\\*\\*Score\\*\\*[：:]\\s*(\\d+)\\s*marks?'
        scores = [int(match) for match in re.findall(score_pattern, grading_text)]
        
        # Extract full marks
        full_marks_pattern = r'\\*\\*Full Marks\\*\\*[：:]\\s*(\\d+)\\s*marks?'
        full_marks = [int(match) for match in re.findall(full_marks_pattern, grading_text)]
        
        total_score = sum(scores)
        total_full_marks = sum(full_marks)
        percentage = (total_score / total_full_marks * 100) if total_full_marks > 0 else 0
        
        return {
            "total_score": total_score,
            "total_full_marks": total_full_marks,
            "percentage": percentage,
            "questions_graded": len(scores),
            "average_score_per_question": total_score / len(scores) if scores else 0,
            "questions_analyzed": analysis_result.get('total_questions', 0)
        }
    
    async def process_complete_workflow(self, file_paths: List[str], file_info_list: List[Dict]) -> Dict[str, Any]:
        """Execute complete three-step grading workflow"""
        logger.info("🚀 Starting complete AI grading workflow...")
        
        start_time = time.time()
        workflow_results = {
            "workflow_successful": False,
            "steps_completed": 0,
            "total_steps": 4,
            "execution_time": 0,
            "errors": []
        }
        
        try:
            # Step 0: Learn marking scheme
            step0_result = await self.step0_learn_marking_scheme(file_paths, file_info_list)
            workflow_results["step0_marking_scheme_learning"] = step0_result
            workflow_results["steps_completed"] += 1
            
            # Step 1: Analyze structure
            step1_result = await self.step1_analyze_structure(file_paths, file_info_list)
            workflow_results["step1_structure_analysis"] = step1_result
            workflow_results["steps_completed"] += 1
            
            # Step 2: Batch grading
            step2_result = await self.step2_batch_grade(file_paths, file_info_list, step1_result, step0_result)
            workflow_results["step2_batch_grading"] = step2_result
            workflow_results["steps_completed"] += 1
            
            # Step 3: Generate summary
            step3_result = await self.step3_generate_summary(step2_result, step1_result)
            workflow_results["step3_summary_generation"] = step3_result
            workflow_results["steps_completed"] += 1
            
            # Check overall success
            workflow_results["workflow_successful"] = (
                step1_result.get('total_questions', 0) > 0 and
                step2_result.get('grading_successful', False) and
                step3_result.get('summary_successful', False)
            )
            
            workflow_results["execution_time"] = time.time() - start_time
            
            logger.info(f"✅ Complete workflow finished in {workflow_results['execution_time']:.2f} seconds")
            
            return workflow_results
            
        except Exception as e:
            workflow_results["errors"].append(str(e))
            workflow_results["execution_time"] = time.time() - start_time
            logger.error(f"❌ Workflow failed: {e}")
            return workflow_results

# Convenience functions for integration
async def process_grading_request(file_paths: List[str], file_info_list: List[Dict], batch_size: int = 10) -> Dict[str, Any]:
    """Process a complete grading request"""
    processor = IntelligentBatchProcessor(batch_size=batch_size)
    return await processor.process_complete_workflow(file_paths, file_info_list)

def process_grading_request_sync(file_paths: List[str], file_info_list: List[Dict], batch_size: int = 10) -> Dict[str, Any]:
    """Synchronous version of grading request processing"""
    try:
        # Check if we're already in an async event loop
        loop = asyncio.get_running_loop()
        # If we're in a loop, we need to use a different approach
        logger.warning("Already in async context, using direct processor call")
        
        # Create processor and run synchronously within async context
        processor = IntelligentBatchProcessor(batch_size=batch_size)
        import concurrent.futures
        
        # Use thread pool to run the async function
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(_run_async_in_thread, processor.process_complete_workflow, file_paths, file_info_list)
            return future.result()
            
    except RuntimeError:
        # No event loop running, safe to use asyncio.run
        return asyncio.run(process_grading_request(file_paths, file_info_list, batch_size))

def _run_async_in_thread(async_func, *args, **kwargs):
    """Helper function to run async function in new thread with new event loop"""
    import asyncio
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)
    try:
        return new_loop.run_until_complete(async_func(*args, **kwargs))
    finally:
        new_loop.close()

def process_grading_request_safe(file_paths: List[str], file_info_list: List[Dict], batch_size: int = 10) -> Dict[str, Any]:
    """Safe version that works in both sync and async contexts"""
    processor = IntelligentBatchProcessor(batch_size=batch_size)
    
    # Use simplified synchronous processing to avoid async conflicts
    try:
        from .ai_grading_engine import call_ai_api
        from .grading_prompts import get_core_grading_prompt, ULTIMATE_SYSTEM_MESSAGE
        
        start_time = time.time()
        
        # Step 1: Analyze structure (simplified)
        analysis_result = {
            "total_questions": len([f for f in file_paths if "QUESTION" in Path(f).name.upper()]),
            "students": ["Test Student"],
            "files_analyzed": len(file_paths)
        }
        
        # Step 2: Perform grading (simplified)
        grading_prompt = get_core_grading_prompt(None, analysis_result)
        grading_prompt += "\n\n请对提供的文件进行AI批改，严格按照批改标准评分。"
        
        grading_result = call_ai_api(
            grading_prompt,
            system_message=ULTIMATE_SYSTEM_MESSAGE,
            files=file_paths
        )
        
        # Step 3: Generate summary (simplified)
        summary_prompt = f"""基于以下批改结果生成总结：\n\n{grading_result}\n\n请提供：
1. 总体表现评价
2. 主要错误类型
3. 改进建议"""
        
        summary_result = call_ai_api(
            summary_prompt,
            system_message="你是教育评估专家，请生成简洁的批改总结。"
        )
        
        execution_time = time.time() - start_time
        
        return {
            "workflow_successful": True,
            "steps_completed": 3,
            "total_steps": 3,
            "execution_time": execution_time,
            "step1_structure_analysis": analysis_result,
            "step2_batch_grading": {
                "grading_successful": True,
                "grading_result": grading_result
            },
            "step3_summary_generation": {
                "summary_successful": True,
                "summary": summary_result
            }
        }
        
    except Exception as e:
        logger.error(f"Safe batch processing failed: {e}")
        return {
            "workflow_successful": False,
            "error": str(e),
            "steps_completed": 0,
            "total_steps": 3
        }