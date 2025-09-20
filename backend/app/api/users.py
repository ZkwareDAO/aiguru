"""User management API endpoints."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import (
    get_current_user,
    require_teacher,
    require_parent,
    require_roles,
    PermissionChecker
)
from app.models.user import User, UserRole
from app.schemas.user import (
    UserResponse,
    UserUpdate,
    UserSearchQuery,
    UserListResponse,
    ParentStudentLink,
    ParentStudentRelationResponse,
    UserStats,
    BulkUserOperation,
    UserRelationshipSummary,
    RelationshipValidation
)
from app.services.user_service import UserService


router = APIRouter(prefix="/users", tags=["用户管理"])


@router.get("/profile", response_model=UserResponse)
async def get_user_profile(
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """获取用户个人资料."""
    return UserResponse.model_validate(current_user)


@router.put("/profile", response_model=UserResponse)
async def update_user_profile(
    profile_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """更新用户个人资料."""
    user_service = UserService(db)
    
    updated_user = await user_service.update_user(
        user_id=current_user.id,
        user_data=profile_data
    )
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    return UserResponse.model_validate(updated_user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """根据ID获取用户信息."""
    # Check permission to access user data
    has_permission = await PermissionChecker.can_access_user_data(
        target_user_id=user_id,
        current_user=current_user,
        db=db
    )
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有访问此用户信息的权限"
        )
    
    user_service = UserService(db)
    user = await user_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    return UserResponse.model_validate(user)


@router.get("/search", response_model=UserListResponse)
async def search_users(
    query: str = Query(None, description="搜索关键词"),
    role: UserRole = Query(None, description="用户角色"),
    is_active: bool = Query(None, description="是否激活"),
    is_verified: bool = Query(None, description="是否验证"),
    school: str = Query(None, description="学校"),
    grade: str = Query(None, description="年级"),
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(require_roles(UserRole.TEACHER, UserRole.PARENT)),
    db: AsyncSession = Depends(get_db)
) -> UserListResponse:
    """搜索用户（支持高级筛选和分页）."""
    user_service = UserService(db)
    
    users, total = await user_service.search_users(
        query=query,
        role=role,
        is_active=is_active,
        is_verified=is_verified,
        school=school,
        grade=grade,
        page=page,
        per_page=per_page
    )
    
    total_pages = (total + per_page - 1) // per_page
    
    return UserListResponse(
        users=[UserResponse.model_validate(user) for user in users],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )


@router.get("/role/{role}", response_model=List[UserResponse])
async def get_users_by_role(
    role: UserRole,
    current_user: User = Depends(require_roles(UserRole.TEACHER, UserRole.PARENT)),
    db: AsyncSession = Depends(get_db)
) -> List[UserResponse]:
    """根据角色获取用户列表."""
    user_service = UserService(db)
    
    users = await user_service.get_users_by_role(role)
    
    return [UserResponse.model_validate(user) for user in users]


@router.post("/validate-parent-student-link", response_model=RelationshipValidation)
async def validate_parent_student_link(
    link_data: ParentStudentLink,
    current_user: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db)
) -> RelationshipValidation:
    """验证家长和学生关联是否有效."""
    user_service = UserService(db)
    
    is_valid, message = await user_service.validate_parent_student_link(
        parent_id=current_user.id,
        student_id=link_data.student_id
    )
    
    return RelationshipValidation(is_valid=is_valid, message=message)


@router.post("/link-parent-student", response_model=dict)
async def link_parent_student(
    link_data: ParentStudentLink,
    current_user: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """关联家长和学生."""
    user_service = UserService(db)
    
    # First validate the link
    is_valid, message = await user_service.validate_parent_student_link(
        parent_id=current_user.id,
        student_id=link_data.student_id
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    success = await user_service.link_parent_student(
        parent_id=current_user.id,
        student_id=link_data.student_id,
        relation_type=link_data.relation_type
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="关联失败，请稍后重试"
        )
    
    return {"message": "关联成功"}


@router.delete("/unlink-parent-student/{student_id}")
async def unlink_parent_student(
    student_id: UUID,
    current_user: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """取消家长和学生关联."""
    user_service = UserService(db)
    
    success = await user_service.unlink_parent_student(
        parent_id=current_user.id,
        student_id=student_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="关联关系不存在"
        )
    
    return {"message": "取消关联成功"}


@router.get("/parent/children", response_model=List[UserResponse])
async def get_parent_children(
    current_user: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db)
) -> List[UserResponse]:
    """获取家长的所有孩子."""
    user_service = UserService(db)
    
    children = await user_service.get_parent_children(current_user.id)
    
    return [UserResponse.model_validate(child) for child in children]


@router.get("/student/parents", response_model=List[UserResponse])
async def get_student_parents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[UserResponse]:
    """获取学生的所有家长."""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有学生可以查看自己的家长信息"
        )
    
    user_service = UserService(db)
    
    parents = await user_service.get_student_parents(current_user.id)
    
    return [UserResponse.model_validate(parent) for parent in parents]


@router.get("/teacher/students", response_model=List[UserResponse])
async def get_teacher_students(
    current_user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
) -> List[UserResponse]:
    """获取教师的所有学生."""
    user_service = UserService(db)
    
    students = await user_service.get_teacher_students(current_user.id)
    
    return [UserResponse.model_validate(student) for student in students]


@router.get("/student/teachers", response_model=List[UserResponse])
async def get_student_teachers(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[UserResponse]:
    """获取学生的所有教师."""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有学生可以查看自己的教师信息"
        )
    
    user_service = UserService(db)
    
    teachers = await user_service.get_student_teachers(current_user.id)
    
    return [UserResponse.model_validate(teacher) for teacher in teachers]


@router.post("/deactivate/{user_id}")
async def deactivate_user(
    user_id: UUID,
    current_user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """停用用户账户 (仅教师可操作)."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能停用自己的账户"
        )
    
    user_service = UserService(db)
    
    success = await user_service.deactivate_user(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    return {"message": "用户账户已停用"}


@router.post("/activate/{user_id}")
async def activate_user(
    user_id: UUID,
    current_user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """激活用户账户 (仅教师可操作)."""
    user_service = UserService(db)
    
    success = await user_service.activate_user(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    return {"message": "用户账户已激活"}


@router.post("/bulk-operation")
async def bulk_user_operation(
    operation_data: BulkUserOperation,
    current_user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """批量用户操作 (仅教师可操作)."""
    user_service = UserService(db)
    
    # Prevent self-operation
    if current_user.id in operation_data.user_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能对自己执行批量操作"
        )
    
    if operation_data.operation == "activate":
        updated_count = await user_service.bulk_update_user_status(
            user_ids=operation_data.user_ids,
            is_active=True
        )
        return {"message": f"已激活 {updated_count} 个用户账户"}
    
    elif operation_data.operation == "deactivate":
        updated_count = await user_service.bulk_update_user_status(
            user_ids=operation_data.user_ids,
            is_active=False
        )
        return {"message": f"已停用 {updated_count} 个用户账户"}
    
    elif operation_data.operation == "verify":
        updated_count = await user_service.bulk_update_user_status(
            user_ids=operation_data.user_ids,
            is_verified=True
        )
        return {"message": f"已验证 {updated_count} 个用户邮箱"}
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不支持的操作类型"
        )


@router.get("/", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(20, ge=1, le=100, description="每页数量"),
    role: UserRole = Query(None, description="用户角色筛选"),
    is_active: bool = Query(None, description="激活状态筛选"),
    current_user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
) -> UserListResponse:
    """获取用户列表 (仅教师可查看)."""
    user_service = UserService(db)
    
    users, total = await user_service.search_users(
        page=page,
        per_page=per_page,
        role=role,
        is_active=is_active
    )
    
    total_pages = (total + per_page - 1) // per_page
    
    return UserListResponse(
        users=[UserResponse.model_validate(user) for user in users],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )


@router.get("/stats/overview", response_model=UserStats)
async def get_user_stats(
    current_user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
) -> UserStats:
    """获取用户统计信息 (仅教师可查看)."""
    user_service = UserService(db)
    
    stats = await user_service.get_user_statistics()
    
    return UserStats(**stats)

@router.get("/relationships/summary", response_model=UserRelationshipSummary)
async def get_user_relationships_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UserRelationshipSummary:
    """获取用户关系摘要."""
    user_service = UserService(db)
    
    summary = await user_service.get_user_relationships_summary(current_user.id)
    
    return UserRelationshipSummary(**summary)


@router.get("/relationships/{user_id}", response_model=UserRelationshipSummary)
async def get_user_relationships_by_id(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UserRelationshipSummary:
    """获取指定用户的关系摘要."""
    # Check permission to access user relationships
    has_permission = await PermissionChecker.can_access_user_data(
        target_user_id=user_id,
        current_user=current_user,
        db=db
    )
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有访问此用户关系信息的权限"
        )
    
    user_service = UserService(db)
    
    summary = await user_service.get_user_relationships_summary(user_id)
    
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    return UserRelationshipSummary(**summary)


@router.get("/parent/relations", response_model=List[ParentStudentRelationResponse])
async def get_parent_relations(
    current_user: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db)
) -> List[ParentStudentRelationResponse]:
    """获取家长的所有关联关系."""
    user_service = UserService(db)
    
    relations = await user_service.get_parent_student_relations(current_user.id)
    
    return [ParentStudentRelationResponse.model_validate(relation) for relation in relations]


@router.get("/student/relations", response_model=List[ParentStudentRelationResponse])
async def get_student_relations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[ParentStudentRelationResponse]:
    """获取学生的所有关联关系."""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有学生可以查看自己的关联关系"
        )
    
    user_service = UserService(db)
    
    relations = await user_service.get_student_parent_relations(current_user.id)
    
    return [ParentStudentRelationResponse.model_validate(relation) for relation in relations]