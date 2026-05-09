import json
import os
import pathlib as pl
from datetime import datetime
from utils import get_base_dir

# ==================== 配置管理类 ====================
class ConfigManager:
    """管理多配置文件的加载、保存和切换"""
    
    DEFAULT_CONFIG = {
        "sniper_list": [""],
        "join_patterns": [
            "%t加入了游戏",
            "%t 加入了游戏",
            "%t joined the game",
            "%t 加入游戏",
            "%t 进入了游戏"
        ],
        "anti_snipe_messages": [
            "/PLAY SWRSOLO"
        ],
        "kill_patterns": [
            "%o被%u击败",
            "%o被炸成了粉尘, 幕后黑手是%u!",
            "%o消逝了, 幕后黑手是%u!",
            "%o被%u用弓箭射穿了",
            "%o跑得很快, 但是他还是摔了一跤, 最终被%u击败了",
            "%u击败了%o"
        ],
        "kill_messages": [
            "黄沙百战穿金甲，不破楼兰终不还。",
            "十步杀一人，千里不留行。",
            "会挽雕弓如满月，西北望，射天狼。",
            "壮志饥餐胡虏肉，笑谈渴饮匈奴血。",
            "谈笑间，樯橹灰飞烟灭。",
            "金戈铁马，气吞万里如虎。"
        ],
        "message_prefix": "",
        "killsay_format": "%t%m"
    }
    
    def __init__(self, config_dir=None):
        if config_dir is None:
            config_dir = os.path.join(get_base_dir(), "configs")
        self.config_dir = pl.Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.current_config_path = None
        self.current_config = None
        
        # 加载默认配置或上次使用的配置
        self._load_last_used()
    
    def _load_last_used(self):
        """加载上次使用的配置文件，如果不存在则创建默认配置"""
        last_used_file = self.config_dir / "last_used.json"
        if last_used_file.exists():
            try:
                with open(last_used_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    last_path = data.get("last_config")
                    if last_path and pl.Path(last_path).exists():
                        self.load_config(last_path)
                        return
            except:
                pass
        
        # 创建默认配置
        default_path = self.config_dir / "default.json"
        if not default_path.exists():
            self.save_config(default_path, self.DEFAULT_CONFIG)
        self.load_config(default_path)
    
    def get_config_list(self):
        """获取所有配置文件的列表"""
        configs = []
        for file in self.config_dir.glob("*.json"):
            if file.name != "last_used.json":
                configs.append({
                    "name": file.stem,
                    "path": str(file),
                    "modified": datetime.fromtimestamp(file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })
        return sorted(configs, key=lambda x: x["modified"], reverse=True)
    
    def load_config(self, config_path):
        """加载指定的配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 确保配置包含所有必要字段
            for key in self.DEFAULT_CONFIG:
                if key not in config:
                    config[key] = self.DEFAULT_CONFIG[key]
            
            self.current_config = config
            self.current_config_path = pl.Path(config_path)
            
            # 保存最近使用的配置
            self._save_last_used()
            
            return True
        except Exception as e:
            print(f"加载配置失败: {e}")
            return False
    
    def _save_last_used(self):
        """保存最近使用的配置路径"""
        last_used_file = self.config_dir / "last_used.json"
        try:
            with open(last_used_file, 'w', encoding='utf-8') as f:
                json.dump({"last_config": str(self.current_config_path)}, f)
        except:
            pass
    
    def save_current_config(self):
        """保存当前配置到当前路径"""
        if self.current_config_path:
            self.save_config(self.current_config_path, self.current_config)
    
    def save_config(self, config_path, config_data):
        """保存配置到指定路径"""
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
    
    def create_new_config(self, name):
        """创建新配置文件"""
        config_path = self.config_dir / f"{name}.json"
        if config_path.exists():
            raise Exception("配置文件已存在")
        
        self.save_config(config_path, self.DEFAULT_CONFIG)
        return config_path
    
    def delete_config(self, config_path):
        """删除配置文件"""
        path = pl.Path(config_path)
        if path.exists() and path != self.current_config_path:
            path.unlink()
            return True
        return False
