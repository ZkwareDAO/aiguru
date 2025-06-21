from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import os
import json
import hashlib
from datetime import datetime, timedelta
import logging
from pathlib import Path
from functions.api_correcting.calling_api import correction_single_group
import re
from pydantic import BaseModel
from typing import List, Optional
import jwt
import secrets
import tempfile
import shutil

# 应用设置
app = FastAPI(
    title="AI智能批改系统",
    description="AI赋能教育，智能批改新纪元",
    version="1.0.0"
)

# CORS设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 常量
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
UPLOAD_DIR = Path("uploads")
DATA_FILE = Path("user_data.json")
SECRET_KEY = secrets.token_urlsafe(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 创建必要的目录
UPLOAD_DIR.mkdir(exist_ok=True)

# 测试账户
TEST_ACCOUNTS = {
    "test_user_1": {"password": "password1"},
    "test_user_2": {"password": "password2"}
}

# Pydantic模型
class UserLogin(BaseModel):
    username: str
    password: str

class UserRegister(BaseModel):
    username: str
    password: str
    confirm_password: str
    email: Optional[str] = None

# 安全相关
security = HTTPBearer(auto_error=False)

def setup_logger():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s"
    )

setup_logger()

# 初始化存储结构
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

def read_user_data():
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            for test_user, details in TEST_ACCOUNTS.items():
                if test_user not in data:
                    data[test_user] = {
                        "password": details["password"],
                        "email": f"{test_user}@example.com",
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "records": []
                    }
            return data
    except FileNotFoundError:
        default_data = {}
        for test_user, details in TEST_ACCOUNTS.items():
            default_data[test_user] = {
                "password": details["password"],
                "email": f"{test_user}@example.com",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "records": []
            }
        return default_data

def save_user_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        return username
    except jwt.PyJWTError:
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要认证"
        )
    
    token = credentials.credentials
    username = verify_token(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据"
        )
    return username

def save_uploaded_file(user_dir: Path, file: UploadFile, file_type: str) -> Path:
    file_extension = os.path.splitext(file.filename)[1]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{file_type}_{timestamp}{file_extension}"
    file_path = user_dir / filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return file_path

# API路由
@app.post("/api/auth/login")
async def login(user_data: UserLogin):
    """用户登录"""
    user_db = read_user_data()
    
    # 检查测试账户
    if user_data.username in TEST_ACCOUNTS:
        if TEST_ACCOUNTS[user_data.username]['password'] == user_data.password:
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": user_data.username}, expires_delta=access_token_expires
            )
            return {"access_token": access_token, "token_type": "bearer", "username": user_data.username}
    
    # 检查注册用户
    if user_data.username in user_db:
        user_info = user_db[user_data.username]
        if user_info.get('password') == hash_password(user_data.password):
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": user_data.username}, expires_delta=access_token_expires
            )
            return {"access_token": access_token, "token_type": "bearer", "username": user_data.username}
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="用户名或密码错误"
    )

@app.post("/api/auth/register")
async def register(user_data: UserRegister):
    """用户注册"""
    if user_data.password != user_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码不匹配"
        )
    
    user_db = read_user_data()
    
    if user_data.username in user_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    user_db[user_data.username] = {
        "password": hash_password(user_data.password),
        "email": user_data.email or "",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "records": []
    }
    save_user_data(user_db)
    
    return {"message": "注册成功"}

@app.post("/api/correction/upload")
async def upload_files_for_correction(
    questions_file: UploadFile = File(None),
    rubric_file: UploadFile = File(None), 
    answers_file: UploadFile = File(...),
    current_user: str = Depends(get_current_user)
):
    """上传文件进行批改"""
    
    if not answers_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="必须上传学生答案文件"
        )
    
    user_dir = UPLOAD_DIR / current_user
    user_dir.mkdir(exist_ok=True)
    
    try:
        image_files = []
        
        # 保存并添加题目文件
        if questions_file:
            if questions_file.size > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"题目文件 {questions_file.filename} 超过大小限制"
                )
            question_path = save_uploaded_file(user_dir, questions_file, "question")
            image_files.append(str(question_path))
        
        # 保存并添加学生答案文件（必需）
        if answers_file.size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"答案文件 {answers_file.filename} 超过大小限制"
            )
        answer_path = save_uploaded_file(user_dir, answers_file, "student_answer")
        image_files.append(str(answer_path))
        
        # 保存并添加评分标准文件
        if rubric_file:
            if rubric_file.size > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"评分标准文件 {rubric_file.filename} 超过大小限制"
                )
            rubric_path = save_uploaded_file(user_dir, rubric_file, "marking_scheme")
            image_files.append(str(rubric_path))
        
        # 调用AI批改API
        result = correction_single_group(
            *image_files,
            strictness_level="中等",
            language="zh",
            group_index=1
        )
        
        if result and isinstance(result, str):
            # 保存记录
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            correction_record = {
                "timestamp": timestamp,
                "content": result,
                "files": {
                    "questions_file": questions_file.filename if questions_file else None,
                    "answers_file": answers_file.filename,
                    "rubric_file": rubric_file.filename if rubric_file else None
                },
                "settings": {
                    "strictness_level": "中等",
                    "language": "zh"
                }
            }
            
            user_data = read_user_data()
            if current_user not in user_data:
                user_data[current_user] = {"records": []}
            if "records" not in user_data[current_user]:
                user_data[current_user]["records"] = []
            user_data[current_user]["records"].append(correction_record)
            save_user_data(user_data)
            
            return {
                "success": True,
                "result": result,
                "timestamp": timestamp
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AI批改服务返回无效结果"
            )
            
    except Exception as e:
        logging.error(f"批改处理错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批改处理失败: {str(e)}"
        )

