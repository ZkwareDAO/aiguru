#!/usr/bin/env python3
"""
Real Document AI Grading Test
Test the backend AI grading functionality with actual student papers and marking schemes
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

class RealDocumentTester:
    """Test AI grading with real student documents"""
    
    def __init__(self):
        self.test_dir = Path("real_test_documents")
        self.results_dir = Path("real_test_results")
        self.setup_directories()
    
    def setup_directories(self):
        """Create necessary directories"""
        self.test_dir.mkdir(exist_ok=True)
        self.results_dir.mkdir(exist_ok=True)
        print(f"📁 Test directories ready:")
        print(f"   📋 Documents: {self.test_dir.absolute()}")
        print(f"   📊 Results: {self.results_dir.absolute()}")
    
    def detect_documents(self) -> Dict[str, List[str]]:
        """Detect and categorize documents in the test directory"""
        print("\n🔍 Detecting documents in test directory...")
        
        files = {
            "questions": [],
            "answers": [], 
            "marking_schemes": [],
            "other": []
        }
        
        for file_path in self.test_dir.iterdir():
            if file_path.is_file():
                name_upper = file_path.name.upper()
                
                # Detect file types based on filename patterns
                if any(keyword in name_upper for keyword in ['QUESTION', '题目', '试题', 'EXAM', 'TEST']):
                    files["questions"].append(str(file_path))
                elif any(keyword in name_upper for keyword in ['ANSWER', '答案', '答题', 'STUDENT', '学生']):
                    files["answers"].append(str(file_path))
                elif any(keyword in name_upper for keyword in ['MARKING', 'SCHEME', '批改', '评分', '标准', 'RUBRIC']):
                    files["marking_schemes"].append(str(file_path))
                else:
                    files["other"].append(str(file_path))
        
        # Print detection results
        print("📋 Document detection results:")
        for category, file_list in files.items():
            if file_list:
                print(f"   📄 {category.title()}: {len(file_list)} files")
                for file_path in file_list:
                    print(f"      - {Path(file_path).name}")
            else:
                print(f"   ❌ {category.title()}: No files found")
        
        return files
    
    def check_prerequisites(self) -> bool:
        """Check if we have the minimum required files"""
        files = self.detect_documents()
        
        has_questions = len(files["questions"]) > 0
        has_answers = len(files["answers"]) > 0
        has_marking = len(files["marking_schemes"]) > 0
        
        print(f"\n✅ Prerequisites check:")
        print(f"   📋 Questions: {'✅' if has_questions else '❌'}")
        print(f"   📝 Answers: {'✅' if has_answers else '❌'}")
        print(f"   📊 Marking schemes: {'✅' if has_marking else '❌'}")
        
        if not (has_questions or has_answers):
            print("⚠️  Warning: No question or answer files detected")
            print("💡 Please place your files in the test directory with appropriate names:")
            print("   - Questions: Include 'question', '题目', or 'exam' in filename")
            print("   - Answers: Include 'answer', '答案', or 'student' in filename") 
            print("   - Marking: Include 'marking', '批改', or 'scheme' in filename")
            return False
        
        return True
    
    def provide_file_placement_guide(self):
        """Provide guidance on how to place files"""
        print("\n📖 File Placement Guide:")
        print("=" * 50)
        print(f"Please place your documents in: {self.test_dir.absolute()}")
        print("\n📋 Recommended file naming:")
        print("   📄 Question files:")
        print("      - QUESTION_math_exam.pdf")
        print("      - 数学题目.jpg") 
        print("      - exam_questions.txt")
        print("\n   📝 Answer files:")
        print("      - ANSWER_student_zhang.pdf")
        print("      - 学生答案_李明.jpg")
        print("      - student_work.txt")
        print("\n   📊 Marking scheme files:")
        print("      - MARKING_scheme.pdf")
        print("      - 批改标准.txt")
        print("      - rubric.jpg")
        print("\n💡 Supported formats: PDF, JPG, PNG, TXT, DOCX")
        print("=" * 50)
    
    def test_document_processing(self, files: Dict[str, List[str]]) -> bool:
        """Test basic document processing"""
        print("\n📄 Testing document processing...")
        
        try:
            from app.core.ai_grading_engine import process_file_content
            
            all_files = []
            for category, file_list in files.items():
                all_files.extend(file_list)
            
            if not all_files:
                print("❌ No files to process")
                return False
            
            processed_count = 0
            for file_path in all_files:
                try:
                    content = process_file_content(file_path)
                    file_size = len(content)
                    print(f"   ✅ {Path(file_path).name}: {file_size} characters")
                    processed_count += 1
                except Exception as e:
                    print(f"   ❌ {Path(file_path).name}: {str(e)}")
            
            success_rate = processed_count / len(all_files)
            print(f"📊 Processing success rate: {processed_count}/{len(all_files)} ({success_rate*100:.1f}%)")
            
            return success_rate > 0.5  # At least 50% success
            
        except Exception as e:
            print(f"❌ Document processing test failed: {e}")
            return False
    
    def test_ai_grading_workflow(self, files: Dict[str, List[str]]) -> Dict[str, Any]:
        """Test complete AI grading workflow with real documents"""
        print("\n🤖 Testing AI grading workflow...")
        
        try:
            from app.core.intelligent_batch_processor import process_grading_request_safe
            
            # Prepare all files for processing
            all_files = []
            file_info_list = []
            
            for category, file_list in files.items():
                for file_path in file_list:
                    all_files.append(file_path)
                    file_info_list.append({
                        'name': Path(file_path).name,
                        'path': file_path,
                        'size': Path(file_path).stat().st_size,
                        'category': category
                    })
            
            if not all_files:
                print("❌ No files to process")
                return {"success": False, "error": "No files"}
            
            print(f"🔄 Processing {len(all_files)} files with AI grading system...")
            start_time = datetime.now()
            
            # Run AI grading workflow
            result = process_grading_request_safe(all_files, file_info_list)
            
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            print(f"⏱️  Processing time: {processing_time:.1f} seconds")
            
            if result.get('workflow_successful', False):
                print("✅ AI grading workflow completed successfully!")
                
                # Extract key results
                grading_results = result.get('step2_batch_grading', {})
                summary_results = result.get('step3_summary_generation', {})
                
                return {
                    "success": True,
                    "processing_time": processing_time,
                    "files_processed": len(all_files),
                    "grading_result": grading_results.get('grading_result', ''),
                    "summary": summary_results.get('summary', ''),
                    "full_result": result
                }
            else:
                print("❌ AI grading workflow failed")
                return {
                    "success": False,
                    "error": result.get('error', 'Unknown error'),
                    "full_result": result
                }
                
        except Exception as e:
            print(f"❌ AI grading workflow test failed: {e}")
            return {"success": False, "error": str(e)}
    
    def test_pdf_report_generation(self, grading_result: str) -> bool:
        """Test PDF report generation with real grading results"""
        print("\n📄 Testing PDF report generation...")
        
        try:
            from app.core.pdf_generator import create_grading_pdf
            
            if not grading_result:
                print("⚠️  No grading result to generate PDF")
                return False
            
            # Extract student info from grading result (if possible)
            student_info = {
                "name": "Real Test Student",
                "student_id": "TEST001",
                "class": "Test Class",
                "test_date": datetime.now().strftime("%Y-%m-%d")
            }
            
            # Basic statistics (extracted from result if possible)
            statistics = {
                "total_score": "N/A",
                "total_full_marks": "N/A", 
                "percentage": "N/A",
                "questions_graded": "N/A"
            }
            
            # Generate PDF
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pdf_filename = f"real_grading_report_{timestamp}.pdf"
            pdf_path = self.results_dir / pdf_filename
            
            print(f"🔄 Generating PDF report: {pdf_filename}")
            
            success = create_grading_pdf(
                content=grading_result,
                output_path=str(pdf_path),
                title="Real Document AI Grading Report",
                student_info=student_info,
                statistics=statistics
            )
            
            if success:
                file_size = pdf_path.stat().st_size
                print(f"✅ PDF report generated successfully!")
                print(f"   📁 Location: {pdf_path}")
                print(f"   📊 Size: {file_size:,} bytes")
                return True
            else:
                print("❌ PDF generation failed")
                return False
                
        except Exception as e:
            print(f"❌ PDF report generation failed: {e}")
            return False
    
    def save_detailed_results(self, test_results: Dict[str, Any]):
        """Save detailed test results to JSON file"""
        print("\n💾 Saving detailed results...")
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_file = self.results_dir / f"test_results_{timestamp}.json"
            
            # Prepare results for JSON serialization
            json_results = {
                "test_info": {
                    "timestamp": timestamp,
                    "test_type": "real_document_grading",
                    "success": test_results.get("success", False)
                },
                "processing": {
                    "files_processed": test_results.get("files_processed", 0),
                    "processing_time_seconds": test_results.get("processing_time", 0)
                },
                "grading_result": test_results.get("grading_result", ""),
                "summary": test_results.get("summary", ""),
                "error": test_results.get("error", None)
            }
            
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(json_results, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Results saved to: {results_file}")
            
        except Exception as e:
            print(f"⚠️  Failed to save results: {e}")
    
    def run_comprehensive_test(self) -> bool:
        """Run comprehensive test with real documents"""
        print("🎯 Real Document AI Grading Comprehensive Test")
        print("=" * 60)
        
        # Step 1: Check prerequisites
        if not self.check_prerequisites():
            self.provide_file_placement_guide()
            return False
        
        # Step 2: Detect documents
        files = self.detect_documents()
        
        # Step 3: Test document processing
        processing_success = self.test_document_processing(files)
        if not processing_success:
            print("❌ Document processing failed, cannot continue")
            return False
        
        # Step 4: Test AI grading workflow
        grading_results = self.test_ai_grading_workflow(files)
        
        if not grading_results.get("success", False):
            print("❌ AI grading workflow failed")
            if grading_results.get("error"):
                print(f"Error details: {grading_results['error']}")
            return False
        
        # Step 5: Display grading results
        print("\n📝 AI Grading Results:")
        print("=" * 40)
        grading_text = grading_results.get("grading_result", "")
        if grading_text:
            # Show first 500 characters as preview
            preview = grading_text[:500] + "..." if len(grading_text) > 500 else grading_text
            print(preview)
        
        summary_text = grading_results.get("summary", "")
        if summary_text:
            print("\n📊 Summary:")
            print("-" * 20)
            summary_preview = summary_text[:300] + "..." if len(summary_text) > 300 else summary_text
            print(summary_preview)
        
        # Step 6: Test PDF generation
        pdf_success = self.test_pdf_report_generation(grading_text)
        
        # Step 7: Save results
        self.save_detailed_results(grading_results)
        
        # Final summary
        print("\n" + "=" * 60)
        print("📊 Test Summary")
        print("=" * 60)
        
        tests = [
            ("Document Processing", processing_success),
            ("AI Grading Workflow", grading_results.get("success", False)),
            ("PDF Report Generation", pdf_success)
        ]
        
        passed = 0
        for test_name, result in tests:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name}")
            if result:
                passed += 1
        
        print(f"\n🎯 Overall Result: {passed}/{len(tests)} tests passed")
        
        if passed == len(tests):
            print("🎉 Excellent! Your AI grading system handles real documents perfectly!")
            print("💡 Key achievements:")
            print(f"   - Processed {grading_results.get('files_processed', 0)} real document files")
            print(f"   - Completed grading in {grading_results.get('processing_time', 0):.1f} seconds") 
            print(f"   - Generated professional PDF report")
            print(f"   - Saved detailed results for analysis")
        elif passed >= 2:
            print("⚠️  Good progress! Most core functionality works with real documents.")
        else:
            print("❌ Issues detected. Please check your document format and API configuration.")
        
        return passed == len(tests)

def main():
    """Main function"""
    print("🎯 Real Document AI Grading Test Suite")
    print("This will test your AI grading system with actual student papers")
    print()
    
    # Load environment
    try:
        import dotenv
        dotenv.load_dotenv()
    except:
        pass
    
    # Create tester and run comprehensive test
    tester = RealDocumentTester()
    success = tester.run_comprehensive_test()
    
    if success:
        print("\n🚀 Your AI grading system is ready for production use!")
    else:
        print("\n💡 Tips for success:")
        print("   1. Ensure you have proper API keys configured")
        print("   2. Place your documents in the test directory")
        print("   3. Use clear, descriptive filenames")
        print("   4. Supported formats: PDF, images, text files")
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        sys.exit(1)