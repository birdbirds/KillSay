import base64
import json
from typing import Optional, Dict, Any, Tuple


def generate_share_code(config: Dict[str, Any], name: Optional[str] = None) -> str:
    """
    生成配置分享码
    
    格式: KS1-<Base64编码的JSON>
    
    Args:
        config: 配置字典
        name: 配置名称（可选）
    
    Returns:
        分享码字符串
    """
    data = {
        "v": 1,
    }
    
    if name:
        data["name"] = name
    
    data["config"] = config
    
    # 转换为紧凑JSON并Base64编码
    json_str = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
    base64_str = base64.b64encode(json_str.encode('utf-8')).decode('ascii')
    return f"KS1-{base64_str}"


def parse_share_code(code: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    解析配置分享码
    
    Args:
        code: 分享码字符串
    
    Returns:
        (config_data, error_message) 元组
        如果成功，config_data 为配置字典，error_message 为 None
        如果失败，config_data 为 None，error_message 为错误信息
    """
    code = code.strip()
    
    # 检查前缀
    if not code.startswith("KS1-"):
        return None, "无效的分享码格式：缺少 KS1- 前缀"
    
    try:
        # 移除前缀并解码
        base64_str = code[4:]
        json_str = base64.b64decode(base64_str).decode('utf-8')
        data = json.loads(json_str)
    except Exception as e:
        return None, f"解码失败：{e}"
    
    # 验证版本
    if not data.get('v') or data['v'] != 1:
        return None, "不支持的分享码版本"
    
    # 验证配置
    if 'config' not in data:
        return None, "分享码中没有配置数据"
    
    return data, None


def import_config_from_share_code(code: str, config_manager) -> Tuple[bool, str]:
    """
    从分享码导入配置
    
    Args:
        code: 分享码
        config_manager: ConfigManager 实例
    
    Returns:
        (success, message) 元组
    """
    data, error = parse_share_code(code)
    
    if error:
        return False, error
    
    try:
        config_name = data.get('name', 'imported')
        config_data = data['config']
        
        # 创建新配置
        config_path = config_manager.config_dir / f"{config_name}.json"
        
        # 如果配置已存在，添加后缀
        counter = 1
        original_name = config_name
        while config_path.exists():
            config_name = f"{original_name}_{counter}"
            config_path = config_manager.config_dir / f"{config_name}.json"
            counter += 1
        
        # 保存配置
        config_manager.save_config(config_path, config_data)
        
        return True, f"配置 '{config_name}' 导入成功"
    except Exception as e:
        return False, f"导入失败：{e}"


def export_config_to_share_code(config_manager, include_name: bool = True) -> Optional[str]:
    """
    导出当前配置为分享码
    
    Args:
        config_manager: ConfigManager 实例
        include_name: 是否包含配置名称
    
    Returns:
        分享码字符串，如果失败返回 None
    """
    if not config_manager.current_config:
        return None
    
    name = None
    if include_name and config_manager.current_config_path:
        name = config_manager.current_config_path.stem
    
    return generate_share_code(config_manager.current_config, name)