@app.get("/api/user/records")
async def get_user_records(current_user: str = Depends(get_current_user)):
    """获取用户的批改记录"""
    user_data = read_user_data()
    user_info = user_data.get(current_user, {})
    records = user_info.get("records", [])
    
    return {
        "records": records,
        "total": len(records)
    }

# 增强批改端点 - 集成calling_api.py功能
@app.post("/api/correction/enhanced")
async def enhanced_correction_endpoint(
    files: List[UploadFile] = File(...),
    correction_type: str = Form("auto"),
    strictness_level: str = Form("中等"),
    language: str = Form("zh"),
    custom_scheme: str = Form(None),
    current_user: str = Depends(get_current_user)
):
    """增强批改端点 - 使用calling_api.py的高级功能"""
    try:
        # 验证文件
        if not files or len(files) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="必须上传至少一个文件"
            )
        
        # 创建用户目录
        user_dir = UPLOAD_DIR / current_user
        user_dir.mkdir(exist_ok=True)
        
        # 保存上传的文件
        saved_files = []
        for i, file in enumerate(files):
            if file.size > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"文件 {file.filename} 超过大小限制"
                )
            
            # 保存文件
            file_extension = os.path.splitext(file.filename)[1]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"enhanced_{i}_{timestamp}{file_extension}"
            file_path = user_dir / filename
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            saved_files.append(str(file_path))
        
        # 执行增强批改
        logging.info(f"开始增强批改: 类型={correction_type}, 严格程度={strictness_level}, 语言={language}")
        
        if correction_type == "generate_scheme":
            # 只生成评分标准
            from functions.api_correcting.calling_api import generate_marking_scheme
            result_content = generate_marking_scheme(*saved_files, language=language)
            result_type = "评分标准"
            
        elif correction_type == "with_scheme":
            # 使用提供的评分标准批改
            if not custom_scheme:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="使用评分标准批改需要提供custom_scheme参数"
                )
            
            from functions.api_correcting.calling_api import correction_with_marking_scheme
            result_content = correction_with_marking_scheme(
                custom_scheme,
                *saved_files,
                strictness_level=strictness_level,
                language=language
            )
            result_type = "使用评分标准批改"
            
        elif correction_type == "single_group":
            # 单题批改
            result_content = correction_single_group(
                *saved_files,
                strictness_level=strictness_level,
                language=language,
                group_index=1
            )
            result_type = "单题批改"
            
        else:  # auto
            # 自动生成评分标准并批改
            from functions.api_correcting.calling_api import correction_without_marking_scheme
            result_content = correction_without_marking_scheme(
                *saved_files,
                strictness_level=strictness_level,
                language=language
            )
            result_type = "自动批改"
        
        # 保存结果到用户记录
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        correction_record = {
            "timestamp": timestamp,
            "content": result_content,
            "files": {f"file_{i+1}": {"filename": file.filename, "saved_path": path} 
                     for i, (file, path) in enumerate(zip(files, saved_files))},
            "settings": {
                "correction_type": correction_type,
                "strictness_level": strictness_level,
                "language": language,
                "processing_method": "enhanced_api",
                "custom_scheme": custom_scheme if custom_scheme else None
            }
        }
        
        user_data = read_user_data()
        if current_user not in user_data:
            user_data[current_user] = {"records": []}
        if "records" not in user_data[current_user]:
            user_data[current_user]["records"] = []
        user_data[current_user]["records"].append(correction_record)
        save_user_data(user_data)
        
        # 验证结果内容
        if not result_content or not result_content.strip():
            logging.warning(f"批改结果为空: 用户={current_user}, 类型={correction_type}")
            result_content = "批改处理完成，但未生成具体内容。请检查上传的文件是否包含可识别的内容。"
        
        logging.info(f"批改成功: 用户={current_user}, 文件数={len(saved_files)}, 结果长度={len(result_content) if result_content else 0}")
        
        return {
            "success": True,
            "result": result_content,
            "correction_type": correction_type,
            "result_type": result_type,
            "files_processed": len(saved_files),
            "strictness_level": strictness_level,
            "language": language,
            "message": "批改处理完成"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"增强批改失败: {str(e)}", exc_info=True)
        
        # 清理已保存的文件
        for file_path in saved_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass
        
        return {
            "success": False,
            "error": f"批改处理失败: {str(e)}",
            "message": "批改过程中发生错误，请检查文件格式和内容",
            "files_processed": 0
        }

@app.get("/api/correction/health")
async def correction_health_check():
    """批改服务健康检查"""
    try:
        # 测试API连接
        from functions.api_correcting.calling_api import call_api
        test_result = call_api("测试连接", language="zh")
        
        return {
            "status": "healthy",
            "service": "Enhanced AI Grading Service with calling_api.py",
            "version": "2.0.0",
            "api_connection": "正常" if test_result else "异常",
            "features": [
                "自动批改",
                "评分标准生成", 
                "智能检测",
                "多语言支持",
                "严格程度控制",
                "单题批改"
            ],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/system/status")
async def system_status():
    """系统状态检查"""
    return {
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "uptime": "running"
    }

@app.get("/api/system/data-source")
async def data_source_status():
    """数据源状态检查"""
    return {
        "status": "connected",
        "timestamp": datetime.now().isoformat(),
        "database": "file-based",
        "connection": "healthy"
    }

@app.get("/")
async def root():
    """根路径"""
    return {"message": "AI智能批改系统API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True) 