import os
import sys
import random
import re
import time
import pathlib as pl
import pygetwindow
import keyboard
import ctypes
import ctypes.wintypes
from collections import deque
import threading
import json
from datetime import datetime
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtCore as QtCore
import PyQt5.QtGui as QtGui
from theme_manager import ThemeManager
from config_manager import ConfigManager
from share_code import generate_share_code, parse_share_code, import_config_from_share_code, export_config_to_share_code
from utils import get_base_dir
from flip_number import FlipNumber

# ==================== 动画辅助类 ====================
class NumberAnimation:
    """数字滚动动画效果"""
    
    def __init__(self, widget, duration=300, steps=30):
        self.widget = widget
        self.duration = duration
        self.steps = steps
        self.current_value = 0
        self.target_value = 0
        self.step_value = 0
        self.current_step = 0
        self.timer = None
    
    def update_value(self, new_value, prefix="", suffix=""):
        """更新数字，带动画效果"""
        if self.timer:
            self.timer.stop()
        
        self.prefix = prefix
        self.suffix = suffix
        self.start_value = self.current_value
        self.target_value = new_value
        self.current_step = 0
        self._animate_step()
    
    def _animate_step(self):
        """执行动画的下一步"""
        if self.current_step >= self.steps:
            self.current_value = self.target_value
            self._update_display()
            return
        
        progress = self.current_step / self.steps
        # 缓动函数 easeOutQuad
        ease_progress = 1 - (1 - progress) ** 2
        self.current_value = self.start_value + (self.target_value - self.start_value) * ease_progress
        self._update_display()
        
        self.current_step += 1
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self._animate_step)
        self.timer.setSingleShot(True)
        self.timer.start(int(self.duration / self.steps))
    
    def _update_display(self):
        """更新显示文本"""
        self.widget.setText(f"{self.prefix}{int(self.current_value)}{self.suffix}")

# ==================== 按键录制对话框 ====================
class KeyCaptureDialog(QtWidgets.QDialog):
    """按键录制对话框：弹出后等待用户按下一个键，返回 keyboard 库格式的键名。"""

    @staticmethod
    def key_to_name(event):
        """把 Qt 按键事件转换为 keyboard 库可用的键名，无法识别返回 None。"""
        key = event.key()
        text = event.text()

        # 字母键 A-Z
        if QtCore.Qt.Key_A <= key <= QtCore.Qt.Key_Z:
            return chr(ord('a') + (key - QtCore.Qt.Key_A))
        # 数字键 0-9
        if QtCore.Qt.Key_0 <= key <= QtCore.Qt.Key_9:
            return str(key - QtCore.Qt.Key_0)
        # 功能键 F1-F12
        if QtCore.Qt.Key_F1 <= key <= QtCore.Qt.Key_F12:
            return "f{}".format(key - QtCore.Qt.Key_F1 + 1)
        # 特殊键
        special = {
            QtCore.Qt.Key_Return: 'enter',
            QtCore.Qt.Key_Enter: 'enter',
            QtCore.Qt.Key_Space: 'space',
            QtCore.Qt.Key_Tab: 'tab',
            QtCore.Qt.Key_Escape: 'esc',
            QtCore.Qt.Key_Backspace: 'backspace',
            QtCore.Qt.Key_Delete: 'delete',
            QtCore.Qt.Key_Up: 'up',
            QtCore.Qt.Key_Down: 'down',
            QtCore.Qt.Key_Left: 'left',
            QtCore.Qt.Key_Right: 'right',
            QtCore.Qt.Key_Shift: 'shift',
            QtCore.Qt.Key_Control: 'ctrl',
            QtCore.Qt.Key_Alt: 'alt',
            QtCore.Qt.Key_Home: 'home',
            QtCore.Qt.Key_End: 'end',
            QtCore.Qt.Key_PageUp: 'page up',
            QtCore.Qt.Key_PageDown: 'page down',
        }
        if key in special:
            return special[key]
        # 其他可打印单字符（含符号）
        if text and text.strip() and len(text) == 1:
            return text.lower()
        return None

    def __init__(self, parent=None, title="设置按键"):
        super().__init__(parent)
        self.captured_key = None
        self.setWindowTitle(title)
        self.setFixedSize(320, 160)
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 26, 24, 20)
        layout.setSpacing(10)

        label = QtWidgets.QLabel("请按下要绑定的按键")
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(label)

        hint = QtWidgets.QLabel("按 Esc 取消")
        hint.setAlignment(QtCore.Qt.AlignCenter)
        hint.setStyleSheet("font-size: 12px; color: #888888;")
        layout.addWidget(hint)

    def keyPressEvent(self, event):
        name = self.key_to_name(event)
        if name is None:
            return
        if name == 'esc':
            self.captured_key = None
        else:
            self.captured_key = name
        self.accept()

