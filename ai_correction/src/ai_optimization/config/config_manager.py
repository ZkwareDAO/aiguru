"""
配置管理器

支持多源配置加载、验证和热重载功能。
"""

import os
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import threading
import time
from pathlib import Path

# 尝试导入yaml，如果不存在则使用简化版本
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    print("警告: PyYAML未安装，将使用JSON格式作为替代")

from .config_sources import EnvironmentConfigSource, FileConfigSource, DatabaseConfigSource


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径，默认为 config/ai_optimization.json
        """
        self.config_file = config_file or "config/ai_optimization.json"
        self.config_data: Dict[str, Any] = {}
        self.config_sources: List = []
        self.watchers: Dict[str, callable] = {}
        self.last_modified: Dict[str, float] = {}
        self._lock = threading.RLock()
        self._hot_reload_enabled = False
        self._reload_thread = None
        
        # 初始化配置源
        self._init_config_sources()
        
        # 加载配置
        self.reload_config()
    
    def _init_config_sources(self):
        """初始化配置源"""
        # 按优先级顺序添加配置源（后面的会覆盖前面的）
        self.config_sources = [
            FileConfigSource(self.config_file),
            EnvironmentConfigSource(),
            # DatabaseConfigSource()  # 可选的数据库配置源
        ]
    
    def reload_config(self) -> bool:
        """重新加载配置"""
        try:
            with self._lock:
                new_config = {}
                
                # 按顺序加载各个配置源
                for source in self.config_sources:
                    try:
                        source_config = source.load()
                        if source_config:
                            new_config = self._merge_config(new_config, source_config)
                    except Exception as e:
                        print(f"警告: 加载配置源 {source.__class__.__name__} 失败: {e}")
                
                # 验证配置
                if self._validate_config(new_config):
                    old_config = self.config_data.copy()
                    self.config_data = new_config
                    
                    # 触发配置变更回调
                    self._notify_config_change(old_config, new_config)
                    
                    return True
                else:
                    print("配置验证失败，保持原有配置")
                    return False
                    
        except Exception as e:
            print(f"重新加载配置失败: {e}")
            return False
    
    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """合并配置"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置"""
        try:
            # 基本结构验证
            required_sections = ['ai_optimization', 'models', 'quality_control']
            for section in required_sections:
                if section not in config:
                    print(f"缺少必需的配置节: {section}")
                    return False
            
            # AI优化配置验证
            ai_config = config.get('ai_optimization', {})
            if 'prompt_engine' not in ai_config:
                print("缺少 prompt_engine 配置")
                return False
            
            # 模型配置验证
            models_config = config.get('models', {})
            if not isinstance(models_config, dict):
                print("models 配置必须是字典类型")
                return False
            
            # 质量控制配置验证
            quality_config = config.get('quality_control', {})
            if 'rules' not in quality_config:
                print("缺少 quality_control.rules 配置")
                return False
            
            return True
            
        except Exception as e:
            print(f"配置验证异常: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键，如 'ai_optimization.prompt_engine.cache_size'
            default: 默认值
            
        Returns:
            配置值
        """
        with self._lock:
            try:
                keys = key.split('.')
                value = self.config_data
                
                for k in keys:
                    if isinstance(value, dict) and k in value:
                        value = value[k]
                    else:
                        return default
                
                return value
                
            except Exception:
                return default
    
    def set(self, key: str, value: Any) -> bool:
        """
        设置配置值（仅在内存中，不持久化）
        
        Args:
            key: 配置键
            value: 配置值
            
        Returns:
            是否设置成功
        """
        try:
            with self._lock:
                keys = key.split('.')
                config = self.config_data
                
                # 导航到目标位置
                for k in keys[:-1]:
                    if k not in config:
                        config[k] = {}
                    config = config[k]
                
                # 设置值
                config[keys[-1]] = value
                return True
                
        except Exception as e:
            print(f"设置配置失败: {e}")
            return False
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        获取配置节
        
        Args:
            section: 节名称
            
        Returns:
            配置节字典
        """
        return self.get(section, {})
    
    def has(self, key: str) -> bool:
        """
        检查配置键是否存在
        
        Args:
            key: 配置键
            
        Returns:
            是否存在
        """
        return self.get(key) is not None
    
    def watch(self, key: str, callback: callable):
        """
        监听配置变更
        
        Args:
            key: 要监听的配置键
            callback: 变更回调函数，接收 (old_value, new_value) 参数
        """
        self.watchers[key] = callback
    
    def unwatch(self, key: str):
        """
        取消监听配置变更
        
        Args:
            key: 配置键
        """
        if key in self.watchers:
            del self.watchers[key]
    
    def _notify_config_change(self, old_config: Dict[str, Any], new_config: Dict[str, Any]):
        """通知配置变更"""
        for key, callback in self.watchers.items():
            try:
                old_value = self._get_value_from_config(old_config, key)
                new_value = self._get_value_from_config(new_config, key)
                
                if old_value != new_value:
                    callback(old_value, new_value)
                    
            except Exception as e:
                print(f"配置变更回调执行失败 {key}: {e}")
    
    def _get_value_from_config(self, config: Dict[str, Any], key: str) -> Any:
        """从配置字典中获取值"""
        try:
            keys = key.split('.')
            value = config
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return None
            
            return value
            
        except Exception:
            return None
    
    def enable_hot_reload(self, interval: int = 5):
        """
        启用热重载
        
        Args:
            interval: 检查间隔（秒）
        """
        if self._hot_reload_enabled:
            return
        
        self._hot_reload_enabled = True
        self._reload_thread = threading.Thread(
            target=self._hot_reload_worker,
            args=(interval,),
            daemon=True
        )
        self._reload_thread.start()
    
    def disable_hot_reload(self):
        """禁用热重载"""
        self._hot_reload_enabled = False
        if self._reload_thread:
            self._reload_thread.join(timeout=1)
    
    def _hot_reload_worker(self, interval: int):
        """热重载工作线程"""
        while self._hot_reload_enabled:
            try:
                # 检查配置文件是否有变更
                if os.path.exists(self.config_file):
                    current_mtime = os.path.getmtime(self.config_file)
                    last_mtime = self.last_modified.get(self.config_file, 0)
                    
                    if current_mtime > last_mtime:
                        print(f"检测到配置文件变更，重新加载: {self.config_file}")
                        if self.reload_config():
                            self.last_modified[self.config_file] = current_mtime
                            print("配置重新加载成功")
                        else:
                            print("配置重新加载失败")
                
                time.sleep(interval)
                
            except Exception as e:
                print(f"热重载检查异常: {e}")
                time.sleep(interval)
    
    def export_config(self, format: str = 'yaml') -> str:
        """
        导出当前配置
        
        Args:
            format: 导出格式，支持 'yaml' 或 'json'
            
        Returns:
            配置字符串
        """
        with self._lock:
            if format.lower() == 'json' or not YAML_AVAILABLE:
                return json.dumps(self.config_data, indent=2, ensure_ascii=False)
            else:
                return yaml.dump(self.config_data, default_flow_style=False, allow_unicode=True)
    
    def save_config(self, file_path: Optional[str] = None) -> bool:
        """
        保存配置到文件
        
        Args:
            file_path: 保存路径，默认为当前配置文件
            
        Returns:
            是否保存成功
        """
        try:
            save_path = file_path or self.config_file
            
            # 确保目录存在
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # 保存配置
            with open(save_path, 'w', encoding='utf-8') as f:
                if YAML_AVAILABLE and save_path.endswith(('.yaml', '.yml')):
                    yaml.dump(self.config_data, f, default_flow_style=False, allow_unicode=True)
                else:
                    # 如果YAML不可用或文件不是YAML格式，使用JSON
                    json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False
    
    def get_config_info(self) -> Dict[str, Any]:
        """获取配置信息"""
        return {
            "config_file": self.config_file,
            "config_sources": [source.__class__.__name__ for source in self.config_sources],
            "hot_reload_enabled": self._hot_reload_enabled,
            "watchers_count": len(self.watchers),
            "last_reload": datetime.now().isoformat(),
            "config_keys": list(self.config_data.keys())
        }
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disable_hot_reload()


# 全局配置管理器实例
_global_config_manager = None


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = ConfigManager()
    return _global_config_manager


def get_config(key: str, default: Any = None) -> Any:
    """获取配置值的便捷函数"""
    return get_config_manager().get(key, default)


def set_config(key: str, value: Any) -> bool:
    """设置配置值的便捷函数"""
    return get_config_manager().set(key, value)