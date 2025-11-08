"""Test script for LangGraph grading workflow."""

import asyncio
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_workflow():
    """Test the LangGraph grading workflow."""
    try:
        # Import after setting up logging
        from app.core.database import get_db
        from app.services.langgraph_grading_workflow import get_langgraph_workflow
        
        logger.info("Starting LangGraph workflow test...")
        
        # Get database session
        async for db in get_db():
            # Get workflow instance
            workflow = get_langgraph_workflow(db)
            
            # Test data - you'll need to replace these with actual file paths
            test_files = {
                "question_files": [],  # Add actual question file paths
                "answer_files": ["test_answer.jpg"],  # Add actual answer file paths
                "marking_scheme_files": [],  # Optional
            }
            
            logger.info(f"Testing with files: {test_files}")
            
            # Execute workflow
            result = await workflow.execute(
                question_files=test_files["question_files"],
                answer_files=test_files["answer_files"],
                marking_scheme_files=test_files["marking_scheme_files"],
                task_type="auto",
                strictness_level="中等",
                language="zh",
                max_score=100
            )
            
            logger.info("Workflow completed successfully!")
            logger.info(f"Result: {result}")
            
            # Print key results
            if result:
                print("\n" + "="*50)
                print("批改结果:")
                print("="*50)
                print(f"总分: {result.get('total_score', 0)}/{result.get('max_score', 100)}")
                print(f"百分比: {result.get('percentage', 0):.2f}%")
                print(f"等级: {result.get('grade_level', 'N/A')}")
                print(f"\n详细反馈:\n{result.get('detailed_feedback', 'N/A')}")
                print("="*50)
            
            break
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        raise


async def test_streaming_workflow():
    """Test the streaming LangGraph workflow."""
    try:
        from app.core.database import get_db
        from app.services.langgraph_grading_workflow import get_langgraph_workflow
        
        logger.info("Starting streaming LangGraph workflow test...")
        
        async for db in get_db():
            workflow = get_langgraph_workflow(db)
            
            test_files = {
                "question_files": [],
                "answer_files": ["test_answer.jpg"],
                "marking_scheme_files": [],
            }
            
            logger.info("Testing streaming mode...")
            
            async for event in workflow.execute_stream(
                question_files=test_files["question_files"],
                answer_files=test_files["answer_files"],
                marking_scheme_files=test_files["marking_scheme_files"],
                task_type="auto",
                strictness_level="中等",
                language="zh",
                max_score=100
            ):
                event_type = event.get("type", "unknown")
                
                if event_type == "progress":
                    logger.info(f"Progress: {event.get('progress', 0)}% - {event.get('phase', '')}")
                elif event_type == "complete":
                    logger.info("Workflow completed!")
                    result = event.get("result", {})
                    print(f"\n总分: {result.get('total_score', 0)}/{result.get('max_score', 100)}")
                elif event_type == "error":
                    logger.error(f"Error: {event.get('error', 'Unknown error')}")
            
            break
        
    except Exception as e:
        logger.error(f"Streaming test failed: {str(e)}", exc_info=True)
        raise


async def test_nodes_individually():
    """Test individual nodes."""
    try:
        from app.services.langgraph_state import create_initial_state
        from app.services.langgraph_nodes import (
            create_upload_validator_node,
            create_document_ingestor_node,
            create_rubric_interpreter_node,
            create_scoring_agent_node
        )
        from app.core.database import get_db
        
        logger.info("Testing individual nodes...")
        
        async for db in get_db():
            # Create initial state
            state = create_initial_state(
                task_id="test-task-123",
                question_files=[],
                answer_files=["test_answer.jpg"],
                marking_scheme_files=[],
                task_type="auto",
                strictness_level="中等",
                language="zh",
                max_score=100
            )
            
            # Test UploadValidator
            logger.info("Testing UploadValidator...")
            upload_validator = create_upload_validator_node(db)
            state = await upload_validator(state)
            logger.info(f"UploadValidator status: {state.get('status', 'unknown')}")
            
            # Test DocumentIngestor
            logger.info("Testing DocumentIngestor...")
            document_ingestor = create_document_ingestor_node()
            state = await document_ingestor(state)
            logger.info(f"DocumentIngestor OCR blocks: {len(state.get('ocr_output', {}).get('text_blocks', []))}")
            
            # Test RubricInterpreter
            logger.info("Testing RubricInterpreter...")
            rubric_interpreter = create_rubric_interpreter_node()
            state = await rubric_interpreter(state)
            logger.info(f"RubricInterpreter criteria: {len(state.get('grading_criteria', []))}")
            
            # Test ScoringAgent
            logger.info("Testing ScoringAgent...")
            scoring_agent = create_scoring_agent_node()
            state = await scoring_agent(state)
            logger.info(f"ScoringAgent score: {state.get('total_score', 0)}/{state.get('max_score', 100)}")
            
            logger.info("All nodes tested successfully!")
            
            break
        
    except Exception as e:
        logger.error(f"Node test failed: {str(e)}", exc_info=True)
        raise


def main():
    """Main test function."""
    import sys
    
    if len(sys.argv) > 1:
        test_mode = sys.argv[1]
    else:
        test_mode = "workflow"
    
    if test_mode == "workflow":
        asyncio.run(test_workflow())
    elif test_mode == "streaming":
        asyncio.run(test_streaming_workflow())
    elif test_mode == "nodes":
        asyncio.run(test_nodes_individually())
    else:
        print("Usage: python test_langgraph_workflow.py [workflow|streaming|nodes]")
        sys.exit(1)


if __name__ == "__main__":
    main()