# ==================== 主应用程序 ====================
class KillSayApp(QtWidgets.QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("KillSay")
        self.setGeometry(100, 100, 1100, 700)
        self.setFixedSize(1100, 700)
        
        # 配置管理器（使用程序目录下的 configs 文件夹）
        self.config_mgr = ConfigManager(config_dir=os.path.join(get_base_dir(), "configs"))
        
        # 主题管理器
        self.theme_mgr = ThemeManager()
        
        # 运行时变量
        self.user = ""
        self.window_name = ""
        self.log_file_path = ""
        self.kills = 0
        self.deaths = 0
        self.wins = 0
        self.losses = 0
        self.win_streak = 0
        self.is_monitoring = False
        self.monitoring_thread = None
        self.anti_snipe_enabled = False
        self.killsay_enabled = True
        self.stats_enabled = True
        self.autotext_enabled = True      # AutoText 开关
        self.autogg_enabled = True        # AutoGG 开关
        self.index_q = deque(maxlen=5)
        self.autotext = []                # 快捷消息列表 [{"message": str, "key": str}]
        self._autotext_handlers = []      # 已注册的热键 [(hotkey_id, message)]
        
        # 历史记录（存储在 configs 目录中）
        self._migrate_history_to_configs_dir()
        self.history_file = pl.Path(os.path.join(get_base_dir(), "configs", "history.json"))
        self.history = self._load_history()
        
        # 从配置加载数据
        self._load_from_config()
        
        # 动画对象
        self.pulse_effect = None
        self._flip_widgets = []      # 主窗口翻页数字控件
        self._float_flips = []       # 悬浮统计窗口翻页数字控件
        
        # 设置样式
        self._setup_styles()

        # 构建界面
        self._build_ui()

        # 构建完成后刷新一次战绩显示（无动画填充初始值）
        self._update_stats_display(animate=False)
    
    def _migrate_history_to_configs_dir(self):
        """将旧位置的 history.json 迁移到 configs 目录"""
        old_path = pl.Path(get_base_dir()) / "history.json"
        new_path = pl.Path(os.path.join(get_base_dir(), "configs", "history.json"))
        if old_path.exists() and not new_path.exists():
            try:
                import shutil
                shutil.copy2(str(old_path), str(new_path))
            except:
                pass

    def _load_history(self):
        """加载历史记录"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"players": [], "paths": []}
    
    def _save_history(self):
        """保存历史记录"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def _add_to_history(self, key, value):
        """添加到历史记录"""
        if value and value not in self.history[key]:
            self.history[key].insert(0, value)
            self.history[key] = self.history[key][:10]  # 最多保存10个
            self._save_history()
    
    def _load_from_config(self):
        """从当前配置加载数据"""
        config = self.config_mgr.current_config
        self.sniper_list = config.get("sniper_list", ConfigManager.DEFAULT_CONFIG["sniper_list"])
        self.join_patterns = config.get("join_patterns", ConfigManager.DEFAULT_CONFIG["join_patterns"])
        self.anti_snipe_messages = config.get("anti_snipe_messages", ConfigManager.DEFAULT_CONFIG["anti_snipe_messages"])
        self.kill_patterns = config.get("kill_patterns", ConfigManager.DEFAULT_CONFIG["kill_patterns"])
        self.kill_messages = config.get("kill_messages", ConfigManager.DEFAULT_CONFIG["kill_messages"])
        self.message_prefix = config.get("message_prefix", ConfigManager.DEFAULT_CONFIG["message_prefix"])
        self.killsay_format = config.get("killsay_format", ConfigManager.DEFAULT_CONFIG["killsay_format"])
        self.chat_key = config.get("chat_key", ConfigManager.DEFAULT_CONFIG["chat_key"])
        self.win_patterns = config.get("win_patterns", ConfigManager.DEFAULT_CONFIG["win_patterns"])
        self.autotext = config.get("autotext", ConfigManager.DEFAULT_CONFIG["autotext"])
        if not isinstance(self.autotext, list):
            self.autotext = []

        # 如果配置中有保存的战绩数据，提示用户
        saved_stats = config.get("saved_stats")
        if saved_stats:
            reply = QtWidgets.QMessageBox.question(
                self, "加载战绩数据",
                f"检测到保存的战绩数据（保存于 {saved_stats.get('saved_at', '未知时间')}）：\n"
                f"击杀: {saved_stats.get('kills', 0)}  死亡: {saved_stats.get('deaths', 0)}\n"
                f"胜利: {saved_stats.get('wins', 0)}  失败: {saved_stats.get('losses', 0)}\n"
                f"连胜: {saved_stats.get('win_streak', 0)}\n\n"
                f"是否加载这些数据？",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            if reply == QtWidgets.QMessageBox.Yes:
                self.kills = saved_stats.get("kills", 0)
                self.deaths = saved_stats.get("deaths", 0)
                self.wins = saved_stats.get("wins", 0)
                self.losses = saved_stats.get("losses", 0)
                self.win_streak = saved_stats.get("win_streak", 0)
                # 战绩数值已在 __init__ 末尾统一刷新显示

        # 配置加载/切换后刷新快捷消息列表（UI 未建立时自动跳过）
        self._refresh_autotext_list()
    
    def _setup_styles(self):
        """设置现代化样式"""
        stylesheet = self.theme_mgr.generate_stylesheet()
        self.setStyleSheet(stylesheet)
        if hasattr(self, 'stats_window') and self.stats_window.isVisible():
            self.stats_window.setStyleSheet(stylesheet)
        self._apply_flip_colors()

    def _flip_colors(self):
        """从当前主题取翻页数字的配色。"""
        colors = self.theme_mgr.get_current_theme().get("colors", {})
        return (
            colors.get("accent_text", colors.get("accent_primary", "#3498db")),
            colors.get("bg_secondary", "#2c3e50"),
            colors.get("bg_tertiary", "#34495e"),
            colors.get("bg_primary", "#1a2a3a"),
        )

    def _make_flip(self, decimals, dw, dh, gap=6):
        """创建翻页数字控件并登记，便于主题切换时统一换色。"""
        accent, card, border, hinge = self._flip_colors()
        w = FlipNumber(decimals=decimals, digit_width=dw, digit_height=dh, gap=gap,
                       fg_color=accent, card_bg=card, border_color=border, hinge_color=hinge)
        self._flip_widgets.append(w)
        return w

    def _apply_flip_colors(self):
        """主题变化后刷新所有翻页数字的颜色。"""
        accent, card, border, hinge = self._flip_colors()
        for w in getattr(self, '_flip_widgets', []):
            try:
                w.setColors(fg_color=accent, card_bg=card, border_color=border, hinge_color=hinge)
            except RuntimeError:
                pass
        for w in getattr(self, '_float_flips', []):
            try:
                w.setColors(fg_color=accent, card_bg=card, border_color=border, hinge_color=hinge)
            except RuntimeError:
                pass

    def _make_sidebar_btn(self, text, index):
        """创建侧边栏按钮"""
        btn = QtWidgets.QPushButton(text)
        btn.setObjectName("sidebar_btn")
        btn.setCheckable(True)
        btn.setFixedHeight(44)
        btn.setCursor(QtCore.Qt.PointingHandCursor)
        btn.clicked.connect(lambda: self._switch_page(index))
        btn.installEventFilter(self)
        return btn

    def eventFilter(self, obj, event):
        """按钮悬停动画 - 位置微上移"""
        if isinstance(obj, QtWidgets.QPushButton) and not obj.isCheckable():
            # 非导航按钮不做悬停动画
            return False
        if isinstance(obj, QtWidgets.QPushButton):
            if event.type() == QtCore.QEvent.Enter:
                self._animate_btn_hover(obj, True)
            elif event.type() == QtCore.QEvent.Leave:
                self._animate_btn_hover(obj, False)
        return False

    def _animate_btn_hover(self, btn, hovered):
        """按钮悬停: hovered 时上移 2px，离开时回到原位"""
        if not hasattr(btn, '_orig_pos'):
            btn._orig_pos = btn.pos()
        target = btn._orig_pos + QtCore.QPoint(0, -2) if hovered else btn._orig_pos
        if hasattr(btn, '_hover_anim') and btn._hover_anim.state() == QtCore.QAbstractAnimation.Running:
            btn._hover_anim.stop()
        anim = QtCore.QPropertyAnimation(btn, b"geometry")
        anim.setDuration(150)
        cur = btn.geometry()
        anim.setStartValue(cur)
        anim.setEndValue(QtCore.QRect(target.x(), target.y(), cur.width(), cur.height()))
        anim.setEasingCurve(QtCore.QEasingCurve.InOutCubic)
        anim.start()
        btn._hover_anim = anim

    def _create_sidebar_indicator(self, parent):
        """创建侧边栏选中指示条"""
        self._indicator = QtWidgets.QFrame(parent)
        self._indicator.setObjectName("sidebar_indicator")
        self._indicator.setFixedSize(3, 32)
        self._indicator.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        # X 位置：侧边栏左侧内边距
        self._indicator.move(5, 0)

    def _move_indicator(self, btn):
        """将指示条动画移到目标按钮位置"""
        if not hasattr(self, '_indicator'):
            return
        # 通过全局坐标转换，兼容多层嵌套布局
        parent = self._indicator.parentWidget()
        global_pt = btn.mapToGlobal(QtCore.QPoint(0, 0))
        local_pt = parent.mapFromGlobal(global_pt)
        target_y = local_pt.y() + (btn.height() - 32) // 2

        if hasattr(self, '_indicator_anim') and self._indicator_anim.state() == QtCore.QAbstractAnimation.Running:
            self._indicator_anim.stop()
        anim = QtCore.QPropertyAnimation(self._indicator, b"pos")
        anim.setDuration(250)
        anim.setStartValue(self._indicator.pos())
        anim.setEndValue(QtCore.QPoint(self._indicator.x(), target_y))
        anim.setEasingCurve(QtCore.QEasingCurve.InOutCubic)
        anim.start()
        self._indicator_anim = anim

    def _switch_page(self, index):
        """切换页面 - 弹簧淡入效果"""
        if self.stack.currentIndex() == index:
            return
        if hasattr(self, '_page_anim') and self._page_anim.state() == QtCore.QAbstractAnimation.Running:
            self._page_anim.stop()

        target = self.stack.widget(index)

        # 淡入效果（OutBack 带来轻微回弹）
        effect = QtWidgets.QGraphicsOpacityEffect(target)
        target.setGraphicsEffect(effect)
        anim = QtCore.QPropertyAnimation(effect, b"opacity")
        anim.setDuration(320)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QtCore.QEasingCurve.OutBack)
        self.stack.setCurrentIndex(index)
        anim.start()
        anim.finished.connect(lambda: target.setGraphicsEffect(None))
        self._page_anim = anim

        # 更新侧边栏选中状态和指示条
        for i, btn in enumerate(self.sidebar_btns):
            is_current = (i == index)
            btn.setChecked(is_current)
            if is_current:
                self._move_indicator(btn)

    def _build_ui(self):
        """构建用户界面 - 侧边栏导航风格"""
        root_layout = QtWidgets.QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ========== 侧边栏 ==========
        sidebar = QtWidgets.QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(200)
        sidebar_layout = QtWidgets.QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Logo区域
        logo_frame = QtWidgets.QFrame()
        logo_frame.setObjectName("logo_area")
        logo_frame.setFixedHeight(80)
        logo_layout = QtWidgets.QVBoxLayout(logo_frame)
        logo_layout.setContentsMargins(20, 15, 20, 10)
        logo_title = QtWidgets.QLabel("KillSay")
        logo_title.setObjectName("logo_title")
        logo_layout.addWidget(logo_title)
        logo_sub = QtWidgets.QLabel("V1.2 作者：开了吗如开")
        logo_sub.setObjectName("logo_sub")
        logo_layout.addWidget(logo_sub)
        sidebar_layout.addWidget(logo_frame)

        # 分隔线
        sep1 = QtWidgets.QFrame()
        sep1.setFrameShape(QtWidgets.QFrame.HLine)
        sep1.setObjectName("sidebar_sep")
        sidebar_layout.addWidget(sep1)

        # 导航按钮
        nav_frame = QtWidgets.QFrame()
        nav_layout = QtWidgets.QVBoxLayout(nav_frame)
        nav_layout.setContentsMargins(12, 15, 12, 0)
        nav_layout.setSpacing(4)

        self.sidebar_btns = []
        nav_items = [
            ("  ⌂  主页", 0),
            ("  ⚙  设置", 1),
            ("  ☰  配置", 2),
            ("  ◆  数据", 3),
            ("  ⚡  AutoText", 4),
            ("  ◐  主题", 5),
        ]
        for text, idx in nav_items:
            btn = self._make_sidebar_btn(text, idx)
            nav_layout.addWidget(btn)
            self.sidebar_btns.append(btn)
        self.sidebar_btns[0].setChecked(True)

        nav_layout.addStretch()
        sidebar_layout.addWidget(nav_frame)

        # 指示条放在侧边栏内，与 nav_frame 同级
        self._create_sidebar_indicator(sidebar)
        # 延迟定位：需要等布局完成
        QtCore.QTimer.singleShot(0, lambda: self._move_indicator(self.sidebar_btns[0]))

        # 底部当前配置信息
        sep2 = QtWidgets.QFrame()
        sep2.setFrameShape(QtWidgets.QFrame.HLine)
        sep2.setObjectName("sidebar_sep")
        sidebar_layout.addWidget(sep2)

        bottom_frame = QtWidgets.QFrame()
        bottom_frame.setObjectName("bottom_info")
        bottom_frame.setFixedHeight(60)
        bottom_layout = QtWidgets.QVBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(16, 8, 16, 8)
        self.config_name_label = QtWidgets.QLabel(f"配置: {self.config_mgr.current_config_path.stem}")
        self.config_name_label.setObjectName("config_label")
        bottom_layout.addWidget(self.config_name_label)
        version_label = QtWidgets.QLabel("v1.2 ")
        version_label.setObjectName("version_label")
        bottom_layout.addWidget(version_label)
        sidebar_layout.addWidget(bottom_frame)

        root_layout.addWidget(sidebar)

        # ========== 内容区域 ==========
        content_frame = QtWidgets.QFrame()
        content_frame.setObjectName("content_area")
        content_layout = QtWidgets.QVBoxLayout(content_frame)
        content_layout.setContentsMargins(30, 25, 30, 25)
        content_layout.setSpacing(20)

        self.stack = QtWidgets.QStackedWidget()
        self.stack.setObjectName("stack")

        # --- 页面0: 主页 ---
        page_home = QtWidgets.QWidget()
        home_layout = QtWidgets.QVBoxLayout(page_home)
        home_layout.setSpacing(20)

        # 页面标题
        home_title = QtWidgets.QLabel("主页")
        home_title.setObjectName("page_title")
        home_layout.addWidget(home_title)

        # 迷你统计仪表盘
        dash_row = QtWidgets.QHBoxLayout()
        dash_row.setSpacing(12)

        def make_mini(label_text, decimals=0):
            box = QtWidgets.QFrame()
            box.setObjectName("mini_stat")
            box_layout = QtWidgets.QVBoxLayout(box)
            box_layout.setContentsMargins(14, 10, 14, 10)
            box_layout.setAlignment(QtCore.Qt.AlignCenter)
            lbl = QtWidgets.QLabel(label_text)
            lbl.setObjectName("mini_stat_label")
            lbl.setAlignment(QtCore.Qt.AlignCenter)
            box_layout.addWidget(lbl)
            val = self._make_flip(decimals, 15, 26, gap=3)
            box_layout.addWidget(val, 0, QtCore.Qt.AlignCenter)
            dash_row.addWidget(box)
            return val

        self.dash_kills = make_mini("击杀")
        self.dash_deaths = make_mini("死亡")
        self.dash_kdr = make_mini("K/D", 2)
        self.dash_wins = make_mini("胜利")
        self.dash_wlr = make_mini("W/L", 2)
        self.dash_ws = make_mini("连胜")

        home_layout.addLayout(dash_row)

        # 监控控制卡片
        monitor_card = QtWidgets.QFrame()
        monitor_card.setObjectName("card")
        monitor_layout = QtWidgets.QVBoxLayout(monitor_card)
        monitor_layout.setContentsMargins(30, 30, 30, 30)
        monitor_layout.setSpacing(15)

        monitor_label = QtWidgets.QLabel("监控控制")
        monitor_label.setObjectName("card_title")
        monitor_layout.addWidget(monitor_label)

        # 状态
        self.status_label = QtWidgets.QLabel("● 准备就绪")
        self.status_label.setObjectName("status")
        self.status_label.setStyleSheet("color: #95a5a6; font-size: 15px;")
        monitor_layout.addWidget(self.status_label)

        # 监控按钮
        self.start_btn = QtWidgets.QPushButton("启动")
        self.start_btn.setObjectName("start_btn")
        self.start_btn.setFixedHeight(50)
        self.start_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.start_btn.clicked.connect(self._toggle_monitoring)
        monitor_layout.addWidget(self.start_btn)

        # 提示
        info_label = QtWidgets.QLabel("请先在「设置」中填写游戏名称、窗口和日志路径，然后点击开始")
        info_label.setObjectName("hint_label")
        monitor_layout.addWidget(info_label)

        home_layout.addWidget(monitor_card)

        # 功能开关卡片
        toggle_card = QtWidgets.QFrame()
        toggle_card.setObjectName("card")
        toggle_layout = QtWidgets.QVBoxLayout(toggle_card)
        toggle_layout.setContentsMargins(30, 25, 30, 25)
        toggle_layout.setSpacing(12)

        toggle_title = QtWidgets.QLabel("功能开关")
        toggle_title.setObjectName("card_title")
        toggle_layout.addWidget(toggle_title)

        toggle_row = QtWidgets.QHBoxLayout()
        toggle_row.setSpacing(16)

        # KILLSAY 开关
        self.killsay_btn = QtWidgets.QPushButton("Killsay: ON")
        self.killsay_btn.setObjectName("success")
        self.killsay_btn.setFixedHeight(36)
        self.killsay_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.killsay_btn.clicked.connect(self._toggle_killsay)
        toggle_row.addWidget(self.killsay_btn)

        # 反狙击开关
        self.anti_snipe_btn = QtWidgets.QPushButton("反狙击: OFF")
        self.anti_snipe_btn.setObjectName("secondary")
        self.anti_snipe_btn.setFixedHeight(36)
        self.anti_snipe_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.anti_snipe_btn.clicked.connect(self._toggle_anti_snipe)
        toggle_row.addWidget(self.anti_snipe_btn)

        # 战绩统计开关
        self.stats_btn = QtWidgets.QPushButton("战绩统计: ON")
        self.stats_btn.setObjectName("success")
        self.stats_btn.setFixedHeight(36)
        self.stats_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.stats_btn.clicked.connect(self._toggle_stats)
        toggle_row.addWidget(self.stats_btn)

        # AutoText 开关
        self.autotext_btn = QtWidgets.QPushButton("AutoText: ON")
        self.autotext_btn.setObjectName("success")
        self.autotext_btn.setFixedHeight(36)
        self.autotext_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.autotext_btn.clicked.connect(self._toggle_autotext)
        toggle_row.addWidget(self.autotext_btn)

        # AutoGG 开关
        self.autogg_btn = QtWidgets.QPushButton("AutoGG: ON")
        self.autogg_btn.setObjectName("success")
        self.autogg_btn.setFixedHeight(36)
        self.autogg_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.autogg_btn.clicked.connect(self._toggle_autogg)
        toggle_row.addWidget(self.autogg_btn)

        toggle_row.addStretch()
        toggle_layout.addLayout(toggle_row)

        home_layout.addWidget(toggle_card)
        home_layout.addStretch()
        self.stack.addWidget(page_home)

        # --- 页面1: 基本设置 ---
        page_settings = QtWidgets.QWidget()
        settings_layout = QtWidgets.QVBoxLayout(page_settings)
        settings_layout.setSpacing(20)

        settings_title = QtWidgets.QLabel("基本设置")
        settings_title.setObjectName("page_title")
        settings_layout.addWidget(settings_title)

        settings_card = QtWidgets.QFrame()
        settings_card.setObjectName("card")
        card_layout = QtWidgets.QVBoxLayout(settings_card)
        card_layout.setContentsMargins(30, 25, 30, 25)
        card_layout.setSpacing(16)

        # 游戏名称
        user_label = QtWidgets.QLabel("游戏ID")
        user_label.setObjectName("field_label")
        card_layout.addWidget(user_label)

        user_row = QtWidgets.QHBoxLayout()
        self.user_entry = QtWidgets.QLineEdit()
        self.user_entry.setPlaceholderText("输入你的游戏ID")
        self.user_entry.setFixedHeight(38)
        user_row.addWidget(self.user_entry)
        user_history_btn = QtWidgets.QPushButton("历史记录")
        user_history_btn.setObjectName("secondary")
        user_history_btn.setFixedSize(60, 38)
        user_history_btn.setCursor(QtCore.Qt.PointingHandCursor)
        user_history_btn.clicked.connect(lambda: self._show_history_dialog("players", self.user_entry))
        user_row.addWidget(user_history_btn)
        save_history_btn = QtWidgets.QPushButton("保存记录")
        save_history_btn.setObjectName("secondary")
        save_history_btn.setFixedSize(60, 38)
        save_history_btn.setCursor(QtCore.Qt.PointingHandCursor)
        save_history_btn.clicked.connect(self._save_to_history)
        user_row.addWidget(save_history_btn)
        card_layout.addLayout(user_row)

        # 分隔
        card_layout.addWidget(self._make_divider())

        # 窗口名称
        window_label = QtWidgets.QLabel("游戏窗口")
        window_label.setObjectName("field_label")
        card_layout.addWidget(window_label)

        window_desc = QtWidgets.QLabel("选择游戏客户端窗口，脚本将向该窗口发送聊天消息")
        window_desc.setObjectName("hint_label")
        card_layout.addWidget(window_desc)

        window_row = QtWidgets.QHBoxLayout()
        self.window_combo = QtWidgets.QComboBox()
        self.window_combo.setEditable(True)
        self.window_combo.setFixedHeight(38)
        self.window_combo.lineEdit().setPlaceholderText("选择窗口或输入窗口名称")
        window_row.addWidget(self.window_combo)
        refresh_win_btn = QtWidgets.QPushButton("刷新")
        refresh_win_btn.setObjectName("secondary")
        refresh_win_btn.setFixedSize(60, 38)
        refresh_win_btn.setCursor(QtCore.Qt.PointingHandCursor)
        refresh_win_btn.clicked.connect(self._refresh_window_list)
        window_row.addWidget(refresh_win_btn)
        card_layout.addLayout(window_row)

        self._refresh_window_list()

        # 分隔
        card_layout.addWidget(self._make_divider())

        # 日志文件
        file_label = QtWidgets.QLabel("游戏日志文件")
        file_label.setObjectName("field_label")
        card_layout.addWidget(file_label)

        file_row = QtWidgets.QHBoxLayout()
        self.log_file_entry = QtWidgets.QLineEdit()
        self.log_file_entry.setText("D:\\MCLDownload\\Game\\.minecraft\\logs\\latest.log")
        self.log_file_entry.setPlaceholderText("选择 Minecraft 的 latest.log 日志文件")
        self.log_file_entry.setFixedHeight(38)
        file_row.addWidget(self.log_file_entry)
        browse_btn = QtWidgets.QPushButton("浏览")
        browse_btn.setObjectName("secondary")
        browse_btn.setFixedSize(60, 38)
        browse_btn.setCursor(QtCore.Qt.PointingHandCursor)
        browse_btn.clicked.connect(self._select_log_file)
        file_row.addWidget(browse_btn)
        file_history_btn = QtWidgets.QPushButton("历史")
        file_history_btn.setObjectName("secondary")
        file_history_btn.setFixedSize(60, 38)
        file_history_btn.setCursor(QtCore.Qt.PointingHandCursor)
        file_history_btn.clicked.connect(lambda: self._show_history_dialog("paths", self.log_file_entry))
        file_row.addWidget(file_history_btn)
        card_layout.addLayout(file_row)

        # 分隔
        card_layout.addWidget(self._make_divider())

        # 聊天按键
        chat_key_label = QtWidgets.QLabel("聊天按键")
        chat_key_label.setObjectName("field_label")
        card_layout.addWidget(chat_key_label)

        chat_key_desc = QtWidgets.QLabel("游戏中打开聊天栏的按键，默认为 T")
        chat_key_desc.setObjectName("hint_label")
        card_layout.addWidget(chat_key_desc)

        chat_key_row = QtWidgets.QHBoxLayout()
        self.chat_key_value = QtWidgets.QLineEdit()
        self.chat_key_value.setReadOnly(True)
        self.chat_key_value.setText(self._pretty_key(self.chat_key))
        self.chat_key_value.setFixedHeight(38)
        self.chat_key_value.setFixedWidth(140)
        self.chat_key_value.setAlignment(QtCore.Qt.AlignCenter)
        chat_key_row.addWidget(self.chat_key_value)

        self.chat_key_btn = QtWidgets.QPushButton("点击以更改")
        self.chat_key_btn.setObjectName("secondary")
        self.chat_key_btn.setFixedSize(80, 38)
        self.chat_key_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.chat_key_btn.clicked.connect(self._capture_chat_key)
        chat_key_row.addWidget(self.chat_key_btn)
        chat_key_row.addStretch()
        card_layout.addLayout(chat_key_row)

        settings_layout.addWidget(settings_card)
        settings_layout.addStretch()
        self.stack.addWidget(page_settings)

        # --- 页面2: 配置管理 ---
        page_config = QtWidgets.QWidget()
        config_page_layout = QtWidgets.QVBoxLayout(page_config)
        config_page_layout.setSpacing(20)

        config_title = QtWidgets.QLabel("配置管理")
        config_title.setObjectName("page_title")
        config_page_layout.addWidget(config_title)

        # 快捷操作卡片
        quick_card = QtWidgets.QFrame()
        quick_card.setObjectName("card")
        quick_layout = QtWidgets.QVBoxLayout(quick_card)
        quick_layout.setContentsMargins(25, 20, 25, 20)
        quick_layout.setSpacing(12)

        quick_label = QtWidgets.QLabel("快捷操作")
        quick_label.setObjectName("card_title")
        quick_layout.addWidget(quick_label)

        quick_btn_row = QtWidgets.QHBoxLayout()
        edit_config_btn = QtWidgets.QPushButton("编辑当前配置")
        edit_config_btn.setFixedHeight(38)
        edit_config_btn.setCursor(QtCore.Qt.PointingHandCursor)
        edit_config_btn.clicked.connect(self._edit_current_config)
        quick_btn_row.addWidget(edit_config_btn)

        new_config_btn = QtWidgets.QPushButton("新建配置")
        new_config_btn.setObjectName("secondary")
        new_config_btn.setFixedHeight(38)
        new_config_btn.setCursor(QtCore.Qt.PointingHandCursor)
        new_config_btn.clicked.connect(self._show_new_config_dialog)
        quick_btn_row.addWidget(new_config_btn)

        manage_config_btn = QtWidgets.QPushButton("配置管理器")
        manage_config_btn.setObjectName("secondary")
        manage_config_btn.setFixedHeight(38)
        manage_config_btn.setCursor(QtCore.Qt.PointingHandCursor)
        manage_config_btn.clicked.connect(self._show_config_manager)
        quick_btn_row.addWidget(manage_config_btn)
        quick_layout.addLayout(quick_btn_row)

        config_page_layout.addWidget(quick_card)

        # 分享码卡片
        share_card = QtWidgets.QFrame()
        share_card.setObjectName("card")
        share_layout = QtWidgets.QVBoxLayout(share_card)
        share_layout.setContentsMargins(25, 20, 25, 20)
        share_layout.setSpacing(12)

        share_label = QtWidgets.QLabel("分享码")
        share_label.setObjectName("card_title")
        share_layout.addWidget(share_label)

        share_desc = QtWidgets.QLabel("生成分享码发送给其他玩家，或粘贴分享码快速导入配置 (KS1-... 格式)")
        share_desc.setObjectName("hint_label")
        share_layout.addWidget(share_desc)

        share_btn_row = QtWidgets.QHBoxLayout()
        export_btn = QtWidgets.QPushButton("导出分享码")
        export_btn.setFixedHeight(38)
        export_btn.setCursor(QtCore.Qt.PointingHandCursor)
        export_btn.clicked.connect(lambda: self._export_share_code(self))
        share_btn_row.addWidget(export_btn)

        import_btn = QtWidgets.QPushButton("导入分享码")
        import_btn.setObjectName("secondary")
        import_btn.setFixedHeight(38)
        import_btn.setCursor(QtCore.Qt.PointingHandCursor)
        import_btn.clicked.connect(lambda: self._import_share_code(self))
        share_btn_row.addWidget(import_btn)
        share_btn_row.addStretch()
        share_layout.addLayout(share_btn_row)

        config_page_layout.addWidget(share_card)
        config_page_layout.addStretch()
        self.stack.addWidget(page_config)

        # --- 页面3: 战绩统计 ---
        page_stats = QtWidgets.QWidget()
        stats_page_layout = QtWidgets.QVBoxLayout(page_stats)
        stats_page_layout.setSpacing(20)

        stats_title = QtWidgets.QLabel("战绩统计")
        stats_title.setObjectName("page_title")
        stats_page_layout.addWidget(stats_title)

        stats_card = QtWidgets.QFrame()
        stats_card.setObjectName("card")
        stats_card_layout = QtWidgets.QVBoxLayout(stats_card)
        stats_card_layout.setContentsMargins(30, 25, 30, 25)
        stats_card_layout.setSpacing(20)

        # 统计数字 - 第一行：击杀统计
        counters_row1 = QtWidgets.QHBoxLayout()
        counters_row1.setSpacing(30)

        # 击杀
        kill_box = QtWidgets.QFrame()
        kill_box.setObjectName("stat_card")
        kill_box_layout = QtWidgets.QVBoxLayout(kill_box)
        kill_box_layout.setContentsMargins(20, 18, 20, 18)
        kill_box_layout.setAlignment(QtCore.Qt.AlignCenter)
        kill_label = QtWidgets.QLabel("击杀")
        kill_label.setObjectName("stat_label")
        kill_label.setAlignment(QtCore.Qt.AlignCenter)
        kill_box_layout.addWidget(kill_label)
        self.kills_label = self._make_flip(0, 30, 46)
        kill_box_layout.addWidget(self.kills_label, 0, QtCore.Qt.AlignCenter)
        counters_row1.addWidget(kill_box)

        # 死亡
        death_box = QtWidgets.QFrame()
        death_box.setObjectName("stat_card")
        death_box_layout = QtWidgets.QVBoxLayout(death_box)
        death_box_layout.setContentsMargins(20, 18, 20, 18)
        death_box_layout.setAlignment(QtCore.Qt.AlignCenter)
        death_label = QtWidgets.QLabel("死亡")
        death_label.setObjectName("stat_label")
        death_label.setAlignment(QtCore.Qt.AlignCenter)
        death_box_layout.addWidget(death_label)
        self.deaths_label = self._make_flip(0, 30, 46)
        death_box_layout.addWidget(self.deaths_label, 0, QtCore.Qt.AlignCenter)
        counters_row1.addWidget(death_box)

        # KDR
        kdr_box = QtWidgets.QFrame()
        kdr_box.setObjectName("stat_card")
        kdr_box_layout = QtWidgets.QVBoxLayout(kdr_box)
        kdr_box_layout.setContentsMargins(20, 18, 20, 18)
        kdr_box_layout.setAlignment(QtCore.Qt.AlignCenter)
        kdr_label = QtWidgets.QLabel("K/D")
        kdr_label.setObjectName("stat_label")
        kdr_label.setAlignment(QtCore.Qt.AlignCenter)
        kdr_box_layout.addWidget(kdr_label)
        self.kdr_label = self._make_flip(2, 30, 46)
        kdr_box_layout.addWidget(self.kdr_label, 0, QtCore.Qt.AlignCenter)
        counters_row1.addWidget(kdr_box)

        stats_card_layout.addLayout(counters_row1)

        # 统计数字 - 第二行：胜负统计
        counters_row2 = QtWidgets.QHBoxLayout()
        counters_row2.setSpacing(30)

        # 胜利
        win_box = QtWidgets.QFrame()
        win_box.setObjectName("stat_card")
        win_box_layout = QtWidgets.QVBoxLayout(win_box)
        win_box_layout.setContentsMargins(20, 18, 20, 18)
        win_box_layout.setAlignment(QtCore.Qt.AlignCenter)
        win_label = QtWidgets.QLabel("胜利")
        win_label.setObjectName("stat_label")
        win_label.setAlignment(QtCore.Qt.AlignCenter)
        win_box_layout.addWidget(win_label)
        self.wins_label = self._make_flip(0, 30, 46)
        win_box_layout.addWidget(self.wins_label, 0, QtCore.Qt.AlignCenter)
        counters_row2.addWidget(win_box)

        # 失败
        loss_box = QtWidgets.QFrame()
        loss_box.setObjectName("stat_card")
        loss_box_layout = QtWidgets.QVBoxLayout(loss_box)
        loss_box_layout.setContentsMargins(20, 18, 20, 18)
        loss_box_layout.setAlignment(QtCore.Qt.AlignCenter)
        loss_label = QtWidgets.QLabel("失败")
        loss_label.setObjectName("stat_label")
        loss_label.setAlignment(QtCore.Qt.AlignCenter)
        loss_box_layout.addWidget(loss_label)
        self.losses_label = self._make_flip(0, 30, 46)
        loss_box_layout.addWidget(self.losses_label, 0, QtCore.Qt.AlignCenter)
        counters_row2.addWidget(loss_box)

        # WLR
        wlr_box = QtWidgets.QFrame()
        wlr_box.setObjectName("stat_card")
        wlr_box_layout = QtWidgets.QVBoxLayout(wlr_box)
        wlr_box_layout.setContentsMargins(20, 18, 20, 18)
        wlr_box_layout.setAlignment(QtCore.Qt.AlignCenter)
        wlr_label = QtWidgets.QLabel("W/L")
        wlr_label.setObjectName("stat_label")
        wlr_label.setAlignment(QtCore.Qt.AlignCenter)
        wlr_box_layout.addWidget(wlr_label)
        self.wlr_label = self._make_flip(2, 30, 46)
        wlr_box_layout.addWidget(self.wlr_label, 0, QtCore.Qt.AlignCenter)
        counters_row2.addWidget(wlr_box)

        stats_card_layout.addLayout(counters_row2)

        # 连胜显示
        ws_row = QtWidgets.QHBoxLayout()
        ws_row.setAlignment(QtCore.Qt.AlignCenter)
        ws_label = QtWidgets.QLabel("连胜:")
        ws_label.setObjectName("stat_label")
        ws_row.addWidget(ws_label)
        self.ws_label = self._make_flip(0, 24, 36, gap=4)
        ws_row.addWidget(self.ws_label)
        stats_card_layout.addLayout(ws_row)

        # 浮窗按钮
        show_stats_btn = QtWidgets.QPushButton("显示悬浮统计窗口")
        show_stats_btn.setObjectName("secondary")
        show_stats_btn.setFixedHeight(40)
        show_stats_btn.setCursor(QtCore.Qt.PointingHandCursor)
        show_stats_btn.clicked.connect(self._show_stats_window)
        stats_card_layout.addWidget(show_stats_btn)

        stats_page_layout.addWidget(stats_card)
        stats_page_layout.addStretch()

        # 初始化动画对象
        self._init_animations()
        self.stack.addWidget(page_stats)

        # --- 页面4: 快捷消息 (AutoText) ---
        page_autotext = QtWidgets.QWidget()
        autotext_layout = QtWidgets.QVBoxLayout(page_autotext)
        autotext_layout.setSpacing(20)

        autotext_title = QtWidgets.QLabel("AutoText")
        autotext_title.setObjectName("page_title")
        autotext_layout.addWidget(autotext_title)

        autotext_card = QtWidgets.QFrame()
        autotext_card.setObjectName("card")
        autotext_card_layout = QtWidgets.QVBoxLayout(autotext_card)
        autotext_card_layout.setContentsMargins(25, 20, 25, 20)
        autotext_card_layout.setSpacing(12)

        autotext_label = QtWidgets.QLabel("AutoText")
        autotext_label.setObjectName("card_title")
        autotext_card_layout.addWidget(autotext_label)

        autotext_desc = QtWidgets.QLabel("添加消息并绑定按键，监控运行时按下该键即可自动发送。")
        autotext_desc.setObjectName("hint_label")
        autotext_desc.setWordWrap(True)
        autotext_card_layout.addWidget(autotext_desc)

        self.autotext_list = QtWidgets.QListWidget()
        self.autotext_list.setMinimumHeight(220)
        autotext_card_layout.addWidget(self.autotext_list)

        autotext_btn_row = QtWidgets.QHBoxLayout()
        add_autotext_btn = QtWidgets.QPushButton("添加消息")
        add_autotext_btn.setFixedHeight(36)
        add_autotext_btn.setCursor(QtCore.Qt.PointingHandCursor)
        add_autotext_btn.clicked.connect(self._show_autotext_dialog)
        autotext_btn_row.addWidget(add_autotext_btn)

        del_autotext_btn = QtWidgets.QPushButton("删除选中")
        del_autotext_btn.setObjectName("danger")
        del_autotext_btn.setFixedHeight(36)
        del_autotext_btn.setCursor(QtCore.Qt.PointingHandCursor)
        del_autotext_btn.clicked.connect(self._delete_autotext)
        autotext_btn_row.addWidget(del_autotext_btn)
        autotext_btn_row.addStretch()
        autotext_card_layout.addLayout(autotext_btn_row)

        autotext_layout.addWidget(autotext_card)
        autotext_layout.addStretch()
        self.stack.addWidget(page_autotext)

        # 初始填充快捷消息列表
        self._refresh_autotext_list()

        # --- 页面5: 主题设置 ---
        page_theme = QtWidgets.QWidget()
        theme_page_layout = QtWidgets.QVBoxLayout(page_theme)
        theme_page_layout.setSpacing(20)

        theme_title = QtWidgets.QLabel("主题设置")
        theme_title.setObjectName("page_title")
        theme_page_layout.addWidget(theme_title)

        theme_card = QtWidgets.QFrame()
        theme_card.setObjectName("card")
        theme_card_layout = QtWidgets.QVBoxLayout(theme_card)
        theme_card_layout.setContentsMargins(25, 20, 25, 20)
        theme_card_layout.setSpacing(15)

        theme_label = QtWidgets.QLabel("选择主题")
        theme_label.setObjectName("card_title")
        theme_card_layout.addWidget(theme_label)

        theme_row = QtWidgets.QHBoxLayout()
        self.theme_combo = QtWidgets.QComboBox()
        self.theme_combo.setFixedHeight(38)
        self._populate_theme_combo()
        self.theme_combo.currentIndexChanged.connect(self._change_theme)
        theme_row.addWidget(self.theme_combo)

        custom_theme_btn = QtWidgets.QPushButton("自定义主题")
        custom_theme_btn.setFixedHeight(38)
        custom_theme_btn.setCursor(QtCore.Qt.PointingHandCursor)
        custom_theme_btn.clicked.connect(self._show_custom_theme_dialog)
        theme_row.addWidget(custom_theme_btn)
        theme_card_layout.addLayout(theme_row)

        # 主题描述显示
        self.theme_desc_label = QtWidgets.QLabel("")
        self.theme_desc_label.setObjectName("hint_label")
        self.theme_desc_label.setWordWrap(True)
        theme_card_layout.addWidget(self.theme_desc_label)

        theme_page_layout.addWidget(theme_card)
        theme_page_layout.addStretch()
        self.stack.addWidget(page_theme)

        content_layout.addWidget(self.stack)
        root_layout.addWidget(content_frame)

    def _refresh_style(self, widget):
        """强制刷新控件样式（objectName 变更后需要调用）"""
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _make_divider(self):
        """创建分隔线"""
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setObjectName("divider")
        return line

    def _set_status(self, text, color):
        """更新状态栏"""
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 15px;")

    def _start_pulse(self):
        """状态指示灯脉冲动画"""
        if hasattr(self, '_pulse_anim') and self._pulse_anim.state() == QtCore.QAbstractAnimation.Running:
            return
        self._pulse_effect = QtWidgets.QGraphicsOpacityEffect(self.status_label)
        self.status_label.setGraphicsEffect(self._pulse_effect)
        self._pulse_anim = QtCore.QPropertyAnimation(self._pulse_effect, b"opacity")
        self._pulse_anim.setDuration(1200)
        self._pulse_anim.setStartValue(1.0)
        self._pulse_anim.setKeyValueAt(0.5, 0.4)
        self._pulse_anim.setEndValue(1.0)
        self._pulse_anim.setLoopCount(-1)
        self._pulse_anim.start()

    def _stop_pulse(self):
        """停止脉冲动画"""
        if hasattr(self, '_pulse_anim'):
            self._pulse_anim.stop()
        if hasattr(self, '_pulse_effect'):
            self.status_label.setGraphicsEffect(None)
    
    def _init_animations(self):
        """初始化翻页数字动画（控件已在创建时配置，这里统一换色）。"""
        self._apply_flip_colors()

    def _show_history_dialog(self, key, target_entry):
        """显示历史记录对话框"""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("选择历史记录")
        dialog.setFixedSize(400, 300)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        
        list_widget = QtWidgets.QListWidget()
        for item in self.history[key]:
            list_widget.addItem(item)
        layout.addWidget(list_widget)
        
        button_layout = QtWidgets.QHBoxLayout()
        select_btn = QtWidgets.QPushButton("选择")
        select_btn.clicked.connect(lambda: self._select_history_item(list_widget, target_entry, dialog))
        button_layout.addWidget(select_btn)
        
        cancel_btn = QtWidgets.QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        dialog.exec_()
    
    def _select_history_item(self, list_widget, target_entry, dialog):
        """选择历史记录项"""
        current_item = list_widget.currentItem()
        if current_item:
            target_entry.setText(current_item.text())
            dialog.accept()

    def _save_to_history(self):
        """保存当前输入到历史记录"""
        user = self.user_entry.text().strip()
        path = self.log_file_entry.text().strip()
        if user:
            self._add_to_history("players", user)
        if path:
            self._add_to_history("paths", path)
        QtWidgets.QMessageBox.information(self, "成功", "已保存到历史记录")
    
    def _show_stats_window(self):
        """显示统计窗口 - 紧凑布局"""
        if hasattr(self, 'stats_window') and self.stats_window.isVisible():
            self.stats_window.raise_()
            return

        self.stats_window = QtWidgets.QWidget()
        self.stats_window.setWindowTitle("KillSay 数据统计")
        self.stats_window.setFixedSize(240, 300)
        self.stats_window.setWindowFlags(self.stats_window.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        self.stats_window.setStyleSheet(self.theme_mgr.generate_stylesheet())

        layout = QtWidgets.QVBoxLayout(self.stats_window)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        label_style = "font-size: 12px;"
        self._float_flips = []

        def add_row(label_text, decimals=0):
            row = QtWidgets.QHBoxLayout()
            lbl = QtWidgets.QLabel(label_text)
            lbl.setObjectName("stat_label")
            lbl.setStyleSheet(label_style)
            row.addWidget(lbl)
            row.addStretch()
            accent, card, border, hinge = self._flip_colors()
            val = FlipNumber(decimals=decimals, digit_width=20, digit_height=28, gap=3,
                             fg_color=accent, card_bg=card, border_color=border, hinge_color=hinge)
            row.addWidget(val)
            layout.addLayout(row)
            self._float_flips.append(val)
            return val

        self.stats_kills_label = add_row("击杀:")
        self.stats_deaths_label = add_row("死亡:")
        self.stats_kdr_label = add_row("K/D:", 2)

        # 分隔线
        divider = QtWidgets.QFrame()
        divider.setFrameShape(QtWidgets.QFrame.HLine)
        divider.setObjectName("divider")
        layout.addWidget(divider)

        self.stats_wins_label = add_row("胜利:")
        self.stats_losses_label = add_row("失败:")
        self.stats_wlr_label = add_row("W/L:", 2)
        self.stats_ws_label = add_row("连胜:")

        # 更新显示
        self._update_stats_window_display()

        self.stats_window.show()

    def _update_stats_window_display(self):
        """更新统计窗口显示"""
        if not hasattr(self, 'stats_window') or not self.stats_window.isVisible():
            return

        kdr = self.kills / self.deaths if self.deaths != 0 else self.kills
        wlr = self.wins / self.losses if self.losses != 0 else self.wins

        self.stats_kills_label.setValue(self.kills)
        self.stats_deaths_label.setValue(self.deaths)
        self.stats_kdr_label.setValue(kdr)
        self.stats_wins_label.setValue(self.wins)
        self.stats_losses_label.setValue(self.losses)
        self.stats_wlr_label.setValue(wlr)
        self.stats_ws_label.setValue(self.win_streak)
    
    def _select_log_file(self):
        """选择日志文件"""
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "选择日志文件", "", "日志文件 (*.log);;所有文件 (*.*)"
        )
        if filename:
            self.log_file_entry.setText(filename)
    
    def _toggle_anti_snipe(self):
        """切换反狙击功能"""
        self.anti_snipe_enabled = not self.anti_snipe_enabled
        if self.anti_snipe_enabled:
            self.anti_snipe_btn.setText("反狙击: ON")
            self.anti_snipe_btn.setObjectName("success")
        else:
            self.anti_snipe_btn.setText("反狙击: OFF")
            self.anti_snipe_btn.setObjectName("secondary")
        self._refresh_style(self.anti_snipe_btn)

    def _toggle_killsay(self):
        """切换KILLSAY功能"""
        self.killsay_enabled = not self.killsay_enabled
        if self.killsay_enabled:
            self.killsay_btn.setText("Killsay: ON")
            self.killsay_btn.setObjectName("success")
        else:
            self.killsay_btn.setText("Killsay: OFF")
            self.killsay_btn.setObjectName("secondary")
        self._refresh_style(self.killsay_btn)

    def _toggle_stats(self):
        """切换战绩统计功能"""
        self.stats_enabled = not self.stats_enabled
        if self.stats_enabled:
            self.stats_btn.setText("战绩统计: ON")
            self.stats_btn.setObjectName("success")
        else:
            self.stats_btn.setText("战绩统计: OFF")
            self.stats_btn.setObjectName("secondary")
        self._refresh_style(self.stats_btn)

    def _toggle_autotext(self):
        """切换 AutoText 功能"""
        self.autotext_enabled = not self.autotext_enabled
        if self.autotext_enabled:
            self.autotext_btn.setText("AutoText: ON")
            self.autotext_btn.setObjectName("success")
        else:
            self.autotext_btn.setText("AutoText: OFF")
            self.autotext_btn.setObjectName("secondary")
        self._refresh_style(self.autotext_btn)
        # 监控中则立即重新应用热键
        if self.is_monitoring:
            self._register_autotext_hotkeys()

    def _toggle_autogg(self):
        """切换 AutoGG 功能"""
        self.autogg_enabled = not self.autogg_enabled
        if self.autogg_enabled:
            self.autogg_btn.setText("AutoGG: ON")
            self.autogg_btn.setObjectName("success")
        else:
            self.autogg_btn.setText("AutoGG: OFF")
            self.autogg_btn.setObjectName("secondary")
        self._refresh_style(self.autogg_btn)

    def _pretty_key(self, key):
        """把键盘键名转成更适合显示的文本"""
        if not key:
            return "未设置"
        mapping = {
            "space": "空格",
            "enter": "回车",
            "esc": "Esc",
            "tab": "Tab",
            "shift": "Shift",
            "ctrl": "Ctrl",
            "alt": "Alt",
            "backspace": "退格",
            "delete": "Delete",
            "caps lock": "CapsLock",
            "up": "↑",
            "down": "↓",
            "left": "←",
            "right": "→",
        }
        return mapping.get(str(key).lower(), str(key).upper())

    def _capture_chat_key(self):
        """录制聊天按键（弹窗捕获，不依赖键盘全局监听）"""
        dialog = KeyCaptureDialog(self, "设置聊天按键")
        dialog.exec_()
        key = dialog.captured_key
        if not key:
            return
        self.chat_key = key
        self.chat_key_value.setText(self._pretty_key(key))
        # 立即保存到当前配置
        if self.config_mgr.current_config is not None:
            self.config_mgr.current_config["chat_key"] = self.chat_key
            self.config_mgr.save_current_config()

    def _refresh_autotext_list(self):
        """刷新快捷消息列表"""
        if not hasattr(self, 'autotext_list'):
            return
        self.autotext_list.clear()
        for item in self.autotext:
            if not isinstance(item, dict):
                continue
            msg = item.get("message", "")
            key = item.get("key", "")
            self.autotext_list.addItem(f"[{self._pretty_key(key)}]  {msg}")

    def _save_autotext(self):
        """把快捷消息保存到当前配置"""
        if self.config_mgr.current_config is not None:
            self.config_mgr.current_config["autotext"] = self.autotext
            self.config_mgr.save_current_config()

    def _show_autotext_dialog(self):
        """显示添加快捷消息对话框"""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("添加快捷消息")
        dialog.setFixedSize(440, 240)

        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        layout.addWidget(QtWidgets.QLabel("消息内容："))
        msg_edit = QtWidgets.QLineEdit()
        msg_edit.setPlaceholderText("输入要自动发送的消息")
        layout.addWidget(msg_edit)

        layout.addWidget(QtWidgets.QLabel("绑定键位："))
        key_row = QtWidgets.QHBoxLayout()
        captured = {"key": None}
        key_value = QtWidgets.QLineEdit()
        key_value.setReadOnly(True)
        key_value.setPlaceholderText("未设置")
        key_value.setFixedHeight(38)
        key_value.setFixedWidth(140)
        key_value.setAlignment(QtCore.Qt.AlignCenter)
        key_row.addWidget(key_value)

        key_record_btn = QtWidgets.QPushButton("录制")
        key_record_btn.setObjectName("secondary")
        key_record_btn.setFixedSize(80, 38)
        key_record_btn.setCursor(QtCore.Qt.PointingHandCursor)

        def record_key():
            dlg = KeyCaptureDialog(dialog, "设置消息键位")
            dlg.exec_()
            if dlg.captured_key:
                captured["key"] = dlg.captured_key
                key_value.setText(self._pretty_key(dlg.captured_key))

        key_record_btn.clicked.connect(record_key)
        key_row.addWidget(key_record_btn)
        key_row.addStretch()
        layout.addLayout(key_row)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()

        def do_add():
            msg = msg_edit.text().strip()
            if not msg:
                QtWidgets.QMessageBox.warning(dialog, "错误", "请输入消息内容")
                return
            if not captured["key"]:
                QtWidgets.QMessageBox.warning(dialog, "错误", "请先设置键位")
                return
            self._add_autotext(msg, captured["key"])
            dialog.accept()

        save_btn = QtWidgets.QPushButton("添加")
        save_btn.clicked.connect(do_add)
        btn_row.addWidget(save_btn)

        cancel_btn = QtWidgets.QPushButton("取消")
        cancel_btn.setObjectName("secondary")
        cancel_btn.clicked.connect(dialog.reject)
        btn_row.addWidget(cancel_btn)

        layout.addLayout(btn_row)
        dialog.exec_()

    def _add_autotext(self, msg, key):
        """添加一条快捷消息"""
        self.autotext.append({"message": msg, "key": key})
        self._save_autotext()
        self._refresh_autotext_list()

    def _delete_autotext(self):
        """删除选中的快捷消息"""
        row = self.autotext_list.currentRow()
        if row < 0 or row >= len(self.autotext):
            QtWidgets.QMessageBox.warning(self, "提示", "请先选中要删除的消息")
            return
        self.autotext.pop(row)
        self._save_autotext()
        self._refresh_autotext_list()

    def _key_to_vk(self, key_name):
        """把 keyboard 库键名转换为 Windows 虚拟键码（VK），无法转换返回 None。"""
        name = str(key_name).lower().strip()
        if not name:
            return None
        # 字母 A-Z
        if len(name) == 1 and 'a' <= name <= 'z':
            return ord(name.upper())
        # 数字 0-9
        if len(name) == 1 and '0' <= name <= '9':
            return ord(name)
        # 其他单字符符号（用 VkKeyScan 转换）
        if len(name) == 1:
            try:
                vk = ctypes.windll.user32.VkKeyScanW(ord(name))
                if vk != -1 and vk != 0xFFFF:
                    return vk & 0xFF
            except Exception:
                pass
        # 功能键 F1-F24
        if name.startswith('f') and name[1:].isdigit():
            n = int(name[1:])
            if 1 <= n <= 24:
                return 0x70 + (n - 1)
        # 特殊键
        special = {
            'enter': 0x0D, 'return': 0x0D,
            'space': 0x20,
            'tab': 0x09,
            'esc': 0x1B, 'escape': 0x1B,
            'backspace': 0x08,
            'delete': 0x2E,
            'up': 0x26, 'down': 0x28, 'left': 0x25, 'right': 0x27,
            'home': 0x24, 'end': 0x23,
            'page up': 0x21, 'page down': 0x22,
            'insert': 0x2D,
            'caps lock': 0x14,
        }
        return special.get(name)

    def _register_autotext_hotkeys(self):
        """用 Windows 原生 RegisterHotKey 注册快捷消息热键，返回失败的键位列表。"""
        self._unregister_autotext_hotkeys()
        self._autotext_handlers = []  # [(hotkey_id, message)]
        if not self.autotext_enabled:
            return []
        hwnd = int(self.winId())
        failed = []
        next_id = 1
        for item in self.autotext:
            if not isinstance(item, dict):
                continue
            key = item.get("key")
            msg = item.get("message")
            if not key or not msg:
                continue
            vk = self._key_to_vk(key)
            if vk is None:
                failed.append(self._pretty_key(key))
                continue
            try:
                ok = ctypes.windll.user32.RegisterHotKey(hwnd, next_id, 0, vk)
            except Exception:
                ok = 0
            if ok:
                self._autotext_handlers.append((next_id, msg))
                next_id += 1
            else:
                failed.append(self._pretty_key(key))
        return failed

    def _unregister_autotext_hotkeys(self):
        """注销所有快捷消息热键"""
        hwnd = int(self.winId())
        for (hotkey_id, _msg) in getattr(self, '_autotext_handlers', []):
            try:
                ctypes.windll.user32.UnregisterHotKey(hwnd, hotkey_id)
            except Exception:
                pass
        self._autotext_handlers = []

    def _on_autotext_triggered(self, msg):
        """快捷消息热键被按下"""
        if not self.is_monitoring or not self.autotext_enabled:
            return
        threading.Thread(target=self._send_autotext, args=(msg,), daemon=True).start()

    def _send_autotext(self, msg):
        """发送快捷消息"""
        self._send_chat(msg)

    def nativeEvent(self, eventType, message):
        """处理 Windows 原生消息：WM_HOTKEY 触发对应的快捷消息。"""
        try:
            if eventType == b"windows_generic_MSG":
                msg = ctypes.wintypes.MSG.from_address(int(message))
                if msg.message == 0x0312:  # WM_HOTKEY
                    hotkey_id = msg.wParam
                    for (hid, text) in self._autotext_handlers:
                        if hid == hotkey_id:
                            self._on_autotext_triggered(text)
                            break
        except Exception:
            pass
        return super().nativeEvent(eventType, message)

    def _refresh_window_list(self):
        """刷新窗口列表"""
        current_text = self.window_combo.currentText()
        self.window_combo.clear()
        try:
            windows = pygetwindow.getAllWindows()
            titles = [w.title for w in windows if w.title and w.title.strip()]
            self.window_combo.addItems(titles)
        except Exception as e:
            print(f"获取窗口列表失败: {e}")
        # 恢复之前选择的窗口
        if current_text:
            idx = self.window_combo.findText(current_text)
            if idx >= 0:
                self.window_combo.setCurrentIndex(idx)
            else:
                self.window_combo.setCurrentText(current_text)

    def _open_config_editor(self, config_name):
        """打开配置编辑窗口，编辑指定名称的配置（不切换当前配置）"""
        config_path = self.config_mgr.config_dir / f"{config_name}.json"
        if not config_path.exists():
            QtWidgets.QMessageBox.warning(self, "错误", "配置文件不存在")
            return
        
        # 加载要编辑的配置数据
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                edit_config = json.load(f)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "错误", f"无法加载配置: {e}")
            return
        
        is_current = (config_path == self.config_mgr.current_config_path)
        
        # 创建编辑窗口
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(f"编辑配置 - {config_name}")
        dialog.setFixedSize(700, 600)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标签页
        tab_widget = QtWidgets.QTabWidget()
        layout.addWidget(tab_widget)
        
        # 狙击手名单标签页
        sniper_tab = QtWidgets.QWidget()
        sniper_layout = QtWidgets.QVBoxLayout(sniper_tab)
        sniper_layout.addWidget(QtWidgets.QLabel("狙击手名单 (每行一个名字):"))
        self.sniper_text = QtWidgets.QTextEdit()
        self.sniper_text.setPlainText("\n".join(edit_config.get("sniper_list", [])))
        sniper_layout.addWidget(self.sniper_text)
        tab_widget.addTab(sniper_tab, "狙击手名单")
        
        # 加入检测模式标签页
        pattern_tab = QtWidgets.QWidget()
        pattern_layout = QtWidgets.QVBoxLayout(pattern_tab)
        pattern_layout.addWidget(QtWidgets.QLabel("玩家加入游戏检测模式 (每行一个):"))
        self.pattern_text = QtWidgets.QTextEdit()
        self.pattern_text.setPlainText("\n".join(edit_config.get("join_patterns", [])))
        pattern_layout.addWidget(self.pattern_text)
        
        pattern_help = QtWidgets.QLabel("提示: %t=玩家名称\n示例: %t加入了游戏 或 %t joined the game")
        pattern_help.setStyleSheet("font-size: 11px; color: #bdc3c7;")
        pattern_layout.addWidget(pattern_help)
        tab_widget.addTab(pattern_tab, "加入检测模式")
        
        # 反狙击消息标签页
        msg_tab = QtWidgets.QWidget()
        msg_layout = QtWidgets.QVBoxLayout(msg_tab)
        msg_layout.addWidget(QtWidgets.QLabel("检测到狙击手时发送的消息 (每行一个):"))
        self.msg_text = QtWidgets.QTextEdit()
        self.msg_text.setPlainText("\n".join(edit_config.get("anti_snipe_messages", [])))
        msg_layout.addWidget(self.msg_text)
        tab_widget.addTab(msg_tab, "反狙击消息")
        
        # 击杀检测模式标签页
        kill_pattern_tab = QtWidgets.QWidget()
        kill_pattern_layout = QtWidgets.QVBoxLayout(kill_pattern_tab)
        kill_pattern_layout.addWidget(QtWidgets.QLabel("击杀检测模式 (每行一个，使用 %o 和 %u 占位符):"))
        self.kill_pattern_text = QtWidgets.QTextEdit()
        self.kill_pattern_text.setPlainText("\n".join(edit_config.get("kill_patterns", [])))
        kill_pattern_layout.addWidget(self.kill_pattern_text)
        
        help_label = QtWidgets.QLabel("提示: %o=对象(被击杀者), %u=用户(击杀者), %n=动态数字\n示例: %o被%u击败 或 %u击败了%o")
        help_label.setStyleSheet("font-size: 11px; color: #bdc3c7;")
        kill_pattern_layout.addWidget(help_label)
        tab_widget.addTab(kill_pattern_tab, "击杀检测模式")

        # 胜利检测模式标签页
        win_pattern_tab = QtWidgets.QWidget()
        win_pattern_layout = QtWidgets.QVBoxLayout(win_pattern_tab)
        win_pattern_layout.addWidget(QtWidgets.QLabel("胜利检测模式 (每行一个，使用 %p 占位符):"))
        self.win_pattern_text = QtWidgets.QTextEdit()
        self.win_pattern_text.setPlainText("\n".join(edit_config.get("win_patterns", [])))
        win_pattern_layout.addWidget(self.win_pattern_text)

        win_help = QtWidgets.QLabel("提示: %p=玩家名称, %m=任意字符(地图名等)\n示例: 恭喜! %p 在地图 %m 获胜!")
        win_help.setStyleSheet("font-size: 11px; color: #bdc3c7;")
        win_pattern_layout.addWidget(win_help)
        tab_widget.addTab(win_pattern_tab, "胜利检测模式")

        # 击杀消息标签页
        kill_msg_tab = QtWidgets.QWidget()
        kill_msg_layout = QtWidgets.QVBoxLayout(kill_msg_tab)
        kill_msg_layout.addWidget(QtWidgets.QLabel("击杀后发送的消息 (每行一个，可使用 %u 和 %o 占位符):"))
        self.kill_msg_text = QtWidgets.QTextEdit()
        self.kill_msg_text.setPlainText("\n".join(edit_config.get("kill_messages", [])))
        kill_msg_layout.addWidget(self.kill_msg_text)
        
        help_label2 = QtWidgets.QLabel("提示: %u=用户(击杀者), %o=对象(被击杀者)\n如果没有占位符，则发送原消息。")
        help_label2.setStyleSheet("font-size: 11px; color: #bdc3c7;")
        kill_msg_layout.addWidget(help_label2)
        tab_widget.addTab(kill_msg_tab, "击杀消息")
        
        # 消息前缀与格式设置标签页
        format_tab = QtWidgets.QWidget()
        format_layout = QtWidgets.QFormLayout(format_tab)
        self.prefix_edit = QtWidgets.QLineEdit(edit_config.get("message_prefix", ""))
        format_layout.addRow("消息前缀:", self.prefix_edit)
        self.format_edit = QtWidgets.QLineEdit(edit_config.get("killsay_format", ConfigManager.DEFAULT_CONFIG["killsay_format"]))
        format_layout.addRow("Killsay 格式:", self.format_edit)
        self.chat_key_edit = QtWidgets.QLineEdit(edit_config.get("chat_key", ConfigManager.DEFAULT_CONFIG["chat_key"]))
        self.chat_key_edit.setPlaceholderText("t")
        format_layout.addRow("聊天按键:", self.chat_key_edit)
        format_help = QtWidgets.QLabel("支持占位符:\n%t - 前缀\n%m - 击杀消息内容\n%u - 用户(击杀者名称)\n%o - 对象(被击杀者名称)\n%c - 当前击杀数\n示例: %t%m | 当前击杀数：%c")
        format_help.setStyleSheet("font-size: 11px; color: #bdc3c7;")
        format_help.setWordWrap(True)
        format_layout.addRow(format_help)
        tab_widget.addTab(format_tab, "消息格式")
        
        # 按钮区域
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        
        save_btn = QtWidgets.QPushButton("保存")
        save_btn.clicked.connect(lambda: self._save_config_edit(dialog, config_path, is_current, config_name))
        button_layout.addWidget(save_btn)
        
        cancel_btn = QtWidgets.QPushButton("取消")
        cancel_btn.setObjectName("secondary")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        dialog.exec_()
    
    def _save_config_edit(self, dialog, config_path, is_current, config_name):
        """保存编辑后的配置"""
        try:
            # 从文本框收集数据
            sniper_list = [line.strip() for line in self.sniper_text.toPlainText().split('\n') if line.strip()]
            join_patterns = [line.strip() for line in self.pattern_text.toPlainText().split('\n') if line.strip()]
            anti_snipe_messages = [line.strip() for line in self.msg_text.toPlainText().split('\n') if line.strip()]
            kill_patterns = [line.strip() for line in self.kill_pattern_text.toPlainText().split('\n') if line.strip()]
            kill_messages = [line.strip() for line in self.kill_msg_text.toPlainText().split('\n') if line.strip()]
            win_patterns = [line.strip() for line in self.win_pattern_text.toPlainText().split('\n') if line.strip()]
            prefix = self.prefix_edit.text().strip()
            killsay_format = self.format_edit.text().strip() or ConfigManager.DEFAULT_CONFIG["killsay_format"]
            chat_key = self.chat_key_edit.text().strip() or ConfigManager.DEFAULT_CONFIG["chat_key"]

            # 构建配置数据
            config_data = {
                "sniper_list": sniper_list,
                "join_patterns": join_patterns,
                "anti_snipe_messages": anti_snipe_messages,
                "kill_patterns": kill_patterns,
                "kill_messages": kill_messages,
                "message_prefix": prefix,
                "killsay_format": killsay_format,
                "chat_key": chat_key,
                "win_patterns": win_patterns
            }

            # 保留之前保存的战绩数据
            try:
                from_config = json.loads(open(config_path, 'r', encoding='utf-8').read()) if pl.Path(config_path).exists() else {}
            except:
                from_config = {}
            if "saved_stats" in from_config:
                config_data["saved_stats"] = from_config["saved_stats"]
            if "autotext" in from_config:
                config_data["autotext"] = from_config["autotext"]
            else:
                config_data["autotext"] = self.autotext
            
            # 保存配置
            self.config_mgr.save_config(config_path, config_data)
            
            # 如果是当前配置，更新内存中的配置
            if is_current:
                self.config_mgr.current_config = config_data
                self._load_from_config()
            
            QtWidgets.QMessageBox.information(dialog, "成功", "配置已保存")
            dialog.accept()
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(dialog, "错误", f"保存配置失败: {e}")
    
    def _edit_current_config(self):
        """编辑当前配置"""
        self._open_config_editor(self.config_mgr.current_config_path.stem)
    
    def _show_new_config_dialog(self):
        """显示新建配置对话框"""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("新建配置")
        dialog.setFixedSize(400, 200)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        
        layout.addWidget(QtWidgets.QLabel("配置名称:"))
        name_entry = QtWidgets.QLineEdit()
        layout.addWidget(name_entry)
        
        button_layout = QtWidgets.QHBoxLayout()
        create_btn = QtWidgets.QPushButton("创建")
        create_btn.clicked.connect(lambda: self._create_new_config(dialog, name_entry))
        button_layout.addWidget(create_btn)
        
        cancel_btn = QtWidgets.QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        dialog.exec_()
    
    def _create_new_config(self, dialog, name_entry):
        name = name_entry.text().strip()
        if not name:
            QtWidgets.QMessageBox.warning(dialog, "错误", "请输入配置名称")
            return
        try:
            config_path = self.config_mgr.create_new_config(name)
            # 新建后打开编辑窗口，但不自动切换当前配置
            self._open_config_editor(name)
            dialog.accept()
        except Exception as e:
            QtWidgets.QMessageBox.critical(dialog, "错误", f"创建配置失败: {e}")
    
    def _show_config_manager(self):
        """显示配置管理窗口"""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("配置管理")
        dialog.setFixedSize(600, 500)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 配置列表
        self.config_tree = QtWidgets.QTreeWidget()
        self.config_tree.setHeaderLabels(["配置名称", "修改时间"])
        self.config_tree.setColumnWidth(0, 200)
        self.config_tree.setColumnWidth(1, 250)
        self.config_tree.setAlternatingRowColors(True)
        self.config_tree.itemDoubleClicked.connect(self._load_selected_config)
        
        layout.addWidget(self.config_tree)
        
        # 刷新列表
        self._refresh_config_list()
        
        # 按钮区域 - 第一行
        button_layout1 = QtWidgets.QHBoxLayout()
        
        load_btn = QtWidgets.QPushButton("加载")
        load_btn.clicked.connect(self._load_selected_config)
        button_layout1.addWidget(load_btn)
        
        edit_btn = QtWidgets.QPushButton("编辑")
        edit_btn.clicked.connect(self._edit_selected_config)
        button_layout1.addWidget(edit_btn)
        
        delete_btn = QtWidgets.QPushButton("删除")
        delete_btn.setObjectName("danger")
        delete_btn.clicked.connect(self._delete_selected_config)
        button_layout1.addWidget(delete_btn)
        
        layout.addLayout(button_layout1)
        
        # 按钮区域 - 第二行（分享码功能）
        button_layout2 = QtWidgets.QHBoxLayout()
        
        export_btn = QtWidgets.QPushButton("导出分享码")
        export_btn.clicked.connect(lambda: self._export_share_code(dialog))
        button_layout2.addWidget(export_btn)
        
        import_btn = QtWidgets.QPushButton("导入分享码")
        import_btn.clicked.connect(lambda: self._import_share_code(dialog))
        button_layout2.addWidget(import_btn)
        
        button_layout2.addStretch()
        
        close_btn = QtWidgets.QPushButton("关闭")
        close_btn.clicked.connect(dialog.reject)
        button_layout2.addWidget(close_btn)
        
        layout.addLayout(button_layout2)
        
        # 说明文字
        info_label = QtWidgets.QLabel("双击配置可快速加载 | 支持删除、编辑和分享码导入导出")
        info_label.setStyleSheet("font-size: 12px; color: #7f8c8d;")
        layout.addWidget(info_label)
        
        dialog.exec_()
    
    def _refresh_config_list(self):
        """刷新配置列表"""
        self.config_tree.clear()
        for config in self.config_mgr.get_config_list():
            item = QtWidgets.QTreeWidgetItem([config["name"], config["modified"]])
            item.setData(0, QtCore.Qt.UserRole, str(config["path"]))
            self.config_tree.addTopLevelItem(item)
    
    def _load_selected_config(self):
        """加载选中的配置"""
        current_item = self.config_tree.currentItem()
        if current_item:
            config_path = current_item.data(0, QtCore.Qt.UserRole)
            if self.config_mgr.load_config(config_path):
                self._load_from_config()
                self.config_name_label.setText(f"配置: {self.config_mgr.current_config_path.stem}")
                QtWidgets.QMessageBox.information(self, "成功", "配置已加载")
                # 关闭对话框
                self.sender().parent().accept() if hasattr(self.sender(), 'parent') else None
            else:
                QtWidgets.QMessageBox.warning(self, "错误", "加载配置失败")
    
    def _edit_selected_config(self):
        """编辑选中的配置"""
        current_item = self.config_tree.currentItem()
        if current_item:
            config_name = current_item.text(0)
            self._open_config_editor(config_name)
    
    def _delete_selected_config(self):
        """删除选中的配置"""
        current_item = self.config_tree.currentItem()
        if current_item:
            config_path = current_item.data(0, QtCore.Qt.UserRole)
            config_name = current_item.text(0)
            
            if config_path == str(self.config_mgr.current_config_path):
                QtWidgets.QMessageBox.warning(self, "错误", "不能删除当前正在使用的配置")
                return
            
            reply = QtWidgets.QMessageBox.question(
                self, "确认", 
                f"确定要删除配置 '{config_name}' 吗？",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            
            if reply == QtWidgets.QMessageBox.Yes:
                if self.config_mgr.delete_config(config_path):
                    self._refresh_config_list()
                    QtWidgets.QMessageBox.information(self, "成功", "配置已删除")
                else:
                    QtWidgets.QMessageBox.warning(self, "错误", "删除失败")
    
    def _export_share_code(self, parent_dialog):
        """导出当前配置为分享码"""
        if not self.config_mgr.current_config:
            QtWidgets.QMessageBox.warning(self, "错误", "没有加载的配置")
            return
        
        share_code = export_config_to_share_code(self.config_mgr, include_name=True)
        if not share_code:
            QtWidgets.QMessageBox.warning(self, "错误", "导出失败")
            return
        
        # 显示分享码对话框
        dialog = QtWidgets.QDialog(parent_dialog)
        dialog.setWindowTitle("导出分享码")
        dialog.setFixedSize(500, 200)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        
        layout.addWidget(QtWidgets.QLabel("分享码（可复制发送给其他玩家）："))
        
        text_edit = QtWidgets.QTextEdit()
        text_edit.setPlainText(share_code)
        text_edit.setReadOnly(True)
        text_edit.setMaximumHeight(80)
        layout.addWidget(text_edit)
        
        button_layout = QtWidgets.QHBoxLayout()
        
        copy_btn = QtWidgets.QPushButton("复制到剪贴板")
        copy_btn.clicked.connect(lambda: QtWidgets.QApplication.clipboard().setText(share_code))
        copy_btn.clicked.connect(lambda: QtWidgets.QMessageBox.information(dialog, "成功", "已复制到剪贴板"))
        button_layout.addWidget(copy_btn)
        
        close_btn = QtWidgets.QPushButton("关闭")
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        dialog.exec_()
    
    def _import_share_code(self, parent_dialog):
        """导入分享码"""
        dialog = QtWidgets.QDialog(parent_dialog)
        dialog.setWindowTitle("导入分享码")
        dialog.setFixedSize(500, 200)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        
        layout.addWidget(QtWidgets.QLabel("粘贴分享码以导入配置 (KS1-... 格式)："))
        
        text_edit = QtWidgets.QTextEdit()
        text_edit.setPlaceholderText("KS1-...")
        text_edit.setMaximumHeight(80)
        layout.addWidget(text_edit)
        
        button_layout = QtWidgets.QHBoxLayout()
        
        import_btn = QtWidgets.QPushButton("导入")
        import_btn.clicked.connect(lambda: self._do_import_share_code(dialog, text_edit.toPlainText()))
        button_layout.addWidget(import_btn)
        
        cancel_btn = QtWidgets.QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        dialog.exec_()
    
    def _do_import_share_code(self, dialog, code):
        """执行导入分享码"""
        success, message = import_config_from_share_code(code, self.config_mgr)
        
        if success:
            QtWidgets.QMessageBox.information(self, "成功", message)
            self._refresh_config_list()
            dialog.accept()
        else:
            QtWidgets.QMessageBox.warning(self, "错误", message)
    
    def _update_stats_display(self, animate=True):
        """更新统计显示（翻页动画）"""
        kdr = self.kills / self.deaths if self.deaths != 0 else self.kills
        wlr = self.wins / self.losses if self.losses != 0 else self.wins

        # 战绩统计页
        self.kills_label.setValue(self.kills, animate)
        self.deaths_label.setValue(self.deaths, animate)
        self.kdr_label.setValue(kdr, animate)
        self.wins_label.setValue(self.wins, animate)
        self.losses_label.setValue(self.losses, animate)
        self.wlr_label.setValue(wlr, animate)
        self.ws_label.setValue(self.win_streak, animate)

        # 主页仪表盘
        self.dash_kills.setValue(self.kills, animate)
        self.dash_deaths.setValue(self.deaths, animate)
        self.dash_kdr.setValue(kdr, animate)
        self.dash_wins.setValue(self.wins, animate)
        self.dash_wlr.setValue(wlr, animate)
        self.dash_ws.setValue(self.win_streak, animate)

        # 更新悬浮统计窗口
        self._update_stats_window_display()
    
    def _toggle_monitoring(self):
        """切换监控状态"""
        if self.is_monitoring:
            self._stop_monitoring()
        else:
            self._start_monitoring()
    
    def _start_monitoring(self):
        """开始监控"""
        # 确保旧的监控线程已完全停止
        if self.is_monitoring:
            self.is_monitoring = False
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=3)

        self.user = self.user_entry.text().strip()
        self.window_name = self.window_combo.currentText().strip()
        self.log_file_path = self.log_file_entry.text().strip()
        
        if not self.user or not self.window_name or not self.log_file_path:
            QtWidgets.QMessageBox.warning(self, "错误", "请填写所有字段并选择日志文件")
            return
        
        # 保存到历史
        self._add_to_history("players", self.user)
        self._add_to_history("paths", self.log_file_path)
        
        log_path = pl.Path(self.log_file_path)
        if not log_path.exists():
            QtWidgets.QMessageBox.warning(self, "错误", "日志文件不存在")
            return
        
        self.kills = 0
        self.deaths = 0
        self.wins = 0
        self.losses = 0
        self.win_streak = 0
        self._update_stats_display()
        
        self.is_monitoring = True
        self.start_btn.setText("停止监控日志")
        self.start_btn.setObjectName("danger")
        self._refresh_style(self.start_btn)
        self._set_status("● 监控日志中", "#27ae60")
        self._start_pulse()
        failed = self._register_autotext_hotkeys()
        
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()

        if failed:
            QtWidgets.QMessageBox.warning(
                self, "提示",
                f"以下快捷消息按键注册失败，可能无法触发：{', '.join(failed)}\n\n"
                "若为权限问题，请尝试以管理员身份运行本程序。"
            )
    
    def _stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False

        # 等待监控线程退出（最多等待 3 秒）
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=3)

        self.start_btn.setText("开始监控")
        self.start_btn.setObjectName("start_btn")
        self._refresh_style(self.start_btn)
        self._set_status("● 已停止", "#95a5a6")
        self._stop_pulse()
        self._unregister_autotext_hotkeys()

        # 询问是否保存当前战绩数据到配置
        self._prompt_save_stats()

    def _prompt_save_stats(self):
        """询问用户是否保存当前战绩数据"""
        # 只有有数据时才询问
        if self.kills == 0 and self.deaths == 0 and self.wins == 0 and self.losses == 0:
            return

        reply = QtWidgets.QMessageBox.question(
            self, "保存数据",
            f"是否将当前战绩数据保存到配置中？\n\n"
            f"击杀: {self.kills}  死亡: {self.deaths}  K/D: {self.kills / self.deaths if self.deaths else self.kills:.2f}\n"
            f"胜利: {self.wins}  失败: {self.losses}  连胜: {self.win_streak}",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes:
            self._save_stats_to_config()

    def _save_stats_to_config(self):
        """保存当前战绩数据到当前配置"""
        try:
            config = self.config_mgr.current_config
            if config is not None:
                config["saved_stats"] = {
                    "kills": self.kills,
                    "deaths": self.deaths,
                    "wins": self.wins,
                    "losses": self.losses,
                    "win_streak": self.win_streak,
                    "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                self.config_mgr.save_current_config()
        except Exception as e:
            print(f"保存战绩数据失败: {e}")

    def _monitoring_loop(self):
        """监控循环（在子线程中运行）"""
        try:
            log_file = pl.Path(self.log_file_path).expanduser().open('rb')
        except Exception as e:
            QtCore.QMetaObject.invokeMethod(self.status_label, "setText", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, f"● 无法打开日志文件: {e}"))
            QtCore.QMetaObject.invokeMethod(self.status_label, "setStyleSheet", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, "color: #e74c3c; font-size: 15px; font-weight: bold;"))
            return

        def tail(file):
            file.seek(0, 2)
            while self.is_monitoring:
                lines = file.readline()
                if not lines:
                    time.sleep(0.1)
                    continue
                yield lines.strip()

        try:
            for log_line in tail(log_file):
                if not self.is_monitoring:
                    break

                # 快照当前配置，防止主线程更改配置导致迭代错误
                kill_patterns = list(self.kill_patterns)
                win_patterns = list(self.win_patterns)
                join_patterns = list(self.join_patterns)
                sniper_list = list(self.sniper_list)
                anti_snipe_messages = list(self.anti_snipe_messages)
                kill_messages = list(self.kill_messages)
                killsay_format = self.killsay_format
                message_prefix = self.message_prefix
                chat_key = self.chat_key

                log_line_de = re.sub(rb'\xac(.?)', b'', log_line).decode('gbk', 'replace')

                if '[CHAT]' in log_line_de:
                    chat_part = log_line_de.split('[CHAT]')[1].strip()
                    self._process_kill(chat_part, kill_patterns, kill_messages, killsay_format, message_prefix, chat_key)
                    self._process_win(chat_part, win_patterns)
                    self._process_anti_snipe(chat_part, join_patterns, sniper_list, anti_snipe_messages)
                elif any(keyword in log_line_de for keyword in ["加入了游戏", "joined the game", "加入游戏"]):
                    self._process_anti_snipe(log_line_de, join_patterns, sniper_list, anti_snipe_messages)
        except Exception as e:
            print(f"监控出错: {e}")
        finally:
            try:
                log_file.close()
            except:
                pass
    
    def _process_kill(self, msg, kill_patterns=None, kill_messages=None, killsay_format=None, message_prefix=None, chat_key=None):
        """处理击杀消息"""
        if kill_patterns is None:
            kill_patterns = self.kill_patterns
        if kill_messages is None:
            kill_messages = self.kill_messages
        if killsay_format is None:
            killsay_format = self.killsay_format
        if message_prefix is None:
            message_prefix = self.message_prefix
        if chat_key is None:
            chat_key = self.chat_key

        for pattern in kill_patterns:
            regex_pattern = self._convert_kill_pattern(pattern)
            match = re.search(regex_pattern, msg)
            if match:
                d = match.group('obj').strip()
                k = match.group('user').strip()

                # 比对时忽略特殊符号，如 ★Player2 == Player2
                clean_k = re.sub(r'[^\w一-鿿]', '', k)
                clean_d = re.sub(r'[^\w一-鿿]', '', d)
                clean_user = re.sub(r'[^\w一-鿿]', '', self.user)

                if clean_k == clean_user:
                    if self.stats_enabled:
                        self.kills += 1
                    if self.killsay_enabled:
                        raw_message = self._get_random_kill_message(kill_messages)
                        formatted_message = self._format_kill_message(raw_message, k, d)
                        send_msg = self._build_killsay_message(formatted_message, k, d, killsay_format, message_prefix)
                        self._send_chat(send_msg, chat_key)
                    if self.stats_enabled:
                        QtCore.QTimer.singleShot(0, self._update_stats_display)

                if clean_d == clean_user:
                    if self.stats_enabled:
                        self.deaths += 1
                        self.losses += 1
                        self.win_streak = 0
                        QtCore.QTimer.singleShot(0, self._update_stats_display)
                break
    
    def _process_anti_snipe(self, msg, join_patterns=None, sniper_list=None, anti_snipe_messages=None):
        """处理反狙击检测"""
        if join_patterns is None:
            join_patterns = self.join_patterns
        if sniper_list is None:
            sniper_list = self.sniper_list
        if anti_snipe_messages is None:
            anti_snipe_messages = self.anti_snipe_messages

        for pattern in join_patterns:
            regex_pattern = self._convert_join_pattern(pattern)
            match = re.search(regex_pattern, msg)
            if match:
                player_name = match.group('name').strip()
                # 清理特殊符号再比对
                clean_name = re.sub(r'[^\w一-鿿]', '', player_name)
                if self.anti_snipe_enabled:
                    if clean_name in [re.sub(r'[^\w一-鿿]', '', s) for s in sniper_list]:
                        for snipe_msg in anti_snipe_messages:
                            self._send_chat(snipe_msg)
                        break
                    for sniper in sniper_list:
                        clean_sniper = re.sub(r'[^\w一-鿿]', '', sniper)
                        if clean_sniper in clean_name or clean_name in clean_sniper:
                            for snipe_msg in anti_snipe_messages:
                                self._send_chat(snipe_msg)
                            break
                break

    def _convert_join_pattern(self, pattern):
        """转换加入检测模式，%t 为玩家名占位符"""
        parts = re.split(r'(%t)', pattern)
        regex = ''
        for part in parts:
            if part == '%t':
                regex += '(?P<name>.+?)'
            elif part:
                chars = list(part)
                regex += '.*?'.join(re.escape(c) for c in chars)
        return regex
    
    def _convert_kill_pattern(self, pattern):
        """转换击杀模式为正则表达式

        占位符之间和文字字符之间都用 .*? 连接，
        允许中间出现任意特殊符号。
        """
        parts = re.split(r'(%[oun])', pattern)
        regex = ''
        for part in parts:
            if part == '%o':
                regex += '(?P<obj>.+?)'
            elif part == '%u':
                regex += '(?P<user>.+?)'
            elif part == '%n':
                regex += r'(?P<num>\d+)'
            elif part:
                regex += '.*?'.join(re.escape(c) for c in part)
        return regex

    def _convert_win_pattern(self, pattern):
        """转换胜利检测模式，%p=玩家名，%m=任意字符（地图名等）"""
        parts = re.split(r'(%[pm])', pattern)
        regex = ''
        for part in parts:
            if part == '%p':
                # 只匹配用户名字符（字母数字下划线+中文），遇到空格/标点就停止
                regex += '(?P<player>[\\w一-鿿]+)'
            elif part == '%m':
                regex += '(?:.*?)'
            elif part:
                chars = list(part)
                regex += '.*?'.join(re.escape(c) for c in chars)
        return regex

    def _process_win(self, msg, win_patterns=None):
        """处理胜利检测"""
        if win_patterns is None:
            win_patterns = self.win_patterns
        for pattern in win_patterns:
            regex_pattern = self._convert_win_pattern(pattern)
            match = re.search(regex_pattern, msg)
            if match:
                player_name = match.group('player').strip()
                clean_player = re.sub(r'[^\w一-鿿]', '', player_name)
                clean_user = re.sub(r'[^\w一-鿿]', '', self.user)
                if clean_player == clean_user:
                    if self.stats_enabled:
                        self.wins += 1
                        self.win_streak += 1
                        QtCore.QTimer.singleShot(0, self._update_stats_display)
                    if self.autogg_enabled:
                        # 胜利时自动发送 GG
                        self._send_chat("GG")
                break

    def _format_kill_message(self, message, killer, killed):
        """格式化击杀消息"""
        formatted = message
        if "%u" in formatted:
            formatted = formatted.replace("%u", killer)
        if "%o" in formatted:
            formatted = formatted.replace("%o", killed)
        return formatted
    
    def _build_killsay_message(self, formatted_message, killer, killed, killsay_format=None, message_prefix=None):
        """根据前缀和格式构建最终发送消息"""
        if killsay_format is None:
            killsay_format = self.killsay_format
        if message_prefix is None:
            message_prefix = self.message_prefix
        result = killsay_format or ConfigManager.DEFAULT_CONFIG["killsay_format"]
        result = result.replace("%t", message_prefix or "")
        result = result.replace("%m", formatted_message)
        result = result.replace("%u", killer)
        result = result.replace("%o", killed)
        result = result.replace("%c", str(self.kills))
        return result.strip()
    
    def _get_random_kill_message(self, kill_messages=None):
        """获取随机击杀消息"""
        if kill_messages is None:
            kill_messages = self.kill_messages
        if len(kill_messages) <= 5:
            return random.choice(kill_messages)

        if len(self.index_q) >= len(kill_messages):
            self.index_q.clear()

        for _ in range(50):
            rindex = random.randint(0, len(kill_messages) - 1)
            if rindex not in self.index_q:
                self.index_q.append(rindex)
                return kill_messages[rindex]

        self.index_q.clear()
        rindex = random.randint(0, len(kill_messages) - 1)
        self.index_q.append(rindex)
        return kill_messages[rindex]
    
    def _send_chat(self, msg, chat_key=None):
        """发送聊天消息"""
        try:
            windows = pygetwindow.getWindowsWithTitle(self.window_name)
            if windows:
                bjd_window = windows[0]
                key = chat_key or self.chat_key or 't'
                keyboard.send(key)
                time.sleep(0.05)
                keyboard.write(msg)
                time.sleep(0.05)
                keyboard.send('enter')
                # self.message_signal.emit(f"已发送消息: {msg}")
                print(f"已发送消息: {msg}")
            else:
                # self.message_signal.emit(f"未找到窗口: {self.window_name}")
                print(f"未找到窗口: {self.window_name}")
        except Exception as e:
            # self.message_signal.emit(f"发送消息失败: {e}")
            print(f"发送消息失败: {e}")
    
    def _populate_theme_combo(self):
        """填充主题选择下拉框"""
        self.theme_combo.clear()
        for theme_key in self.theme_mgr.get_theme_names():
            theme_info = self.theme_mgr.get_theme_info(theme_key)
            self.theme_combo.addItem(theme_info["name"], theme_key)
        
        # 设置当前主题
        current_theme = self.theme_mgr.current_theme
        index = self.theme_combo.findData(current_theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
            # 显示当前主题描述（如果存在）
            try:
                info = self.theme_mgr.get_theme_info(current_theme)
                desc = info.get("description", "") if isinstance(info, dict) else ""
                if hasattr(self, 'theme_desc_label'):
                    self.theme_desc_label.setText(desc)
            except:
                pass
    
    def _change_theme(self, index):
        """更改主题"""
        if index is None or index < 0:
            return
        theme_key = self.theme_combo.itemData(index)
        if theme_key and self.theme_mgr.set_theme(theme_key):
            theme_name = self.theme_combo.currentText()
            self._setup_styles()
            # 更新描述显示
            try:
                info = self.theme_mgr.get_theme_info(theme_key)
                desc = info.get("description", "") if isinstance(info, dict) else ""
                if hasattr(self, 'theme_desc_label'):
                    self.theme_desc_label.setText(desc)
            except:
                pass
            QtWidgets.QMessageBox.information(self, "成功", f"已切换到主题: {theme_name}")
        elif theme_key:
            QtWidgets.QMessageBox.warning(self, "错误", "切换主题失败")
    
    def _show_custom_theme_dialog(self):
        """显示自定义主题对话框（点色块直接选主题色，自动生成配色 + 实时预览）"""
        dialog = QtWidgets.QDialog(self)
        current_theme_key = self.theme_mgr.current_theme if self.theme_mgr.is_custom_theme(self.theme_mgr.current_theme) else None
        dialog.setWindowTitle("编辑自定义主题" if current_theme_key else "创建自定义主题")
        dialog.setFixedSize(520, 480)

        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # 主题名称
        name_row = QtWidgets.QHBoxLayout()
        name_row.addWidget(QtWidgets.QLabel("主题名称:"))
        self.theme_name_edit = QtWidgets.QLineEdit()
        name_row.addWidget(self.theme_name_edit)
        layout.addLayout(name_row)

        # 初始颜色
        if current_theme_key:
            current_theme = self.theme_mgr.get_theme_info(current_theme_key)
            self.theme_name_edit.setText(current_theme.get("name", ""))
            default_color = current_theme.get("colors", {}).get("accent_primary", "#3498db")
        else:
            default_color = "#3498db"

        # 主题色：点击色块直接选色
        color_row = QtWidgets.QHBoxLayout()
        color_row.addWidget(QtWidgets.QLabel("主题色:"))
        self.theme_color_edit = QtWidgets.QLineEdit(default_color)
        self.theme_color_edit.setReadOnly(True)
        self.theme_color_edit.setMaximumWidth(110)
        color_row.addWidget(self.theme_color_edit)

        self.theme_color_swatch = QtWidgets.QPushButton()
        self.theme_color_swatch.setFixedSize(44, 30)
        self.theme_color_swatch.setCursor(QtCore.Qt.PointingHandCursor)
        self.theme_color_swatch.setToolTip("点击选择主题色")
        self.theme_color_swatch.clicked.connect(lambda: self._pick_theme_color(dialog))
        color_row.addWidget(self.theme_color_swatch)
        color_row.addStretch()
        layout.addLayout(color_row)

        # 实时预览
        layout.addWidget(QtWidgets.QLabel("实时预览:"))
        self.theme_preview = QtWidgets.QFrame()
        self.theme_preview.setObjectName("theme_preview")
        self.theme_preview.setFixedHeight(150)
        preview_layout = QtWidgets.QVBoxLayout(self.theme_preview)
        preview_layout.setContentsMargins(16, 14, 16, 14)
        preview_layout.setSpacing(8)
        self.preview_title = QtWidgets.QLabel("标题示例")
        self.preview_title.setObjectName("preview_title")
        preview_layout.addWidget(self.preview_title)
        self.preview_btn = QtWidgets.QPushButton("按钮示例")
        self.preview_btn.setObjectName("preview_btn")
        self.preview_btn.setFixedHeight(34)
        preview_layout.addWidget(self.preview_btn)
        self.preview_text = QtWidgets.QLabel("这是正文文字示例，用于预览正文与次要文字的颜色。")
        self.preview_text.setObjectName("preview_text")
        self.preview_text.setWordWrap(True)
        preview_layout.addWidget(self.preview_text)
        preview_layout.addStretch()
        layout.addWidget(self.theme_preview)

        self._apply_theme_preview(default_color)

        # 按钮区域
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        save_btn = QtWidgets.QPushButton("保存主题")
        save_btn.clicked.connect(lambda: self._save_custom_theme(dialog, current_theme_key))
        button_layout.addWidget(save_btn)
        cancel_btn = QtWidgets.QPushButton("取消")
        cancel_btn.setObjectName("secondary")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        dialog.exec_()

    def _pick_theme_color(self, parent):
        """弹出颜色选择器，选完后更新色块与预览"""
        current = QtGui.QColor(self.theme_color_edit.text().strip())
        color = QtWidgets.QColorDialog.getColor(current if current.isValid() else QtGui.QColor("#3498db"), parent, "选择主题色")
        if color.isValid():
            self.theme_color_edit.setText(color.name())
            self._apply_theme_preview(color.name())

    def _apply_theme_preview(self, accent):
        """根据主题色渲染色块与预览面板"""
        self.theme_color_swatch.setStyleSheet(f"background-color: {accent}; border: 1px solid #888888; border-radius: 4px;")
        colors = self.theme_mgr.generate_palette_from_primary(accent)
        self.theme_preview.setStyleSheet(
            f"QFrame#theme_preview {{ background-color: {colors['bg_primary']}; border: 1px solid {colors['bg_tertiary']}; border-radius: 8px; }}"
            f"QPushButton#preview_btn {{ background-color: {colors['accent_primary']}; color: {colors['text_primary']}; border: none; border-radius: 6px; font-weight: bold; }}"
            f"QLabel#preview_title {{ color: {colors['text_primary']}; font-size: 15px; font-weight: bold; background: transparent; }}"
            f"QLabel#preview_text {{ color: {colors['text_secondary']}; font-size: 12px; background: transparent; }}"
        )
    
    
    def _save_custom_theme(self, dialog, theme_key=None):
        """保存自定义主题"""
        theme_name = self.theme_name_edit.text().strip()
        # 编辑已有主题时保留原描述，新建时描述为空
        if theme_key and self.theme_mgr.is_custom_theme(theme_key):
            theme_desc = self.theme_mgr.get_theme_info(theme_key).get("description", "")
        else:
            theme_desc = ""
        accent_primary = self.theme_color_edit.text().strip()

        if not theme_name:
            QtWidgets.QMessageBox.warning(dialog, "错误", "请输入主题名称")
            return

        if not accent_primary.startswith("#") or len(accent_primary) != 7:
            QtWidgets.QMessageBox.warning(dialog, "错误", "请输入有效的主题色")
            return

        colors = self.theme_mgr.generate_palette_from_primary(accent_primary)

        try:
            if theme_key and self.theme_mgr.is_custom_theme(theme_key):
                self.theme_mgr.update_custom_theme(theme_key, theme_name, theme_desc, colors)
                result_msg = f"自定义主题 '{theme_name}' 已更新并应用"
            else:
                theme_key = self.theme_mgr.create_custom_theme(theme_name, theme_desc, colors)
                result_msg = f"自定义主题 '{theme_name}' 已创建并应用"

            # 刷新主题选择器
            self._populate_theme_combo()

            # 切换并应用主题
            self.theme_mgr.set_theme(theme_key)
            self._setup_styles()

            QtWidgets.QMessageBox.information(dialog, "成功", result_msg)
            dialog.accept()

        except Exception as e:
            QtWidgets.QMessageBox.critical(dialog, "错误", f"保存主题失败: {e}")
    
    def closeEvent(self, event):
        """窗口关闭时的处理"""
        self.is_monitoring = False
        self._unregister_autotext_hotkeys()
        event.accept()
    
    def run(self):
        """运行应用程序"""
        self.show()
