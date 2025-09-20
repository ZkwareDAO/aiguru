#!/usr/bin/env python3
"""Simple test script to verify class management implementation."""

import asyncio
import sys
from uuid import uuid4

# Add the backend directory to the path
sys.path.insert(0, '.')

from app.core.database import db_manager
from app.models.user import User, UserRole
from app.models.class_model import Class
from app.services.class_service import ClassService
from app.schemas.class_schema import ClassCreate


async def test_class_management():
    """Test basic class management functionality."""
    print("Testing Class Management System...")
    
    try:
        # Get database session
        async for db in db_manager.get_session():
            # Create a test teacher
            teacher = User(
                email="test_teacher@example.com",
                password_hash="hashed_password",
                name="Test Teacher",
                role=UserRole.TEACHER,
                is_active=True
            )
            db.add(teacher)
            await db.commit()
            await db.refresh(teacher)
            print(f"✓ Created teacher: {teacher.name} ({teacher.id})")
            
            # Create a test student
            student = User(
                email="test_student@example.com",
                password_hash="hashed_password",
                name="Test Student",
                role=UserRole.STUDENT,
                is_active=True
            )
            db.add(student)
            await db.commit()
            await db.refresh(student)
            print(f"✓ Created student: {student.name} ({student.id})")
            
            # Test class service
            class_service = ClassService(db)
            
            # Create a class
            class_data = ClassCreate(
                name="Test Math Class",
                description="A test mathematics class",
                school="Test School",
                grade="Grade 1",
                subject="Mathematics"
            )
            
            new_class = await class_service.create_class(teacher.id, class_data)
            print(f"✓ Created class: {new_class.name} (Code: {new_class.class_code})")
            
            # Add student to class
            membership = await class_service.add_student_to_class(
                new_class.id, student.id, teacher.id
            )
            print(f"✓ Added student to class: {membership.student_id}")
            
            # Get class stats
            stats = await class_service.get_class_stats(new_class.id, teacher.id)
            print(f"✓ Class stats - Students: {stats.total_students}, Active: {stats.active_students}")
            
            # Get class analytics
            analytics = await class_service.get_detailed_class_analytics(new_class.id, teacher.id)
            print(f"✓ Analytics generated with {len(analytics)} sections")
            
            # Test student joining by code
            await class_service.leave_class(new_class.id, student.id)
            print("✓ Student left class")
            
            membership2 = await class_service.join_class_by_code(student.id, new_class.class_code)
            print(f"✓ Student rejoined class using code: {membership2.is_active}")
            
            # Export class data
            export_data = await class_service.export_class_data(new_class.id, teacher.id)
            print(f"✓ Exported class data with {len(export_data['students'])} students")
            
            print("\n🎉 All class management tests passed!")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


async def main():
    """Main test function."""
    print("Class Management System Test")
    print("=" * 40)
    
    success = await test_class_management()
    
    if success:
        print("\n✅ Class management system is working correctly!")
        return 0
    else:
        print("\n❌ Class management system has issues!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)