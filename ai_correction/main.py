from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os
import json
import hashlib
from datetime import datetime, timedelta
import time
import logging
from pathlib import Path
from functions.api_correcting.pdf_merger import PDFMerger, ImageToPDFConverter
from functions.api_correcting.calling_api import (
    correction_with_image_marking_scheme, 
    correction_with_marking_scheme, 
    correction_without_marking_scheme,
    correction_single_group,
    generate_comprehensive_summary
)
import re
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import jwt
import secrets
from enum import Enum
import tempfile
import shutil
import base64

# 应用设置
app = FastAPI(
    title="AI智能批改系统",
    description="AI赋能教育，智能批改新纪元",
    version="1.0.0"
)

# CORS设置 - 最宽松配置用于测试
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=False,  # 禁用凭据以避免冲突
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有头部
)

# 静态文件服务（用于前端）
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# 常量
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
UPLOAD_DIR = Path("uploads")
DATA_FILE = Path("user_data.json")
MAX_RECORD_AGE_DAYS = 7
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 创建必要的目录
UPLOAD_DIR.mkdir(exist_ok=True)

# 测试账户
TEST_ACCOUNTS = {
    "testuser": {"password": "123456"},
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

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class EmailUpdate(BaseModel):
    new_email: str

class CorrectionSettings(BaseModel):
    strictness_level: str = "中等"
    language: str = "zh"

class StrictnessLevel(str, Enum):
    loose = "宽松"
    medium = "中等"
    strict = "严格"

class Language(str, Enum):
    zh = "zh"
    en = "en"

# 安全相关
security = HTTPBearer(auto_error=False)

def setup_logger(log_dir="logs"):
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_file = os.path.join(log_dir, "app_debug.log")
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s @ %(module)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

# 初始化日志
setup_logger()
logging.info("FastAPI应用启动")

# 初始化存储结构
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

def filter_old_records(user_data):
    """过滤掉超过MAX_RECORD_AGE_DAYS天的记录"""
    current_date = datetime.now()
    cutoff_date = current_date - timedelta(days=MAX_RECORD_AGE_DAYS)
    records_removed = 0

    for username, user_info in user_data.items():
        if isinstance(user_info, dict) and 'records' in user_info and isinstance(user_info['records'], list):
            filtered_records = []
            for record in user_info['records']:
                timestamp_str = record.get('timestamp')
                if not timestamp_str:
                    filtered_records.append(record)
                    continue

                try:
                    record_date = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                    if record_date >= cutoff_date:
                        filtered_records.append(record)
                    else:
                        records_removed += 1
                except (ValueError, TypeError):
                    filtered_records.append(record)

            user_info['records'] = filtered_records

    if records_removed > 0:
        logging.info(f"移除了{records_removed}条超过{MAX_RECORD_AGE_DAYS}天的记录")

    return user_data

def read_user_data():
    """从JSON文件读取用户数据"""
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)

            # 确保测试账户存在
            for test_user, details in TEST_ACCOUNTS.items():
                if test_user not in data:
                    data[test_user] = {
                        "password": details["password"],
                        "email": f"{test_user}@example.com",
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "records": []
                    }

            # 过滤旧记录
            data = filter_old_records(data)
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
    """保存用户数据到JSON文件"""
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def hash_password(password):
    """对密码进行哈希处理"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_access_token(data: dict, expires_delta: timedelta = None):
    """创建JWT访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    """验证JWT令牌"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except jwt.PyJWTError:
        return None

def create_simple_jwt_token(username: str):
    """创建一个简单的JWT格式token（不使用加密）"""
    # 创建header
    header = {"alg": "none", "typ": "JWT"}
    
    # 创建payload
    exp_time = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": username,
        "exp": int(exp_time.timestamp()),
        "iat": int(datetime.utcnow().timestamp())
    }
    
    # Base64编码
    header_encoded = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
    payload_encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    
    # 创建简单JWT格式 (header.payload.signature)
    token = f"{header_encoded}.{payload_encoded}.signature"
    return token

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """获取当前用户"""
    # 检查 credentials 是否存在
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌为空",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 简化的token验证 - 支持测试token
    if token.startswith("test_token_"):
        try:
            parts = token.split("_")
            if len(parts) >= 3:
                username = parts[2]
                return username
        except:
            pass
    
    # 尝试JWT验证
    username = verify_token(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return username

def ensure_valid_file_path(file_path):
    """确保文件路径有效"""
    str_path = str(file_path) if file_path is not None else ""
    is_valid = os.path.exists(str_path) if str_path else False
    
    if not is_valid and str_path:
        logging.warning(f"文件未找到: {str_path}")
    
    return is_valid, str_path

def save_uploaded_file(user_dir: Path, file: UploadFile, file_type: str) -> Path:
    """保存上传的文件"""
    file_extension = os.path.splitext(file.filename)[1]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{file_type}_{timestamp}{file_extension}"
    file_path = user_dir / filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return file_path

def detect_file_groups(user_files):
    """检测文件分组"""
    if not user_files:
        return []
        
    if len(user_files) <= 3:
        return [list(user_files.keys())]
        
    numbered_groups = {}
    unnumbered_files = []
    
    for file_key in user_files.keys():
        number_match = re.search(r'(\d+)', file_key)
        
        if number_match:
            question_number = number_match.group(1)
            if question_number not in numbered_groups:
                numbered_groups[question_number] = []
            numbered_groups[question_number].append(file_key)
        else:
            unnumbered_files.append(file_key)
    
    file_groups = list(numbered_groups.values())
    
    if unnumbered_files:
        if not file_groups:
            file_groups.append(unnumbered_files)
        else:
            for file_key in unnumbered_files:
                file_type = None
                if "question" in file_key:
                    file_type = "question"
                elif "student_answer" in file_key:
                    file_type = "student_answer"
                elif "marking_scheme" in file_key:
                    file_type = "marking_scheme"
                
                if file_type:
                    for group in file_groups:
                        has_this_type = False
                        for existing_file in group:
                            if file_type in existing_file:
                                has_this_type = True
                                break
                        
                        if not has_this_type:
                            group.append(file_key)
                            break
                    else:
                        if file_groups:
                            file_groups[0].append(file_key)
    
    return file_groups

def parse_correction_blocks(correction_content):
    """解析批改内容块"""
    if not correction_content:
        return []
        
    content = re.sub(r'^学生答案批改如下:\s*', '', correction_content)
    question_markers = re.findall(r'(第\s*\d+\s*题|题目\s*\d+)', content)
    
    if not question_markers:
        return [content]
        
    blocks = []
    for i, marker in enumerate(question_markers):
        if i < len(question_markers) - 1:
            next_marker = question_markers[i + 1]
            pattern = f'({re.escape(marker)}.+?)(?={re.escape(next_marker)})'
        else:
            pattern = f'({re.escape(marker)}.+)'
            
        match = re.search(pattern, content, re.DOTALL)
        if match:
            blocks.append(match.group(1).strip())
    
    if not blocks:
        blocks = [content]
        
    return blocks

# API路由

@app.get("/")
async def read_root():
    """根路径重定向到前端"""
    return FileResponse("前端/app/page.tsx")

@app.post("/api/auth/login")
async def login(credentials: UserLogin):
    print(f"[DEBUG] 登录请求开始")
    print(f"[DEBUG] 收到登录请求: {credentials.username}")
    
    # 简单的用户验证（实际项目中应该查询数据库）
    valid_users = {
        "testuser": "123456",
        "test_user_2": "password2",
        "admin": "admin123"
    }
    
    if credentials.username in valid_users and valid_users[credentials.username] == credentials.password:
        # 创建简单JWT token
        access_token = create_simple_jwt_token(credentials.username)
        
        response_data = {
            "access_token": access_token,
            "token_type": "bearer",
            "username": credentials.username
        }
        print(f"[DEBUG] 登录成功，返回token长度: {len(access_token)}")
        return response_data
    else:
        print(f"[DEBUG] 登录失败: {credentials.username}")
        raise HTTPException(status_code=401, detail="用户名或密码错误")

@app.get("/api/test")
async def test_endpoint():
    """测试端点"""
    return {"message": "测试成功", "timestamp": datetime.now().isoformat()}

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
    
    # 创建新用户
    user_db[user_data.username] = {
        "password": hash_password(user_data.password),
        "email": user_data.email or "",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "records": []
    }
    save_user_data(user_db)
    
    return {"message": "注册成功"}

@app.get("/api/user/profile")
async def get_user_profile(current_user: str = Depends(get_current_user)):
    """获取用户资料"""
    user_data = read_user_data()
    user_info = user_data.get(current_user, {})
    
    return {
        "username": current_user,
        "email": user_info.get("email", ""),
        "created_at": user_info.get("created_at", ""),
        "record_count": len(user_info.get("records", []))
    }

@app.put("/api/user/password")
async def change_password(
    password_data: PasswordChange,
    current_user: str = Depends(get_current_user)
):
    """修改密码"""
    user_data = read_user_data()
    user_info = user_data.get(current_user, {})
    
    # 验证当前密码
    if current_user in TEST_ACCOUNTS:
        if password_data.current_password != TEST_ACCOUNTS[current_user]['password']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="当前密码错误"
            )
    else:
        if user_info.get('password') != hash_password(password_data.current_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="当前密码错误"
            )
    
    # 更新密码
    user_info['password'] = hash_password(password_data.new_password)
    user_data[current_user] = user_info
    save_user_data(user_data)
    
    return {"message": "密码修改成功"}

@app.put("/api/user/email")
async def update_email(
    email_data: EmailUpdate,
    current_user: str = Depends(get_current_user)
):
    """更新邮箱"""
    user_data = read_user_data()
    user_info = user_data.get(current_user, {})
    
    user_info['email'] = email_data.new_email
    user_data[current_user] = user_info
    save_user_data(user_data)
    
    return {"message": "邮箱更新成功"}

@app.get("/api/user/records")
async def get_user_records(
    page: int = 0,
    per_page: int = 9,
    current_user: str = Depends(get_current_user)
):
    """获取用户批改记录"""
    user_data = read_user_data()
    user_records = user_data.get(current_user, {}).get('records', [])
    
    # 过滤空内容记录
    filtered_records = [
        record for record in user_records 
        if record.get('content') and record['content'].strip()
    ]
    
    # 分页
    start_idx = page * per_page
    end_idx = start_idx + per_page
    paginated_records = filtered_records[start_idx:end_idx]
    
    total_pages = len(filtered_records) // per_page
    if len(filtered_records) % per_page > 0:
        total_pages += 1
    
    return {
        "records": paginated_records,
        "total": len(filtered_records),
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages
    }

@app.get("/api/user/records/{record_index}")
async def get_record_detail(
    record_index: int,
    current_user: str = Depends(get_current_user)
):
    """获取特定记录详情"""
    user_data = read_user_data()
    user_records = user_data.get(current_user, {}).get('records', [])
    
    if record_index < 0 or record_index >= len(user_records):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="记录不存在"
        )
    
    # 记录索引是从新到老的顺序
    actual_index = len(user_records) - 1 - record_index
    record = user_records[actual_index]
    
    return {
        "record": record,
        "record_index": record_index
    }

@app.delete("/api/user/records/{record_index}")
async def delete_record(
    record_index: int,
    current_user: str = Depends(get_current_user)
):
    """删除特定记录"""
    user_data = read_user_data()
    user_records = user_data.get(current_user, {}).get('records', [])
    
    if record_index < 0 or record_index >= len(user_records):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="记录不存在"
        )
    
    # 记录索引是从新到老的顺序
    actual_index = len(user_records) - 1 - record_index
    user_records.pop(actual_index)
    
    user_data[current_user]['records'] = user_records
    save_user_data(user_data)
    
    return {"message": "记录删除成功"}

@app.delete("/api/user/records")
async def clear_all_records(current_user: str = Depends(get_current_user)):
    """清除所有记录"""
    user_data = read_user_data()
    user_data[current_user]['records'] = []
    save_user_data(user_data)
    
    return {"message": "所有记录已清除"}

@app.get("/api/user/statistics")
async def get_user_statistics(current_user: str = Depends(get_current_user)):
    """获取用户统计信息"""
    user_data = read_user_data()
    user_records = user_data.get(current_user, {}).get('records', [])
    
    # 过滤空内容记录
    filtered_records = [
        record for record in user_records 
        if record.get('content') and record['content'].strip()
    ]
    
    # 计算基本统计
    total_corrections = len(filtered_records)
    
    # 语言统计
    language_stats = {"zh": 0, "en": 0}
    for record in filtered_records:
        lang = record.get('settings', {}).get('language', 'zh')
        if lang in language_stats:
            language_stats[lang] += 1
    
    # 严格程度统计
    strictness_stats = {"宽松": 0, "中等": 0, "严格": 0}
    for record in filtered_records:
        strictness = record.get('settings', {}).get('strictness_level', '中等')
        if strictness in strictness_stats:
            strictness_stats[strictness] += 1
    
    # 最近7天活动统计
    from datetime import datetime, timedelta
    today = datetime.now()
    recent_activity = []
    
    for i in range(7):
        date = today - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        count = 0
        
        for record in filtered_records:
            try:
                record_date = datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00'))
                if record_date.strftime('%Y-%m-%d') == date_str:
                    count += 1
            except:
                continue
        
        recent_activity.append({
            "date": date_str,
            "count": count
        })
    
    # 按日期正序排列
    recent_activity.reverse()
    
    return {
        "total_corrections": total_corrections,
        "language_stats": language_stats,
        "strictness_stats": strictness_stats,
        "recent_activity": recent_activity
    }

@app.post("/api/correction/upload")
async def upload_files_for_correction(
    question_files: List[UploadFile] = File(None),
    student_answer_files: List[UploadFile] = File(...),
    marking_scheme_files: List[UploadFile] = File(None),
    strictness_level: str = Form("中等"),
    language: str = Form("zh"),
    current_user: str = Depends(get_current_user)
):
    """上传文件进行批改"""
    
    # 验证必需文件
    if not student_answer_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="必须上传至少一个学生答案文件"
        )
    
    # 创建用户目录
    user_dir = UPLOAD_DIR / current_user
    user_dir.mkdir(exist_ok=True)
    
    # 保存文件
    user_files = {}
    
    if question_files:
        for i, question in enumerate(question_files):
            if question.size > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"文件 {question.filename} 超过大小限制"
                )
            question_path = save_uploaded_file(user_dir, question, f"question_{i + 1}")
            user_files[f"question_{i + 1}"] = {
                "filename": question.filename,
                "saved_path": str(question_path)
            }
    
    for i, student_answer in enumerate(student_answer_files):
        if student_answer.size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"文件 {student_answer.filename} 超过大小限制"
            )
        answer_path = save_uploaded_file(user_dir, student_answer, f"student_answer_{i + 1}")
        user_files[f"student_answer_{i + 1}"] = {
            "filename": student_answer.filename,
            "saved_path": str(answer_path)
        }
    
    if marking_scheme_files:
        for i, marking_scheme in enumerate(marking_scheme_files):
            if marking_scheme.size > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"文件 {marking_scheme.filename} 超过大小限制"
                )
            scheme_path = save_uploaded_file(user_dir, marking_scheme, f"marking_scheme_{i + 1}")
            user_files[f"marking_scheme_{i + 1}"] = {
                "filename": marking_scheme.filename,
                "saved_path": str(scheme_path)
            }
    
    # 开始批改处理
    try:
        # 检测文件分组
        file_groups = detect_file_groups(user_files)
        logging.info(f"检测到{len(file_groups)}个文件组用于分别调用API")
        
        # 存储所有API结果
        all_api_results = []
        
        # 为每个文件组单独调用API
        for group_idx, group in enumerate(file_groups):
            # 准备当前组的图像文件
            group_image_files = []
            group_file_info = {}
            
            # 按照题目、学生答案、评分标准的顺序添加文件
            file_types_order = ["question", "student_answer", "marking_scheme"]
            
            for file_type in file_types_order:
                for file_key in group:
                    if file_type in file_key and file_key in user_files:
                        file_path = user_files[file_key]["saved_path"]
                        group_image_files.append(file_path)
                        group_file_info[file_key] = user_files[file_key]
                        break
            
            if not group_image_files:
                logging.warning(f"第{group_idx + 1}组未找到有效文件")
                continue
            
            logging.info(f"第{group_idx + 1}组: 使用{len(group_image_files)}个文件调用API")
            
            try:
                # 调用API进行批改
                group_api_result = correction_single_group(
                    *group_image_files,
                    strictness_level=strictness_level,
                    language=language,
                    group_index=group_idx + 1
                )
                
                if group_api_result and isinstance(group_api_result, str):
                    # 为每个组的结果添加标识
                    if len(file_groups) > 1:
                        group_header = f"\n\n=== 第 {group_idx + 1} 组批改结果 ===\n"
                        all_api_results.append(group_header + group_api_result)
                    else:
                        all_api_results.append(group_api_result)
                else:
                    error_msg = f"第 {group_idx + 1} 组API返回无效结果"
                    logging.error(error_msg)
                    all_api_results.append(f"\n\n=== 第 {group_idx + 1} 组处理失败 ===\n{error_msg}")
                    
            except Exception as group_e:
                error_msg = f"第 {group_idx + 1} 组处理失败: {str(group_e)}"
                logging.error(error_msg)
                all_api_results.append(f"\n\n=== 第 {group_idx + 1} 组处理失败 ===\n{error_msg}")
        
        # 合并所有API结果
        if all_api_results:
            # 过滤出成功的结果用于生成综合总结
            successful_results = [result for result in all_api_results if not "处理失败" in result]
            
            combined_result = "\n".join(all_api_results)
            
            # 如果有多个成功的结果，生成综合总结
            if len(successful_results) > 1:
                try:
                    comprehensive_summary = generate_comprehensive_summary(
                        successful_results, 
                        language=language, 
                        total_groups=len(successful_results)
                    )
                    
                    # 添加综合总结到结果中
                    combined_result += f"\n\n{'='*50}\n\n{comprehensive_summary}"
                    
                except Exception as summary_e:
                    logging.error(f"生成综合总结失败: {str(summary_e)}")
                    summary_error_msg = "综合总结生成失败，但各题批改结果正常" if language == "zh" else "Comprehensive summary generation failed, but individual problem grading results are normal"
                    combined_result += f"\n\n{'='*50}\n\n⚠️ {summary_error_msg}: {str(summary_e)}"
            
            # 保存结果到用户记录
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            correction_record = {
                "timestamp": timestamp,
                "content": combined_result,
                "files": user_files,
                "settings": {
                    "strictness_level": strictness_level,
                    "language": language,
                    "processing_method": "separate_api_calls",
                    "groups_processed": len(file_groups),
                    "has_comprehensive_summary": len(successful_results) > 1
                }
            }
            
            user_data = read_user_data()
            user_data[current_user]["records"].append(correction_record)
            save_user_data(user_data)
            
            return {
                "success": True,
                "result": combined_result,
                "files": user_files,
                "groups_processed": len(file_groups)
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="没有成功处理任何文件组"
            )
            
    except Exception as e:
        logging.error(f"批改处理错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批改处理失败: {str(e)}"
        )

@app.get("/api/correction/download/{record_index}")
async def download_correction_result(
    record_index: int,
    format: str = "txt",
    current_user: str = Depends(get_current_user)
):
    """下载批改结果"""
    user_data = read_user_data()
    user_records = user_data.get(current_user, {}).get('records', [])
    
    if record_index < 0 or record_index >= len(user_records):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="记录不存在"
        )
    
    # 记录索引是从新到老的顺序
    actual_index = len(user_records) - 1 - record_index
    record = user_records[actual_index]
    content = record.get('content', '')
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if format == "txt":
        filename = f"correction_result_{timestamp}.txt"
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
        temp_file.write(content)
        temp_file.close()
        
        return FileResponse(
            temp_file.name,
            filename=filename,
            media_type='text/plain',
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    elif format == "pdf":
        # 这里需要实现PDF生成逻辑
        try:
            user_dir = UPLOAD_DIR / current_user
            pdf_filename = f"correction_result_{timestamp}.pdf"
            output_path = user_dir / pdf_filename
            
            # 使用PDFMerger生成PDF
            pdf_merger = PDFMerger(UPLOAD_DIR)
            files_dict = record.get('files', {})
            
            files_to_include = {}
            for key, file_info in files_dict.items():
                if isinstance(file_info, dict) and 'saved_path' in file_info:
                    is_valid, file_path = ensure_valid_file_path(file_info['saved_path'])
                    if is_valid:
                        file_type = key.split('_')[0]  # 提取文件类型
                        files_to_include[file_type] = {'path': file_path}
            
            success, pdf_path = pdf_merger.merge_pdfs(
                files_to_include,
                content,
                "AI Correction Results",
                output_path
            )
            
            if success and os.path.exists(pdf_path):
                return FileResponse(
                    pdf_path,
                    filename=pdf_filename,
                    media_type='application/pdf',
                    headers={"Content-Disposition": f"attachment; filename={pdf_filename}"}
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="PDF生成失败"
                )
                
        except Exception as e:
            logging.error(f"PDF生成错误: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"PDF生成失败: {str(e)}"
            )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不支持的文件格式"
        )

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
        user_data[current_user]["records"].append(correction_record)
        save_user_data(user_data)
        
        return {
            "success": True,
            "result": result_content,
            "correction_type": correction_type,
            "result_type": result_type,
            "files_processed": len(saved_files),
            "strictness_level": strictness_level,
            "language": language
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"增强批改失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"增强批改失败: {str(e)}"
        )

@app.post("/api/correction/intelligent")
async def intelligent_correction_endpoint(
    files: List[UploadFile] = File(...),
    auto_detect_type: bool = Form(True),
    strictness_level: str = Form("中等"),
    language: str = Form("zh"),
    current_user: str = Depends(get_current_user)
):
    """智能批改端点 - 自动检测最佳批改方式"""
    try:
        # 验证文件
        if not files or len(files) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="必须上传至少一个文件"
            )
        
        # 创建用户目录并保存文件
        user_dir = UPLOAD_DIR / current_user
        user_dir.mkdir(exist_ok=True)
        
        saved_files = []
        for i, file in enumerate(files):
            if file.size > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"文件 {file.filename} 超过大小限制"
                )
            
            file_extension = os.path.splitext(file.filename)[1]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"intelligent_{i}_{timestamp}{file_extension}"
            file_path = user_dir / filename
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            saved_files.append(str(file_path))
        
        # 智能检测批改类型
        if auto_detect_type:
            correction_type = detect_correction_type(saved_files)
        else:
            correction_type = "auto"
        
        logging.info(f"智能检测批改类型: {correction_type}")
        
        # 执行批改
        if correction_type == "single_group":
            result_content = correction_single_group(
                *saved_files,
                strictness_level=strictness_level,
                language=language,
                group_index=1
            )
        else:  # auto
            from functions.api_correcting.calling_api import correction_without_marking_scheme
            result_content = correction_without_marking_scheme(
                *saved_files,
                strictness_level=strictness_level,
                language=language
            )
        
        # 保存结果
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        correction_record = {
            "timestamp": timestamp,
            "content": result_content,
            "files": {f"file_{i+1}": {"filename": file.filename, "saved_path": path} 
                     for i, (file, path) in enumerate(zip(files, saved_files))},
            "settings": {
                "correction_type": "intelligent",
                "detected_type": correction_type,
                "strictness_level": strictness_level,
                "language": language,
                "processing_method": "intelligent_api",
                "auto_detect": auto_detect_type
            }
        }
        
        user_data = read_user_data()
        user_data[current_user]["records"].append(correction_record)
        save_user_data(user_data)
        
        return {
            "success": True,
            "result": result_content,
            "auto_detected_type": correction_type,
            "files_processed": len(saved_files),
            "message": f"智能批改完成 (类型: {correction_type})"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"智能批改失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"智能批改失败: {str(e)}"
        )

def detect_correction_type(file_paths: List[str]) -> str:
    """检测最佳批改类型"""
    try:
        # 简单的文件内容分析
        total_content = ""
        for file_path in file_paths:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    total_content += content
            except:
                # 如果无法读取为文本，可能是图像文件，跳过
                pass
        
        content_lower = total_content.lower()
        
        # 检测是否包含评分标准
        if any(keyword in content_lower for keyword in ['评分', '分值', '得分', 'scoring', 'marks', 'points']):
            return "with_scheme"
        
        # 检测是否为单题
        if len(file_paths) == 1 and len(total_content) < 1000:
            return "single_group"
        
        # 默认使用自动模式
        return "auto"
        
    except Exception:
        return "auto"

@app.get("/api/file/preview")
async def preview_file(
    path: str,
    current_user: str = Depends(get_current_user)
):
    """
    预览文件内容
    """
    try:
        # 标准化路径分隔符
        normalized_path = path.replace('\\', '/')
        file_path = Path(normalized_path)
        
        # 如果路径不是绝对路径，则相对于项目根目录
        if not file_path.is_absolute():
            file_path = Path.cwd() / normalized_path
            
        print(f"调试: 原始路径={path}, 标准化路径={normalized_path}, 最终路径={file_path}")
        
        if not file_path.exists():
            print(f"调试: 文件不存在 {file_path}")
            raise HTTPException(status_code=404, detail=f"文件不存在: {file_path}")
        
        # 确保文件在用户目录内
        user_dir = UPLOAD_DIR / current_user
        try:
            file_path.resolve().relative_to(user_dir.resolve())
            print(f"调试: 文件权限验证通过")
        except ValueError:
            print(f"调试: 无权访问文件 {file_path}, 用户目录 {user_dir}")
            raise HTTPException(status_code=403, detail="无权访问此文件")
        
        # 获取文件扩展名
        file_ext = file_path.suffix.lower()
        
        # 文本文件预览
        if file_ext in ['.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml']:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return {"type": "text", "content": content}
            except UnicodeDecodeError:
                try:
                    with open(file_path, 'r', encoding='gbk') as f:
                        content = f.read()
                    return {"type": "text", "content": content}
                except:
                    return {"type": "text", "content": "无法读取文件内容（编码问题）"}
        
        # 图片文件预览
        elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
            import base64
            try:
                with open(file_path, 'rb') as f:
                    image_data = f.read()
                    base64_data = base64.b64encode(image_data).decode('utf-8')
                return {
                    "type": "image", 
                    "base64": f"data:image/{file_ext[1:]};base64,{base64_data}",
                    "size": len(image_data)
                }
            except Exception as e:
                return {"type": "error", "message": f"无法读取图片: {str(e)}"}
        
        # PDF文件预览
        elif file_ext == '.pdf':
            try:
                file_size = file_path.stat().st_size
                
                # 尝试提取PDF文本内容
                try:
                    import PyPDF2
                    with open(file_path, 'rb') as pdf_file:
                        pdf_reader = PyPDF2.PdfReader(pdf_file)
                        text = ""
                        for page_num in range(min(len(pdf_reader.pages), 5)):  # 只读前5页
                            page = pdf_reader.pages[page_num]
                            text += page.extract_text() + "\n"
                        
                        if text.strip():
                            return {
                                "type": "text",
                                "content": f"PDF文件内容预览 ({file_size / 1024:.1f} KB):\n\n{text[:2000]}{'...' if len(text) > 2000 else ''}",
                                "size": file_size
                            }
                except ImportError:
                    pass
                except Exception as e:
                    print(f"PDF文本提取失败: {e}")
                
                # 如果文本提取失败，提供PDF作为图像的base64编码
                try:
                    import base64
                    with open(file_path, 'rb') as f:
                        pdf_data = f.read()
                        base64_data = base64.b64encode(pdf_data).decode('utf-8')
                    return {
                        "type": "image",
                        "base64": f"data:application/pdf;base64,{base64_data}",
                        "size": file_size,
                        "message": f"PDF文件 ({file_size / 1024:.1f} KB) - 以图像形式显示"
                    }
                except Exception as e:
                    return {
                        "type": "pdf",
                        "message": f"PDF文件 ({file_size / 1024:.1f} KB) - 点击下载查看",
                        "size": file_size,
                        "download_url": f"/api/file/download?path={path}"
                    }
            except Exception as e:
                return {"type": "error", "message": f"无法读取PDF: {str(e)}"}
        
        # 其他文件类型
        else:
            file_size = file_path.stat().st_size
            return {
                "type": "binary",
                "message": f"二进制文件 ({file_size / 1024:.1f} KB)",
                "size": file_size,
                "download_url": f"/api/file/download?path={path}"
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"文件预览失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"预览失败: {str(e)}")

@app.get("/api/file/download")
async def download_file(
    path: str,
    current_user: str = Depends(get_current_user)
):
    """
    下载文件
    """
    try:
        # 验证文件路径安全性
        file_path = Path(path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 确保文件在用户目录内
        user_dir = UPLOAD_DIR / current_user
        try:
            file_path.resolve().relative_to(user_dir.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="无权访问此文件")
        
        return FileResponse(
            path=file_path,
            filename=file_path.name,
            media_type='application/octet-stream'
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"文件下载失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")

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
    """健康检查端点"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/test-cors")
async def test_cors():
    """测试CORS配置"""
    return {"message": "CORS test successful", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
