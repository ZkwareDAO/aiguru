"""
配置源实现

支持环境变量、文件和数据库等多种配置源。
"""

import os
import json
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

# 尝试导入yaml，如果不存在则使用简化版本
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


class ConfigSource(ABC):
    """配置源基类"""
    
    @abstractmethod
    def load(self) -> Dict[str, Any]:
        """加载配置"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查配置源是否可用"""
        pass


class EnvironmentConfigSource(ConfigSource):
    """环境变量配置源"""
    
    def __init__(self, prefix: str = "AI_OPT_"):
        """
        初始化环境变量配置源
        
        Args:
            prefix: 环境变量前缀
        """
        self.prefix = prefix
    
    def load(self) -> Dict[str, Any]:
        """从环境变量加载配置"""
        config = {}
        
        for key, value in os.environ.items():
            if key.startswith(self.prefix):
                # 移除前缀并转换为小写
                config_key = key[len(self.prefix):].lower()
                
                # 转换嵌套键（用双下划线分隔）
                if '__' in config_key:
                    self._set_nested_value(config, config_key.split('__'), value)
                else:
                    config[config_key] = self._convert_value(value)
        
        return config
    
    def _set_nested_value(self, config: Dict[str, Any], keys: list, value: str):
        """设置嵌套配置值"""
        current = config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = self._convert_value(value)
    
    def _convert_value(self, value: str) -> Any:
        """转换环境变量值类型"""
        # 尝试转换为布尔值
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # 尝试转换为数字
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # 尝试转换为JSON
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            pass
        
        # 返回字符串
        return value
    
    def is_available(self) -> bool:
        """检查是否有相关环境变量"""
        return any(key.startswith(self.prefix) for key in os.environ.keys())


class FileConfigSource(ConfigSource):
    """文件配置源"""
    
    def __init__(self, file_path: str):
        """
        初始化文件配置源
        
        Args:
            file_path: 配置文件路径
        """
        self.file_path = file_path
    
    def load(self) -> Dict[str, Any]:
        """从文件加载配置"""
        if not self.is_available():
            return {}
        
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                if self.file_path.endswith('.json'):
                    return json.load(f)
                elif self.file_path.endswith(('.yaml', '.yml')):
                    if YAML_AVAILABLE:
                        return yaml.safe_load(f) or {}
                    else:
                        print(f"警告: YAML文件 {self.file_path} 无法加载，因为PyYAML未安装")
                        return {}
                else:
                    # 尝试YAML格式
                    if YAML_AVAILABLE:
                        return yaml.safe_load(f) or {}
                    else:
                        # 如果YAML不可用，尝试JSON格式
                        try:
                            f.seek(0)
                            return json.load(f)
                        except json.JSONDecodeError:
                            print(f"警告: 无法解析配置文件 {self.file_path}，需要PyYAML支持")
                            return {}
                    
        except Exception as e:
            print(f"加载配置文件失败 {self.file_path}: {e}")
            return {}
    
    def is_available(self) -> bool:
        """检查配置文件是否存在"""
        return os.path.exists(self.file_path) and os.path.isfile(self.file_path)


class DatabaseConfigSource(ConfigSource):
    """数据库配置源"""
    
    def __init__(self, connection_string: Optional[str] = None, table_name: str = "ai_config"):
        """
        初始化数据库配置源
        
        Args:
            connection_string: 数据库连接字符串
            table_name: 配置表名
        """
        self.connection_string = connection_string or os.getenv('AI_CONFIG_DB_URL')
        self.table_name = table_name
        self._connection = None
    
    def load(self) -> Dict[str, Any]:
        """从数据库加载配置"""
        if not self.is_available():
            return {}
        
        try:
            import sqlite3
            
            with sqlite3.connect(self.connection_string) as conn:
                cursor = conn.cursor()
                
                # 检查表是否存在
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name=?
                """, (self.table_name,))
                
                if not cursor.fetchone():
                    return {}
                
                # 查询配置
                cursor.execute(f"SELECT key, value FROM {self.table_name}")
                rows = cursor.fetchall()
                
                config = {}
                for key, value in rows:
                    try:
                        # 尝试解析JSON值
                        parsed_value = json.loads(value)
                        self._set_nested_key(config, key, parsed_value)
                    except (json.JSONDecodeError, ValueError):
                        # 如果不是JSON，直接使用字符串值
                        self._set_nested_key(config, key, value)
                
                return config
                
        except Exception as e:
            print(f"从数据库加载配置失败: {e}")
            return {}
    
    def _set_nested_key(self, config: Dict[str, Any], key: str, value: Any):
        """设置嵌套键值"""
        if '.' in key:
            keys = key.split('.')
            current = config
            
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
            
            current[keys[-1]] = value
        else:
            config[key] = value
    
    def is_available(self) -> bool:
        """检查数据库配置源是否可用"""
        if not self.connection_string:
            return False
        
        try:
            import sqlite3
            # 简单的连接测试
            with sqlite3.connect(self.connection_string) as conn:
                conn.execute("SELECT 1")
            return True
        except Exception:
            return False
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """保存配置到数据库"""
        if not self.connection_string:
            return False
        
        try:
            import sqlite3
            
            with sqlite3.connect(self.connection_string) as conn:
                cursor = conn.cursor()
                
                # 创建配置表
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 清空现有配置
                cursor.execute(f"DELETE FROM {self.table_name}")
                
                # 插入新配置
                flat_config = self._flatten_config(config)
                for key, value in flat_config.items():
                    cursor.execute(
                        f"INSERT INTO {self.table_name} (key, value) VALUES (?, ?)",
                        (key, json.dumps(value, ensure_ascii=False))
                    )
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"保存配置到数据库失败: {e}")
            return False
    
    def _flatten_config(self, config: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """扁平化配置字典"""
        result = {}
        
        for key, value in config.items():
            full_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                result.update(self._flatten_config(value, full_key))
            else:
                result[full_key] = value
        
        return result


class MultiConfigSource(ConfigSource):
    """多配置源组合"""
    
    def __init__(self, sources: list):
        """
        初始化多配置源
        
        Args:
            sources: 配置源列表，按优先级排序
        """
        self.sources = sources
    
    def load(self) -> Dict[str, Any]:
        """加载所有配置源并合并"""
        merged_config = {}
        
        for source in self.sources:
            if source.is_available():
                try:
                    source_config = source.load()
                    merged_config = self._merge_config(merged_config, source_config)
                except Exception as e:
                    print(f"加载配置源失败 {source.__class__.__name__}: {e}")
        
        return merged_config
    
    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """合并配置"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def is_available(self) -> bool:
        """检查是否有可用的配置源"""
        return any(source.is_available() for source in self.sources)