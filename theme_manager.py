import json
import os
from utils import get_base_dir

# ==================== 主题管理系统 ====================
class ThemeManager:
    """管理应用程序主题"""

    # 预定义主题
    THEMES = {
        "light_blue": {
            "name": "浅蓝主题",
            "description": "浅色主题，适合明亮环境",
            "colors": {
                "bg_primary": "#f8f9fa",
                "bg_secondary": "#e9ecef",
                "bg_tertiary": "#dee2e6",
                "text_primary": "#212529",
                "text_secondary": "#6c757d",
                "accent_primary": "#007bff",
                "accent_hover": "#0056b3",
                "accent_pressed": "#0056b3",
                "danger": "#dc3545",
                "danger_hover": "#c82333",
                "success": "#28a745",
                "success_hover": "#1e7e34",
                "secondary": "#6c757d",
                "secondary_hover": "#545b62"
            }
        },
        "dark_green": {
            "name": "深绿主题",
            "description": "深绿配色，给人清新自然的感觉",
            "colors": {
                "bg_primary": "#1a2520",
                "bg_secondary": "#2c3e2f",
                "bg_tertiary": "#344935",
                "text_primary": "#ecf0f1",
                "text_secondary": "#bdc3c7",
                "accent_primary": "#27ae60",
                "accent_hover": "#229954",
                "accent_pressed": "#229954",
                "danger": "#e74c3c",
                "danger_hover": "#c0392b",
                "success": "#0c311c",
                "success_hover": "#042914",
                "secondary": "#95a5a6",
                "secondary_hover": "#7f8c8d"
            }
        },
        "dark_purple": {
            "name": "深紫主题",
            "description": "深紫配色，神秘而优雅",
            "colors": {
                "bg_primary": "#1a1a2a",
                "bg_secondary": "#2c2c3e",
                "bg_tertiary": "#343449",
                "text_primary": "#ecf0f1",
                "text_secondary": "#bdc3c7",
                "accent_primary": "#9b59b6",
                "accent_hover": "#8e44ad",
                "accent_pressed": "#8e44ad",
                "danger": "#e74c3c",
                "danger_hover": "#c0392b",
                "success": "#0c311c",
                "success_hover": "#042914",
                "secondary": "#95a5a6",
                "secondary_hover": "#7f8c8d"
            }
        },
        "dark_blue": {
            "name": "深蓝主题",
            "description": "深蓝配色，适合长时间使用",
            "colors": {
                "bg_primary": "#1a2a3a",
                "bg_secondary": "#2c3e50",
                "bg_tertiary": "#34495e",
                "text_primary": "#ecf0f1",
                "text_secondary": "#bdc3c7",
                "accent_primary": "#3498db",
                "accent_hover": "#2980b9",
                "accent_pressed": "#2980b9",
                "danger": "#e74c3c",
                "danger_hover": "#c0392b",
                "success": "#0c311c",
                "success_hover": "#042914",
                "secondary": "#95a5a6",
                "secondary_hover": "#7f8c8d"
            }
        },
        "dark_red": {
            "name": "深红主题",
            "description": "深红配色，醒目而有冲击力",
            "colors": {
                "bg_primary": "#2a1a1a",
                "bg_secondary": "#3e2c2c",
                "bg_tertiary": "#493434",
                "text_primary": "#ecf0f1",
                "text_secondary": "#bdc3c7",
                "accent_primary": "#e74c3c",
                "accent_hover": "#c0392b",
                "accent_pressed": "#c0392b",
                "danger": "#e74c3c",
                "danger_hover": "#c0392b",
                "success": "#0c311c",
                "success_hover": "#042914",
                "secondary": "#95a5a6",
                "secondary_hover": "#7f8c8d"
            }
        },
        "cyberpunk": {
            "name": "赛博朋克主题",
            "description": "霓虹灯风格，未来感十足",
            "colors": {
                "bg_primary": "#0a0a0a",
                "bg_secondary": "#1a1a1a",
                "bg_tertiary": "#2a2a2a",
                "text_primary": "#00ff41",
                "text_secondary": "#00cc33",
                "accent_primary": "#ff0080",
                "accent_hover": "#cc0066",
                "accent_pressed": "#cc0066",
                "danger": "#ff4444",
                "danger_hover": "#cc3333",
                "success": "#00ff41",
                "success_hover": "#00cc33",
                "secondary": "#666666",
                "secondary_hover": "#555555"
            }
        }
    }

    def __init__(self):
        self.current_theme = "light_blue"
        self.custom_themes = {}  # 自定义主题存储
        self._migrate_to_configs_dir()
        self.load_custom_themes()
        self.load_theme()
        if self.current_theme not in self.THEMES and self.current_theme not in self.custom_themes:
            self.current_theme = "light_blue"

    def _migrate_to_configs_dir(self):
        """将旧位置的 JSON 文件迁移到 configs 目录"""
        configs_dir = os.path.join(get_base_dir(), "configs")
        os.makedirs(configs_dir, exist_ok=True)
        for filename in ["custom_themes.json", "theme_config.json"]:
            old_path = os.path.join(get_base_dir(), filename)
            new_path = os.path.join(configs_dir, filename)
            if os.path.exists(old_path) and not os.path.exists(new_path):
                try:
                    import shutil
                    shutil.copy2(old_path, new_path)
                except:
                    pass

    def load_theme(self):
        """从配置文件加载主题"""
        config_file = os.path.join(get_base_dir(), "configs", "theme_config.json")
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.current_theme = config.get("current_theme", "light_blue")
        except:
            self.current_theme = "light_blue"

    def load_custom_themes(self):
        """加载自定义主题"""
        custom_file = os.path.join(get_base_dir(), "configs", "custom_themes.json")
        try:
            if os.path.exists(custom_file):
                with open(custom_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.custom_themes = data if isinstance(data, dict) else {}
        except:
            self.custom_themes = {}

    def save_theme(self):
        """保存主题配置"""
        config_file = os.path.join(get_base_dir(), "configs", "theme_config.json")
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump({"current_theme": self.current_theme}, f, indent=2)
        except:
            pass

    def save_custom_themes(self):
        """保存自定义主题"""
        custom_file = os.path.join(get_base_dir(), "configs", "custom_themes.json")
        try:
            with open(custom_file, 'w', encoding='utf-8') as f:
                json.dump(self.custom_themes, f, indent=2, ensure_ascii=False)
        except:
            pass

    def create_custom_theme(self, name, description, colors):
        """创建自定义主题"""
        idx = 0
        while True:
            theme_key = f"custom_{idx}"
            if theme_key not in self.custom_themes:
                break
            idx += 1
        self.custom_themes[theme_key] = {
            "name": name,
            "description": description,
            "colors": colors,
            "custom": True
        }
        self.save_custom_themes()
        return theme_key

    def update_custom_theme(self, theme_key, name, description, colors):
        """更新自定义主题"""
        if theme_key in self.custom_themes:
            self.custom_themes[theme_key] = {
                "name": name,
                "description": description,
                "colors": colors,
                "custom": True
            }
            self.save_custom_themes()
            return True
        return False

    def delete_custom_theme(self, theme_key):
        """删除自定义主题"""
        if theme_key in self.custom_themes:
            del self.custom_themes[theme_key]
            self.save_custom_themes()
            # 如果删除的是当前主题，切换到默认主题
            if self.current_theme == theme_key:
                self.set_theme("dark_blue")
            return True
        return False

    def set_theme(self, theme_name):
        """设置当前主题"""
        if theme_name in self.THEMES or theme_name in self.custom_themes:
            self.current_theme = theme_name
            self.save_theme()
            return True
        return False

    def get_current_theme(self):
        """获取当前主题"""
        if self.current_theme in self.THEMES:
            return self.THEMES[self.current_theme]
        elif self.current_theme in self.custom_themes:
            return self.custom_themes[self.current_theme]
        else:
            return self.THEMES["dark_blue"]

    def get_theme_names(self):
        """获取所有主题名称"""
        return list(self.THEMES.keys()) + list(self.custom_themes.keys())

    def get_theme_info(self, theme_name):
        """获取主题信息"""
        if theme_name in self.THEMES:
            return self.THEMES[theme_name]
        elif theme_name in self.custom_themes:
            return self.custom_themes[theme_name]
        return {}

    def is_custom_theme(self, theme_name):
        """检查是否为自定义主题"""
        return theme_name in self.custom_themes

    def get_default_colors(self):
        """获取默认颜色模板"""
        return {
            "bg_primary": "#1a2a3a",
            "bg_secondary": "#2c3e50",
            "bg_tertiary": "#34495e",
            "text_primary": "#ecf0f1",
            "text_secondary": "#bdc3c7",
            "accent_primary": "#3498db",
            "accent_hover": "#2980b9",
            "accent_pressed": "#2980b9",
            "danger": "#e74c3c",
            "danger_hover": "#c0392b",
            "success": "#0c311c",
            "success_hover": "#042914",
            "secondary": "#95a5a6",
            "secondary_hover": "#7f8c8d"
        }

    def _hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _rgb_to_hex(self, rgb):
        return '#{:02x}{:02x}{:02x}'.format(*[max(0, min(255, int(v))) for v in rgb])

    def _blend_colors(self, color_a, color_b, ratio=0.5):
        a = self._hex_to_rgb(color_a)
        b = self._hex_to_rgb(color_b)
        return self._rgb_to_hex(tuple(a[i] * (1 - ratio) + b[i] * ratio for i in range(3)))

    def _adjust_brightness(self, hex_color, factor):
        rgb = self._hex_to_rgb(hex_color)
        adjusted = tuple(max(0, min(255, int(c * factor))) for c in rgb)
        return self._rgb_to_hex(adjusted)

    def _is_light_color(self, hex_color):
        r, g, b = self._hex_to_rgb(hex_color)
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return luminance > 0.65

    def generate_palette_from_primary(self, accent_primary, bg_primary=None):
        """根据主强调色自动判断深浅，全自动生成一套完整配色。

        - 主色偏浅 → 生成浅色主题（浅背景、深文字）；
        - 主色偏深 → 生成深色主题（深背景、浅文字）；
        - 背景色始终随主色色调变化，不再固定为深色。
        """
        try:
            accent_primary = accent_primary.strip()
            if not accent_primary.startswith('#') or len(accent_primary) != 7:
                raise ValueError("无效的主色调")

            accent_is_light = self._is_light_color(accent_primary)

            if bg_primary is None or not bg_primary.startswith('#') or len(bg_primary) != 7:
                if accent_is_light:
                    # 浅色主色 → 浅色背景（主色混入白色，保留色调）
                    bg_primary = self._blend_colors(accent_primary, '#ffffff', 0.85)
                else:
                    # 深色主色 → 深色背景（主色混入深蓝黑，保留色调）
                    bg_primary = self._blend_colors(accent_primary, '#0b1220', 0.78)
            else:
                bg_primary = bg_primary.strip()

            bg_is_light = self._is_light_color(bg_primary)

            # 文字色自动与背景形成对比
            text_primary = '#212529' if bg_is_light else '#ecf0f1'
            text_secondary = '#6c757d' if bg_is_light else '#bdc3c7'

            # 辅助背景色：与背景同亮暗、微带主色色调
            if bg_is_light:
                bg_secondary = self._blend_colors(bg_primary, accent_primary, 0.13)
                bg_tertiary = self._blend_colors(bg_primary, accent_primary, 0.08)
            else:
                bg_secondary = self._blend_colors(bg_primary, accent_primary, 0.22)
                bg_tertiary = self._blend_colors(bg_primary, accent_primary, 0.14)

            secondary = self._blend_colors(text_primary, bg_primary, 0.64)
            secondary_hover = self._adjust_brightness(secondary, 0.88)

            if accent_is_light:
                accent_hover = self._adjust_brightness(accent_primary, 0.86)
                accent_pressed = self._adjust_brightness(accent_primary, 0.74)
                # 浅色主色 → 更深一档，用作文字/数字，保证浅背景上可读
                accent_text = self._adjust_brightness(accent_primary, 0.62)
            else:
                accent_hover = self._adjust_brightness(accent_primary, 1.25)
                accent_pressed = self._adjust_brightness(accent_primary, 0.78)
                # 深色主色 → 更亮一档，用作文字/数字，保证深背景上醒目
                accent_text = self._adjust_brightness(accent_primary, 1.30)

            # 成功/危险色根据主题深浅调整，保证可读
            if bg_is_light:
                success = self._blend_colors(accent_primary, '#1e7e34', 0.30)
                success_hover = self._adjust_brightness('#1e7e34', 0.95)
            else:
                success = self._blend_colors(accent_primary, '#27ae60', 0.35)
                success_hover = self._adjust_brightness('#27ae60', 0.9)
            danger = self._blend_colors(accent_primary, '#e74c3c', 0.40)
            danger_hover = self._adjust_brightness('#e74c3c', 0.85)

            return {
                "bg_primary": bg_primary,
                "bg_secondary": bg_secondary,
                "bg_tertiary": bg_tertiary,
                "text_primary": text_primary,
                "text_secondary": text_secondary,
                "accent_primary": accent_primary,
                "accent_hover": accent_hover,
                "accent_pressed": accent_pressed,
                "accent_text": accent_text,
                "danger": danger,
                "danger_hover": danger_hover,
                "success": success,
                "success_hover": success_hover,
                "secondary": secondary,
                "secondary_hover": secondary_hover
            }

        except Exception:
            return self.get_default_colors()

    def generate_stylesheet(self, theme_name=None):
        """生成QSS样式表 - 侧边栏导航风格"""
        if theme_name is None:
            theme_name = self.current_theme

        theme = self.get_theme_info(theme_name)
        if not theme or "colors" not in theme:
            theme = self.THEMES["dark_blue"]
        c = dict(theme["colors"])
        # 兼容没有 accent_text 字段的旧主题/预设主题
        c.setdefault("accent_text", c.get("accent_primary", "#3498db"))

        # 计算一些派生色
        sidebar_bg = self._adjust_brightness(c['bg_primary'], 0.82) if not self._is_light_color(c['bg_primary']) else self._adjust_brightness(c['bg_primary'], 0.94)
        card_bg = self._blend_colors(c['bg_primary'], c['bg_secondary'], 0.3) if self._is_light_color(c['bg_primary']) else self._blend_colors(c['bg_primary'], c['bg_secondary'], 0.5)
        stat_card_bg = c['bg_secondary']
        input_bg = self._blend_colors(c['bg_secondary'], c['bg_primary'], 0.3) if self._is_light_color(c['bg_primary']) else self._blend_colors(c['bg_secondary'], c['bg_primary'], 0.5)
        # 侧边栏渐变色（随背景深浅自适应）
        if self._is_light_color(c['bg_primary']):
            sb_stop0 = self._adjust_brightness(c['bg_primary'], 0.99)
            sb_stop1 = self._adjust_brightness(c['bg_primary'], 0.90)
        else:
            sb_stop0 = self._adjust_brightness(c['bg_primary'], 0.80)
            sb_stop1 = self._adjust_brightness(c['bg_primary'], 0.94)

        # 磨砂玻璃色 (rgba)
        r, g, b = self._hex_to_rgb(sidebar_bg)
        sidebar_glass = f"rgba({r},{g},{b},220)"
        cr, cg, cb = self._hex_to_rgb(card_bg)
        card_glass = f"rgba({cr},{cg},{cb},180)"
        sr, sg, sb = self._hex_to_rgb(stat_card_bg)
        stat_glass = f"rgba({sr},{sg},{sb},180)"

        # 渐变派生色（用于卡片与按钮的立体感）
        card_light = self._adjust_brightness(card_bg, 1.10)
        card_dark = self._adjust_brightness(card_bg, 0.90)
        stat_light = self._adjust_brightness(stat_card_bg, 1.12)
        stat_dark = self._adjust_brightness(stat_card_bg, 0.90)
        accent_light = self._adjust_brightness(c['accent_primary'], 1.15)
        accent_dark = self._adjust_brightness(c['accent_primary'], 0.82)
        btn_light = self._adjust_brightness(c['accent_primary'], 1.10)
        btn_dark = self._adjust_brightness(c['accent_primary'], 0.85)

        return f"""
            /* ========== 全局 ========== */
            QWidget {{
                background-color: {c['bg_primary']};
                color: {c['text_primary']};
                font-family: "Microsoft YaHei", "微软雅黑", "Segoe UI", "PingFang SC", "Noto Sans SC", sans-serif;
                font-size: 13px;
            }}

            /* ========== 侧边栏 ========== */
            QFrame#sidebar {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 {sb_stop0},
                                            stop:1 {sb_stop1});
                border-right: 1px solid rgba({self._hex_to_rgb(c['bg_tertiary'])[0]},{self._hex_to_rgb(c['bg_tertiary'])[1]},{self._hex_to_rgb(c['bg_tertiary'])[2]},120);
            }}
            QFrame#sidebar_indicator {{
                background-color: {c['accent_primary']};
                border-radius: 1px;
            }}
            QFrame#logo_area {{
                background: transparent;
            }}
            QLabel#logo_title {{
                font-size: 24px;
                font-weight: bold;
                color: {c['accent_text']};
                background: transparent;
            }}
            QLabel#logo_sub {{
                font-size: 11px;
                color: {c['text_secondary']};
                background: transparent;
            }}
            QFrame#sidebar_sep {{
                border: none;
                background-color: rgba({self._hex_to_rgb(c['bg_tertiary'])[0]},{self._hex_to_rgb(c['bg_tertiary'])[1]},{self._hex_to_rgb(c['bg_tertiary'])[2]},80);
                max-height: 1px;
            }}
            QFrame#bottom_info {{
                background: transparent;
            }}
            QLabel#config_label {{
                font-size: 11px;
                color: {c['text_secondary']};
                background: transparent;
            }}

            /* 侧边栏按钮 */
            QPushButton#sidebar_btn {{
                background-color: transparent;
                color: {c['text_secondary']};
                border: none;
                border-radius: 8px;
                padding: 10px 16px 10px 16px;
                font-size: 13px;
                text-align: left;
                font-weight: normal;
            }}
            QPushButton#sidebar_btn:hover {{
                background-color: rgba({self._hex_to_rgb(c['accent_primary'])[0]},{self._hex_to_rgb(c['accent_primary'])[1]},{self._hex_to_rgb(c['accent_primary'])[2]},30);
                color: {c['text_primary']};
            }}
            QPushButton#sidebar_btn:checked {{
                background-color: rgba({self._hex_to_rgb(c['accent_primary'])[0]},{self._hex_to_rgb(c['accent_primary'])[1]},{self._hex_to_rgb(c['accent_primary'])[2]},50);
                color: {c['accent_text']};
                font-weight: bold;
            }}

            /* ========== 内容区域 ========== */
            QFrame#content_area {{
                background-color: {c['bg_primary']};
            }}

            /* ========== 页面标题 ========== */
            QLabel#page_title {{
                font-size: 22px;
                font-weight: bold;
                color: {c['text_primary']};
                padding-bottom: 5px;
            }}

            /* ========== 卡片 ========== */
            QFrame#card {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 {card_light},
                                            stop:1 {card_dark});
                border: 1px solid rgba({self._hex_to_rgb(c['bg_tertiary'])[0]},{self._hex_to_rgb(c['bg_tertiary'])[1]},{self._hex_to_rgb(c['bg_tertiary'])[2]},100);
                border-top: 3px solid {c['accent_primary']};
                border-radius: 14px;
            }}
            QLabel#card_title {{
                font-size: 16px;
                font-weight: bold;
                color: {c['text_primary']};
            }}
            QLabel#field_label {{
                font-size: 12px;
                font-weight: bold;
                color: {c['text_secondary']};
            }}
            QLabel#hint_label {{
                font-size: 11px;
                color: {c['text_secondary']};
            }}

            /* ========== 统计卡片 ========== */
            QFrame#stat_card {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 {stat_light},
                                            stop:1 {stat_dark});
                border: 1px solid rgba({self._hex_to_rgb(c['bg_tertiary'])[0]},{self._hex_to_rgb(c['bg_tertiary'])[1]},{self._hex_to_rgb(c['bg_tertiary'])[2]},100);
                border-radius: 12px;
            }}
            QLabel#stat_label {{
                font-size: 12px;
                color: {c['text_secondary']};
                background: transparent;
            }}
            QLabel#stat_number {{
                font-size: 30px;
                font-weight: bold;
                color: {c['accent_text']};
                background: transparent;
            }}

            /* ========== 迷你统计卡（主页仪表盘） ========== */
            QFrame#mini_stat {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 {stat_light},
                                            stop:1 {stat_dark});
                border: 1px solid rgba({self._hex_to_rgb(c['bg_tertiary'])[0]},{self._hex_to_rgb(c['bg_tertiary'])[1]},{self._hex_to_rgb(c['bg_tertiary'])[2]},80);
                border-radius: 12px;
                border-left: 3px solid {c['accent_primary']};
            }}
            QLabel#mini_stat_number {{
                font-size: 22px;
                font-weight: bold;
                color: {c['accent_text']};
                background: transparent;
            }}
            QLabel#mini_stat_label {{
                font-size: 10px;
                color: {c['text_secondary']};
                background: transparent;
            }}

            /* ========== 版本号 ========== */
            QLabel#version_label {{
                font-size: 10px;
                color: rgba({self._hex_to_rgb(c['text_secondary'])[0]},{self._hex_to_rgb(c['text_secondary'])[1]},{self._hex_to_rgb(c['text_secondary'])[2]},150);
                background: transparent;
            }}

            /* ========== 分隔线 ========== */
            QFrame#divider {{
                border: none;
                background-color: {c['bg_tertiary']};
                max-height: 1px;
            }}

            /* ========== 按钮 ========== */
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 {btn_light},
                                            stop:1 {btn_dark});
                color: {c['text_primary']};
                border: 1px solid rgba(255,255,255,18);
                padding: 8px 12px;
                font-weight: bold;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 {self._adjust_brightness(c['accent_primary'], 1.22)},
                                            stop:1 {self._adjust_brightness(c['accent_primary'], 0.95)});
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 {accent_dark},
                                            stop:1 {accent_light});
            }}
            /* 开始监控按钮 */
            QPushButton#start_btn {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 {accent_light},
                                            stop:1 {accent_dark});
                color: {c['text_primary']};
                font-size: 16px;
                font-weight: bold;
                border-radius: 10px;
                padding: 12px 30px;
                border: 1px solid rgba(255,255,255,22);
            }}
            QPushButton#start_btn:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 {self._adjust_brightness(c['accent_primary'], 1.28)},
                                            stop:1 {self._adjust_brightness(c['accent_primary'], 0.95)});
            }}
            /* 状态按钮：成功（绿）、危险（红）、次要（灰） */
            QPushButton#success {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 {self._adjust_brightness(c['success'], 1.25)},
                                            stop:1 {self._adjust_brightness(c['success'], 0.85)});
                color: {c['text_primary']};
            }}
            QPushButton#success:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 {self._adjust_brightness(c['success'], 1.45)},
                                            stop:1 {self._adjust_brightness(c['success'], 0.95)});
            }}
            QPushButton#danger {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 {self._adjust_brightness(c['danger'], 1.20)},
                                            stop:1 {self._adjust_brightness(c['danger'], 0.82)});
                color: #ffffff;
            }}
            QPushButton#danger:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 {self._adjust_brightness(c['danger'], 1.40)},
                                            stop:1 {self._adjust_brightness(c['danger'], 0.95)});
            }}
            QPushButton#secondary {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 {self._adjust_brightness(c['secondary'], 1.15)},
                                            stop:1 {self._adjust_brightness(c['secondary'], 0.82)});
                color: {c['text_primary']};
            }}
            QPushButton#secondary:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 {self._adjust_brightness(c['secondary'], 1.30)},
                                            stop:1 {self._adjust_brightness(c['secondary'], 0.90)});
            }}

            /* ========== 输入控件 ========== */
            QLineEdit {{
                background-color: {input_bg};
                color: {c['text_primary']};
                border: 1px solid {c['bg_tertiary']};
                padding: 6px 10px;
                border-radius: 8px;
                font-family: "Microsoft YaHei", "微软雅黑", "Segoe UI", "PingFang SC", "Noto Sans SC", sans-serif;
                font-size: 13px;
                selection-background-color: {c['accent_primary']};
            }}
            QLineEdit:focus {{
                border: 1px solid {c['accent_primary']};
            }}
            QLineEdit:disabled {{
                color: {c['text_secondary']};
            }}
            QTextEdit {{
                background-color: {input_bg};
                color: {c['text_primary']};
                border: 1px solid {c['bg_tertiary']};
                border-radius: 8px;
                font-family: "Microsoft YaHei", "微软雅黑", "Segoe UI", "PingFang SC", "Noto Sans SC", sans-serif;
                font-size: 13px;
                selection-background-color: {c['accent_primary']};
            }}
            QTextEdit:focus {{
                border: 1px solid {c['accent_primary']};
            }}

            /* ========== 下拉框 ========== */
            QComboBox {{
                background-color: {c['bg_secondary']};
                color: {c['text_primary']};
                border: 1px solid {c['bg_tertiary']};
                padding: 6px 10px;
                border-radius: 8px;
                font-family: "Microsoft YaHei", "微软雅黑", "Segoe UI", "PingFang SC", "Noto Sans SC", sans-serif;
                font-size: 13px;
            }}
            QComboBox:hover {{
                border: 1px solid {c['accent_primary']};
            }}
            QComboBox::drop-down {{
                border: none;
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 24px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {c['text_secondary']};
            }}
            QComboBox QAbstractItemView {{
                background-color: {c['bg_secondary']};
                color: {c['text_primary']};
                selection-background-color: {c['accent_primary']};
                border-radius: 6px;
                font-size: 13px;
                padding: 4px;
            }}
            QComboBox QLineEdit {{
                background-color: transparent;
                border: none;
                padding: 0;
                font-size: 13px;
                color: {c['text_primary']};
                selection-background-color: {c['accent_primary']};
            }}

            /* ========== 树控件 ========== */
            QTreeWidget {{
                background-color: {c['bg_secondary']};
                color: {c['text_primary']};
                border: 1px solid {c['bg_tertiary']};
                border-radius: 8px;
                alternate-background-color: {c['bg_tertiary']};
            }}
            QTreeWidget::item {{
                padding: 6px;
            }}
            QTreeWidget::item:selected {{
                background-color: {c['accent_primary']};
            }}

            /* ========== 标签页 ========== */
            QTabWidget::pane {{
                border: 1px solid {c['bg_tertiary']};
                background-color: {c['bg_primary']};
                border-radius: 0 0 8px 8px;
            }}
            QTabBar::tab {{
                background-color: {c['bg_secondary']};
                color: {c['text_secondary']};
                padding: 10px 20px;
                border: 1px solid {c['bg_tertiary']};
                border-bottom: none;
                margin-right: 2px;
                border-radius: 8px 8px 0 0;
            }}
            QTabBar::tab:selected {{
                background-color: {c['accent_primary']};
                color: {c['text_primary']};
            }}
            QTabBar::tab:hover {{
                background-color: {c['accent_hover']};
            }}

            /* ========== GroupBox (兼容旧对话框) ========== */
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {c['bg_tertiary']};
                border-radius: 10px;
                margin-top: 1ex;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px 0 8px;
                color: {c['accent_text']};
            }}

            /* ========== 滚动条 ========== */
            QScrollBar:vertical {{
                background: {c['bg_primary']};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {c['bg_tertiary']};
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {c['secondary']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QScrollBar:horizontal {{
                background: {c['bg_primary']};
                height: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:horizontal {{
                background: {c['bg_tertiary']};
                border-radius: 4px;
                min-width: 30px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {c['secondary']};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0;
            }}

            /* ========== 列表控件 ========== */
            QListWidget {{
                background-color: {c['bg_secondary']};
                color: {c['text_primary']};
                border: 1px solid {c['bg_tertiary']};
                border-radius: 8px;
            }}
            QListWidget::item {{
                padding: 6px;
            }}
            QListWidget::item:selected {{
                background-color: {c['accent_primary']};
            }}
        """
