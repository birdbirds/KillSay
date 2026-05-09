import os
import sys
import random
import re
import time
import pathlib as pl
import pygetwindow
import keyboard
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

# ==================== 主应用程序 ====================
class KillSayApp(QtWidgets.QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("KILLSAY-击杀喊话")
        self.setGeometry(100, 100, 1200, 750)
        self.setFixedSize(1200, 750)
        
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
        self.is_monitoring = False
        self.monitoring_thread = None
        self.anti_snipe_enabled = False
        self.index_q = deque(maxlen=5)
        
        # 历史记录
        self.history_file = pl.Path(get_base_dir()) / "history.json"
        self.history = self._load_history()
        
        # 从配置加载数据
        self._load_from_config()
        
        # 动画对象
        self.kills_anim = None
        self.deaths_anim = None
        self.kdr_anim = None
        self.pulse_effect = None
        
        # 设置样式
        self._setup_styles()
        
        # 构建界面
        self._build_ui()
    
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
    
    def _setup_styles(self):
        """设置现代化样式"""
        self.setStyleSheet(self.theme_mgr.generate_stylesheet())
    
    def _build_ui(self):
        """构建用户界面"""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 头部区域
        header_layout = QtWidgets.QVBoxLayout()
        title_label = QtWidgets.QLabel("KILLSAY")
        title_label.setObjectName("title")
        header_layout.addWidget(title_label)
        
        subtitle_label = QtWidgets.QLabel("Minecraft 击杀喊话 | 多配置管理")
        subtitle_label.setObjectName("subtitle")
        header_layout.addWidget(subtitle_label)
        
        main_layout.addLayout(header_layout)
        
        # 配置信息栏
        config_layout = QtWidgets.QHBoxLayout()
        self.config_name_label = QtWidgets.QLabel(f"当前配置: {self.config_mgr.current_config_path.stem}")
        self.config_name_label.setStyleSheet("color: #3498db;")
        config_layout.addWidget(self.config_name_label)
        
        config_layout.addStretch()
        
        # 配置管理按钮
        edit_config_btn = QtWidgets.QPushButton("编辑配置")
        edit_config_btn.setObjectName("secondary")
        edit_config_btn.clicked.connect(self._edit_current_config)
        config_layout.addWidget(edit_config_btn)
        
        new_config_btn = QtWidgets.QPushButton("新建配置")
        new_config_btn.setObjectName("secondary")
        new_config_btn.clicked.connect(self._show_new_config_dialog)
        config_layout.addWidget(new_config_btn)
        
        manage_config_btn = QtWidgets.QPushButton("配置管理")
        manage_config_btn.setObjectName("secondary")
        manage_config_btn.clicked.connect(self._show_config_manager)
        config_layout.addWidget(manage_config_btn)
        
        # 主题选择器
        theme_layout = QtWidgets.QHBoxLayout()
        theme_layout.addWidget(QtWidgets.QLabel("主题:"))
        self.theme_combo = QtWidgets.QComboBox()
        self._populate_theme_combo()
        self.theme_combo.currentIndexChanged.connect(self._change_theme)
        theme_layout.addWidget(self.theme_combo)
        
        # 自定义主题按钮
        custom_theme_btn = QtWidgets.QPushButton("自定义主题")
        custom_theme_btn.setObjectName("secondary")
        custom_theme_btn.clicked.connect(self._show_custom_theme_dialog)
        theme_layout.addWidget(custom_theme_btn)
        
        config_layout.addLayout(theme_layout)
        
        main_layout.addLayout(config_layout)
        
        # 输入区域
        input_group = QtWidgets.QGroupBox("基本设置")
        input_layout = QtWidgets.QVBoxLayout(input_group)
        input_layout.setSpacing(8)
        
        # 用户名
        user_layout = QtWidgets.QHBoxLayout()
        user_layout.addWidget(QtWidgets.QLabel("游戏名称:"))
        self.user_entry = QtWidgets.QLineEdit()
        user_layout.addWidget(self.user_entry)
        user_history_btn = QtWidgets.QPushButton("历史")
        user_history_btn.setObjectName("secondary")
        user_history_btn.clicked.connect(lambda: self._show_history_dialog("players", self.user_entry))
        user_layout.addWidget(user_history_btn)
        save_history_btn = QtWidgets.QPushButton("保存")
        save_history_btn.setObjectName("secondary")
        save_history_btn.clicked.connect(self._save_to_history)
        user_layout.addWidget(save_history_btn)
        input_layout.addLayout(user_layout)
        
        # 窗口名称
        window_layout = QtWidgets.QHBoxLayout()
        window_layout.addWidget(QtWidgets.QLabel("窗口名称:"))
        self.window_entry = QtWidgets.QLineEdit()
        self.window_entry.setText("布吉岛")
        window_layout.addWidget(self.window_entry)
        input_layout.addLayout(window_layout)
        
        # 日志文件
        file_layout = QtWidgets.QHBoxLayout()
        file_layout.addWidget(QtWidgets.QLabel("日志文件:"))
        self.log_file_entry = QtWidgets.QLineEdit()
        self.log_file_entry.setText("D:\\MCLDownload\\Game\\.minecraft\\logs\\latest.log")
        file_layout.addWidget(self.log_file_entry)
        browse_btn = QtWidgets.QPushButton("浏览")
        browse_btn.setObjectName("secondary")
        browse_btn.clicked.connect(self._select_log_file)
        file_layout.addWidget(browse_btn)
        file_history_btn = QtWidgets.QPushButton("历史")
        file_history_btn.setObjectName("secondary")
        file_history_btn.clicked.connect(lambda: self._show_history_dialog("paths", self.log_file_entry))
        file_layout.addWidget(file_history_btn)
        input_layout.addLayout(file_layout)
        
        main_layout.addWidget(input_group)
        
        # 反狙击区域
        anti_snipe_layout = QtWidgets.QVBoxLayout()
        self.anti_snipe_btn = QtWidgets.QPushButton("反狙击: OFF")
        self.anti_snipe_btn.setObjectName("secondary")
        self.anti_snipe_btn.clicked.connect(self._toggle_anti_snipe)
        anti_snipe_layout.addWidget(self.anti_snipe_btn)
        
        self.anti_snipe_status = QtWidgets.QLabel("反狙击功能已关闭")
        self.anti_snipe_status.setStyleSheet("font-size: 9pt;")
        anti_snipe_layout.addWidget(self.anti_snipe_status)
        
        main_layout.addLayout(anti_snipe_layout)
        
        # 统计区域
        stats_group = QtWidgets.QGroupBox("战绩统计")
        stats_layout = QtWidgets.QHBoxLayout(stats_group)
        
        # 击杀显示
        kills_layout = QtWidgets.QVBoxLayout()
        kills_layout.addWidget(QtWidgets.QLabel("击杀"))
        self.kills_label = QtWidgets.QLabel("0")
        self.kills_label.setObjectName("stats")
        kills_layout.addWidget(self.kills_label)
        stats_layout.addLayout(kills_layout)
        
        # 死亡显示
        deaths_layout = QtWidgets.QVBoxLayout()
        deaths_layout.addWidget(QtWidgets.QLabel("死亡"))
        self.deaths_label = QtWidgets.QLabel("0")
        self.deaths_label.setObjectName("stats")
        deaths_layout.addWidget(self.deaths_label)
        stats_layout.addLayout(deaths_layout)
        
        # KDR显示
        kdr_layout = QtWidgets.QVBoxLayout()
        kdr_layout.addWidget(QtWidgets.QLabel("K/D"))
        self.kdr_label = QtWidgets.QLabel("0")
        self.kdr_label.setObjectName("stats")
        kdr_layout.addWidget(self.kdr_label)
        stats_layout.addLayout(kdr_layout)
        
        # 显示统计窗口按钮
        show_stats_btn = QtWidgets.QPushButton("显示统计窗口")
        show_stats_btn.setObjectName("secondary")
        show_stats_btn.clicked.connect(self._show_stats_window)
        stats_layout.addWidget(show_stats_btn)
        
        main_layout.addWidget(stats_group)
        
        # 初始化动画对象
        self._init_animations()
        
        # 监控按钮
        self.start_btn = QtWidgets.QPushButton("开始监控")
        self.start_btn.clicked.connect(self._toggle_monitoring)
        main_layout.addWidget(self.start_btn, alignment=QtCore.Qt.AlignCenter)
        
        # 状态区域
        self.status_label = QtWidgets.QLabel("● 就绪")
        self.status_label.setObjectName("status")
        self.status_label.setStyleSheet("color: #95a5a6;")
        main_layout.addWidget(self.status_label, alignment=QtCore.Qt.AlignCenter)
        
        # 提示信息
        info_label = QtWidgets.QLabel("提示: 确保游戏窗口处于活动状态，脚本将自动发送击杀喊话")
        info_label.setStyleSheet("font-size: 8pt; color: #7f8c8d;")
        main_layout.addWidget(info_label, alignment=QtCore.Qt.AlignCenter)
        
        # 脉冲效果（暂时跳过）
    
    def _init_animations(self):
        """初始化动画对象"""
        # 为统计标签添加数字动画属性
        self.kills_label.setProperty("value", 0)
        self.deaths_label.setProperty("value", 0)
        self.kdr_label.setProperty("value", 0.0)
        
        # 创建动画
        self.kills_anim = QtCore.QVariantAnimation()
        self.kills_anim.setDuration(500)
        self.kills_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self.kills_anim.valueChanged.connect(lambda value: self.kills_label.setText(str(int(value))))
        
        self.deaths_anim = QtCore.QVariantAnimation()
        self.deaths_anim.setDuration(500)
        self.deaths_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self.deaths_anim.valueChanged.connect(lambda value: self.deaths_label.setText(str(int(value))))
        
        self.kdr_anim = QtCore.QVariantAnimation()
        self.kdr_anim.setDuration(500)
        self.kdr_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self.kdr_anim.valueChanged.connect(lambda value: self.kdr_label.setText(f"{float(value):.2f}"))
    
    def _update_label_text(self, label, value):
        """更新标签文本"""
        if label == self.kdr_label:
            label.setText(f"{value:.2f}")
        else:
            label.setText(str(value))
    
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
        """显示统计窗口"""
        if hasattr(self, 'stats_window') and self.stats_window.isVisible():
            self.stats_window.raise_()
            return
        
        self.stats_window = QtWidgets.QWidget()
        self.stats_window.setWindowTitle("KILLSAY - 统计")
        self.stats_window.setFixedSize(200, 150)
        self.stats_window.setWindowFlags(self.stats_window.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        
        layout = QtWidgets.QVBoxLayout(self.stats_window)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 击杀
        kills_layout = QtWidgets.QHBoxLayout()
        kills_layout.addWidget(QtWidgets.QLabel("击杀:"))
        self.stats_kills_label = QtWidgets.QLabel("0")
        self.stats_kills_label.setObjectName("stats")
        kills_layout.addWidget(self.stats_kills_label)
        layout.addLayout(kills_layout)
        
        # 死亡
        deaths_layout = QtWidgets.QHBoxLayout()
        deaths_layout.addWidget(QtWidgets.QLabel("死亡:"))
        self.stats_deaths_label = QtWidgets.QLabel("0")
        self.stats_deaths_label.setObjectName("stats")
        deaths_layout.addWidget(self.stats_deaths_label)
        layout.addLayout(deaths_layout)
        
        # K/D
        kdr_layout = QtWidgets.QHBoxLayout()
        kdr_layout.addWidget(QtWidgets.QLabel("K/D:"))
        self.stats_kdr_label = QtWidgets.QLabel("0")
        self.stats_kdr_label.setObjectName("stats")
        kdr_layout.addWidget(self.stats_kdr_label)
        layout.addLayout(kdr_layout)
        
        # 初始化动画
        self.stats_kills_anim = QtCore.QVariantAnimation()
        self.stats_kills_anim.setDuration(500)
        self.stats_kills_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self.stats_kills_anim.valueChanged.connect(lambda value: self.stats_kills_label.setText(str(int(value))))
        
        self.stats_deaths_anim = QtCore.QVariantAnimation()
        self.stats_deaths_anim.setDuration(500)
        self.stats_deaths_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self.stats_deaths_anim.valueChanged.connect(lambda value: self.stats_deaths_label.setText(str(int(value))))
        
        self.stats_kdr_anim = QtCore.QVariantAnimation()
        self.stats_kdr_anim.setDuration(500)
        self.stats_kdr_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self.stats_kdr_anim.valueChanged.connect(lambda value: self.stats_kdr_label.setText(f"{float(value):.2f}"))
        
        # 更新显示
        self._update_stats_window_display()
        
        self.stats_window.show()
    
    def _update_stats_window_display(self):
        """更新统计窗口显示"""
        if not hasattr(self, 'stats_window'):
            return
        
        kdr = self.kills / self.deaths if self.deaths != 0 else self.kills

        self.stats_kills_anim.setStartValue(int(self.stats_kills_label.text() or 0))
        self.stats_kills_anim.setEndValue(self.kills)
        self.stats_kills_anim.start()

        self.stats_deaths_anim.setStartValue(int(self.stats_deaths_label.text() or 0))
        self.stats_deaths_anim.setEndValue(self.deaths)
        self.stats_deaths_anim.start()

        self.stats_kdr_anim.setStartValue(float(self.stats_kdr_label.text() or 0.0))
        self.stats_kdr_anim.setEndValue(kdr)
        self.stats_kdr_anim.start()
    
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
            self.anti_snipe_btn.setStyleSheet(self.anti_snipe_btn.styleSheet())  # 刷新样式
            self.anti_snipe_status.setText("反狙击功能已启用")
            self.anti_snipe_status.setStyleSheet("color: #27ae60;")
        else:
            self.anti_snipe_btn.setText("反狙击: OFF")
            self.anti_snipe_btn.setObjectName("secondary")
            self.anti_snipe_btn.setStyleSheet(self.anti_snipe_btn.styleSheet())  # 刷新样式
            self.anti_snipe_status.setText("反狙击功能已关闭")
            self.anti_snipe_status.setStyleSheet("color: #ecf0f1;")
    
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
        pattern_help.setStyleSheet("font-size: 8pt; color: #bdc3c7;")
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
        help_label.setStyleSheet("font-size: 8pt; color: #bdc3c7;")
        kill_pattern_layout.addWidget(help_label)
        tab_widget.addTab(kill_pattern_tab, "击杀检测模式")
        
        # 击杀消息标签页
        kill_msg_tab = QtWidgets.QWidget()
        kill_msg_layout = QtWidgets.QVBoxLayout(kill_msg_tab)
        kill_msg_layout.addWidget(QtWidgets.QLabel("击杀后发送的消息 (每行一个，可使用 %u 和 %o 占位符):"))
        self.kill_msg_text = QtWidgets.QTextEdit()
        self.kill_msg_text.setPlainText("\n".join(edit_config.get("kill_messages", [])))
        kill_msg_layout.addWidget(self.kill_msg_text)
        
        help_label2 = QtWidgets.QLabel("提示: %u=用户(击杀者), %o=对象(被击杀者)\n如果没有占位符，则发送原消息。")
        help_label2.setStyleSheet("font-size: 8pt; color: #bdc3c7;")
        kill_msg_layout.addWidget(help_label2)
        tab_widget.addTab(kill_msg_tab, "击杀消息")
        
        # 消息前缀与格式设置标签页
        format_tab = QtWidgets.QWidget()
        format_layout = QtWidgets.QFormLayout(format_tab)
        self.prefix_edit = QtWidgets.QLineEdit(edit_config.get("message_prefix", ""))
        format_layout.addRow("消息前缀:", self.prefix_edit)
        self.format_edit = QtWidgets.QLineEdit(edit_config.get("killsay_format", ConfigManager.DEFAULT_CONFIG["killsay_format"]))
        format_layout.addRow("Killsay 格式:", self.format_edit)
        format_help = QtWidgets.QLabel("支持占位符:\n%t - 前缀\n%m - 击杀消息内容\n%u - 用户(击杀者名称)\n%o - 对象(被击杀者名称)\n%c - 当前击杀数\n示例: %t%m | 当前击杀数：%c")
        format_help.setStyleSheet("font-size: 8pt; color: #bdc3c7;")
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
            prefix = self.prefix_edit.text().strip()
            killsay_format = self.format_edit.text().strip() or ConfigManager.DEFAULT_CONFIG["killsay_format"]
            
            # 构建配置数据
            config_data = {
                "sniper_list": sniper_list,
                "join_patterns": join_patterns,
                "anti_snipe_messages": anti_snipe_messages,
                "kill_patterns": kill_patterns,
                "kill_messages": kill_messages,
                "message_prefix": prefix,
                "killsay_format": killsay_format
            }
            
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
        info_label = QtWidgets.QLabel("双击配置可快速加载 | 分享码格式: KS1-... (兼容 Rust 版本)")
        info_label.setStyleSheet("font-size: 9pt; color: #7f8c8d;")
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
                self.config_name_label.setText(f"当前配置: {self.config_mgr.current_config_path.stem}")
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
        
        layout.addWidget(QtWidgets.QLabel("粘贴分享码（KS1-...格式，兼容 Rust 版本）："))
        
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
    
    def _update_stats_display(self):
        """更新统计显示"""
        kdr = self.kills / self.deaths if self.deaths != 0 else self.kills

        self.kills_anim.setStartValue(int(self.kills_label.text() or 0))
        self.kills_anim.setEndValue(self.kills)
        self.kills_anim.start()

        self.deaths_anim.setStartValue(int(self.deaths_label.text() or 0))
        self.deaths_anim.setEndValue(self.deaths)
        self.deaths_anim.start()

        self.kdr_anim.setStartValue(float(self.kdr_label.text() or 0.0))
        self.kdr_anim.setEndValue(kdr)
        self.kdr_anim.start()
        
        # 更新统计窗口
        self._update_stats_window_display()
    
    def _toggle_monitoring(self):
        """切换监控状态"""
        if self.is_monitoring:
            self._stop_monitoring()
        else:
            self._start_monitoring()
    
    def _start_monitoring(self):
        """开始监控"""
        self.user = self.user_entry.text().strip()
        self.window_name = self.window_entry.text().strip()
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
        self._update_stats_display()
        
        self.is_monitoring = True
        self.start_btn.setText("停止监控")
        self.start_btn.setObjectName("danger")
        self.start_btn.setStyleSheet(self.start_btn.styleSheet())  # 刷新样式
        self.status_label.setText("● 监控中...")
        self.status_label.setStyleSheet("color: #032921;")
        # self.message_signal.emit("已开始监控日志文件")
        # 脉冲效果暂时跳过
        
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
    
    def _stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False
        self.start_btn.setText("开始监控")
        self.start_btn.setObjectName("")  # 默认样式
        self.start_btn.setStyleSheet(self.start_btn.styleSheet())  # 刷新样式
        self.status_label.setText("● 已停止")
        self.status_label.setStyleSheet("color: #95a5a6;")
        # self.message_signal.emit("已停止监控")
        # self.pulse_effect.stop()
    
    def _monitoring_loop(self):
        """监控循环（在子线程中运行）"""
        try:
            log_file = pl.Path(self.log_file_path).expanduser().open('rb')
        except Exception as e:
            # self.message_signal.emit(f"无法打开日志文件: {e}")
            QtCore.QMetaObject.invokeMethod(self.status_label, "setText", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, f"● 无法打开日志文件: {e}"))
            QtCore.QMetaObject.invokeMethod(self.status_label, "setStyleSheet", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, "color: #e74c3c;"))
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
                
                log_line_de = re.sub(rb'\xac(.?)', b'', log_line).decode('gbk', 'replace')
                
                if '[CHAT]' in log_line_de:
                    chat_part = log_line_de.split('[CHAT]')[1].strip()
                    self._process_kill(chat_part)
                    self._process_anti_snipe(chat_part)
                elif any(keyword in log_line_de for keyword in ["加入了游戏", "joined the game", "加入游戏"]):
                    self._process_anti_snipe(log_line_de)
        except Exception as e:
            print(f"监控出错: {e}")
        finally:
            try:
                log_file.close()
            except:
                pass
    
    def _process_kill(self, msg):
        """处理击杀消息"""
        for pattern in self.kill_patterns:
            regex_pattern = self._convert_kill_pattern(pattern)
            match = re.search(regex_pattern, msg)
            if match:
                data = match.groups()
                if len(data) >= 2:
                    d_index = pattern.find("%o")
                    k_index = pattern.find("%u")
                    
                    if d_index < k_index:
                        d, k = data[0], data[1]
                    else:
                        k, d = data[0], data[1]
                    
                    d = d.strip()
                    k = k.strip()
                    
                    if k == self.user:
                        self.kills += 1
                        raw_message = self._get_random_kill_message()
                        formatted_message = self._format_kill_message(raw_message, k, d)
                        send_msg = self._build_killsay_message(formatted_message, k, d)
                        self._send_chat(send_msg)
                        QtCore.QTimer.singleShot(0, self._update_stats_display)
                    
                    if d == self.user:
                        self.deaths += 1
                        QtCore.QTimer.singleShot(0, self._update_stats_display)
                    break
    
    def _process_anti_snipe(self, msg):
        """处理反狙击检测"""
        for pattern in self.join_patterns:
            # 将 %t 转换为正则表达式捕获组
            regex_pattern = re.escape(pattern).replace(r'%t', '(.*?)')
            match = re.search(regex_pattern, msg)
            if match:
                player_name = match.group(1).strip()
                if self.anti_snipe_enabled:
                    if player_name in self.sniper_list:
                        # self.message_signal.emit(f"检测到狙击手加入：{player_name}")
                        for snipe_msg in self.anti_snipe_messages:
                            self._send_chat(snipe_msg)
                        break
                    for sniper in self.sniper_list:
                        if sniper in player_name or player_name in sniper:
                            # self.message_signal.emit(f"检测到疑似狙击手加入：{player_name}")
                            for snipe_msg in self.anti_snipe_messages:
                                self._send_chat(snipe_msg)
                            break
                break
    
    def _convert_kill_pattern(self, pattern):
        """转换击杀模式为正则表达式"""
        escaped_pattern = re.escape(pattern)
        escaped_pattern = escaped_pattern.replace(r'%o', '(.*?)')
        escaped_pattern = escaped_pattern.replace(r'%u', '(.*?)')
        escaped_pattern = escaped_pattern.replace(r'%n', '(\\d+)')
        return escaped_pattern
    
    def _format_kill_message(self, message, killer, killed):
        """格式化击杀消息"""
        formatted = message
        if "%u" in formatted:
            formatted = formatted.replace("%u", killer)
        if "%o" in formatted:
            formatted = formatted.replace("%o", killed)
        return formatted
    
    def _build_killsay_message(self, formatted_message, killer, killed):
        """根据前缀和格式构建最终发送消息"""
        result = self.killsay_format or ConfigManager.DEFAULT_CONFIG["killsay_format"]
        result = result.replace("%t", self.message_prefix or "")
        result = result.replace("%m", formatted_message)
        result = result.replace("%u", killer)
        result = result.replace("%o", killed)
        result = result.replace("%c", str(self.kills))
        return result.strip()
    
    def _get_random_kill_message(self):
        """获取随机击杀消息"""
        if len(self.kill_messages) <= 5:
            return random.choice(self.kill_messages)
        
        if len(self.index_q) >= len(self.kill_messages):
            self.index_q.clear()
        
        for _ in range(50):
            rindex = random.randint(0, len(self.kill_messages) - 1)
            if rindex not in self.index_q:
                self.index_q.append(rindex)
                return self.kill_messages[rindex]
        
        self.index_q.clear()
        rindex = random.randint(0, len(self.kill_messages) - 1)
        self.index_q.append(rindex)
        return self.kill_messages[rindex]
    
    def _send_chat(self, msg):
        """发送聊天消息"""
        try:
            windows = pygetwindow.getWindowsWithTitle(self.window_name)
            if windows:
                bjd_window = windows[0]
                keyboard.send('t')
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
    
    def _change_theme(self, index):
        """更改主题"""
        if index is None or index < 0:
            return
        theme_key = self.theme_combo.itemData(index)
        if theme_key and self.theme_mgr.set_theme(theme_key):
            theme_name = self.theme_combo.currentText()
            self._setup_styles()
            QtWidgets.QMessageBox.information(self, "成功", f"已切换到主题: {theme_name}")
        elif theme_key:
            QtWidgets.QMessageBox.warning(self, "错误", "切换主题失败")
    
    def _show_custom_theme_dialog(self):
        """显示自定义主题对话框"""
        dialog = QtWidgets.QDialog(self)
        current_theme_key = self.theme_mgr.current_theme if self.theme_mgr.is_custom_theme(self.theme_mgr.current_theme) else None
        dialog.setWindowTitle("编辑自定义主题" if current_theme_key else "创建自定义主题")
        dialog.setFixedSize(800, 700)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 主题信息
        info_layout = QtWidgets.QHBoxLayout()
        info_layout.addWidget(QtWidgets.QLabel("主题名称:"))
        self.theme_name_edit = QtWidgets.QLineEdit()
        info_layout.addWidget(self.theme_name_edit)
        
        info_layout.addWidget(QtWidgets.QLabel("描述:"))
        self.theme_desc_edit = QtWidgets.QLineEdit()
        info_layout.addWidget(self.theme_desc_edit)
        
        layout.addLayout(info_layout)
        
        # 颜色选择区域
        instruction_label = QtWidgets.QLabel("只需选择“主强调色”，然后点击“自动生成配色”即可创建完整主题。")
        instruction_label.setStyleSheet("color: #3498db; font-size: 10pt;")
        layout.addWidget(instruction_label)

        scroll_area = QtWidgets.QScrollArea()
        scroll_widget = QtWidgets.QWidget()
        scroll_layout = QtWidgets.QVBoxLayout(scroll_widget)
        
        # 颜色标签映射
        color_labels = {
            "bg_primary": "主背景色",
            "bg_secondary": "次背景色", 
            "bg_tertiary": "三级背景色",
            "text_primary": "主要文字色",
            "text_secondary": "次要文字色",
            "accent_primary": "主强调色",
            "accent_hover": "强调色悬停",
            "accent_pressed": "强调色按下",
            "danger": "危险色",
            "danger_hover": "危险色悬停",
            "success": "成功色",
            "success_hover": "成功色悬停",
            "secondary": "次要色",
            "secondary_hover": "次要色悬停"
        }
        
        self.color_edits = {}
        if current_theme_key:
            current_theme = self.theme_mgr.get_theme_info(current_theme_key)
            self.theme_name_edit.setText(current_theme.get("name", ""))
            self.theme_desc_edit.setText(current_theme.get("description", ""))
            default_colors = current_theme.get("colors", self.theme_mgr.get_default_colors())
        else:
            default_colors = self.theme_mgr.get_default_colors()
        
        for color_key, label in color_labels.items():
            color_layout = QtWidgets.QHBoxLayout()
            color_layout.addWidget(QtWidgets.QLabel(f"{label}:"))

            color_value = default_colors.get(color_key, "#000000")
            color_edit = QtWidgets.QLineEdit()
            color_edit.setText(color_value)
            color_edit.setMaximumWidth(100)
            self.color_edits[color_key] = color_edit
            color_layout.addWidget(color_edit)

            choose_btn = QtWidgets.QPushButton("选择")
            choose_btn.setObjectName("secondary")
            color_layout.addWidget(choose_btn)

            color_preview = QtWidgets.QLabel()
            color_preview.setFixedSize(30, 20)
            color_preview.setStyleSheet(f"background-color: {color_value}; border: 1px solid #ccc;")
            color_layout.addWidget(color_preview)

            def make_color_picker(edit, preview):
                def pick_color():
                    current = QtGui.QColor(edit.text().strip())
                    color = QtWidgets.QColorDialog.getColor(current if current.isValid() else QtGui.QColor("#000000"), dialog, "选择颜色")
                    if color.isValid():
                        hex_color = color.name()
                        edit.setText(hex_color)
                        preview.setStyleSheet(f"background-color: {hex_color}; border: 1px solid #ccc;")
                return pick_color

            choose_btn.clicked.connect(make_color_picker(color_edit, color_preview))
            color_edit.textChanged.connect(lambda text, preview=color_preview: 
                preview.setStyleSheet(f"background-color: {text}; border: 1px solid #ccc;"))

            color_layout.addStretch()
            scroll_layout.addLayout(color_layout)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        # 按钮区域
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        
        # 预设按钮
        load_preset_btn = QtWidgets.QPushButton("从当前主题加载")
        load_preset_btn.clicked.connect(lambda: self._load_current_theme_colors(dialog))
        button_layout.addWidget(load_preset_btn)

        auto_palette_btn = QtWidgets.QPushButton("一键生成配色")
        auto_palette_btn.setObjectName("secondary")
        auto_palette_btn.clicked.connect(self._auto_generate_palette)
        button_layout.addWidget(auto_palette_btn)
        
        save_btn = QtWidgets.QPushButton("保存主题")
        save_btn.clicked.connect(lambda: self._save_custom_theme(dialog, current_theme_key))
        button_layout.addWidget(save_btn)
        
        cancel_btn = QtWidgets.QPushButton("取消")
        cancel_btn.setObjectName("secondary")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        dialog.exec_()
    
    def _load_current_theme_colors(self, dialog):
        """加载当前主题的颜色到编辑框"""
        current_theme = self.theme_mgr.get_current_theme()
        colors = current_theme.get("colors", {})
        
        for color_key, color_edit in self.color_edits.items():
            color_value = colors.get(color_key, "#000000")
            color_edit.setText(color_value)

    def _auto_generate_palette(self):
        """根据主色自动生成完整配色"""
        accent_value = self.color_edits.get("accent_primary").text().strip()
        generated = self.theme_mgr.generate_palette_from_primary(accent_value)
        for color_key, color_edit in self.color_edits.items():
            if color_key in generated:
                color_edit.setText(generated[color_key])
    
    def _save_custom_theme(self, dialog, theme_key=None):
        """保存自定义主题"""
        theme_name = self.theme_name_edit.text().strip()
        theme_desc = self.theme_desc_edit.text().strip()
        
        if not theme_name:
            QtWidgets.QMessageBox.warning(dialog, "错误", "请输入主题名称")
            return
        
        # 收集颜色值
        colors = {}
        for color_key, color_edit in self.color_edits.items():
            color_value = color_edit.text().strip()
            if not color_value.startswith("#") or len(color_value) != 7:
                QtWidgets.QMessageBox.warning(dialog, "错误", f"颜色值格式不正确: {color_key}")
                return
            colors[color_key] = color_value
        
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
        event.accept()
    
    def run(self):
        """运行应用程序"""
        self.show()
