"""数字翻转控件（3D 前后翻转）。

纯 Qt 绘制实现的数字翻牌效果：
- 数字绕水平中轴做前后翻转（rotateX），转 90° 时旧数字消失、
  新数字再从 90° 转回正面（视觉上共翻转 180°）；
- 从最低位到最高位带有轻微级联效果；
- 支持整数与小数（小数点为静态圆点）。
"""
import math
from PyQt5 import QtCore, QtGui, QtWidgets


class FlipNumber(QtWidgets.QWidget):
    """数字翻转显示控件。

    用法：``widget.setValue(12, animate=True)``，内部自动播放前后翻转动画。
    """

    def __init__(self, parent=None, decimals=0, duration=240,
                 digit_width=34, digit_height=52, gap=6,
                 fg_color="#4aa3ff", card_bg="#243447",
                 border_color="#3d5069", hinge_color="#141e2b",
                 stagger=0.06):
        super().__init__(parent)

        self._decimals = int(decimals)
        self._duration = int(duration)
        self._digit_width = int(digit_width)
        self._digit_height = int(digit_height)
        self._gap = int(gap)
        self._fg_color = fg_color
        self._card_bg = card_bg
        self._border_color = border_color
        self._stagger = float(stagger)

        self._value = 0.0 if self._decimals else 0
        self._from_str = self._fmt(0)
        self._to_str = self._fmt(0)
        self._progress = 1.0

        # 让控件背景透明，避免圆角卡片周围出现方角底色
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self.setStyleSheet("background: transparent;")

        self._anim = QtCore.QVariantAnimation(self)
        self._anim.setDuration(self._duration)
        self._anim.setEasingCurve(QtCore.QEasingCurve.Linear)
        self._anim.valueChanged.connect(self._on_progress)
        self._anim.finished.connect(self._on_finished)

        self._glyph_cache = {}
        self._update_size()

    # ------------------------------------------------------------------ #
    # 公共接口
    # ------------------------------------------------------------------ #
    def setValue(self, value, animate=True):
        """设置数值，可选择是否播放翻转动画。"""
        if self._decimals:
            value = float(value)
        else:
            value = int(round(float(value)))

        if value == self._value:
            return

        self._from_str = self._fmt(self._value)
        self._value = value
        self._to_str = self._fmt(value)
        self._update_size()

        if animate and self.isVisible():
            self._progress = 0.0
            self._anim.stop()
            self._anim.setStartValue(0.0)
            self._anim.setEndValue(1.0)
            self._anim.start()
        else:
            self._progress = 1.0
        self.update()

    def value(self):
        """返回当前数值。"""
        return self._value

    def text(self):
        """返回当前显示文本（与数值一致的格式化字符串）。"""
        return self._fmt(self._value)

    def setColors(self, fg_color=None, card_bg=None, border_color=None, hinge_color=None):
        """更新配色并清空字形缓存。"""
        if fg_color is not None:
            self._fg_color = fg_color
        if card_bg is not None:
            self._card_bg = card_bg
        if border_color is not None:
            self._border_color = border_color
        self._glyph_cache.clear()
        self.update()

    # ------------------------------------------------------------------ #
    # 内部实现
    # ------------------------------------------------------------------ #
    def _fmt(self, value):
        if self._decimals:
            return "{:.{}f}".format(float(value), self._decimals)
        return str(int(round(float(value))))

    def _dot_width(self):
        return max(10, int(self._digit_width * 0.45))

    def _update_size(self):
        s = self._to_str
        w = 0
        for ch in s:
            w += self._dot_width() if ch == '.' else self._digit_width
        w += self._gap * max(0, len(s) - 1)
        self.setFixedSize(w + 2, self._digit_height + 2)

    def _on_progress(self, v):
        self._progress = float(v)
        self.update()

    def _on_finished(self):
        self._progress = 1.0
        self.update()

    def _local_progress(self, i, n):
        """根据数字位计算级联延迟后的本地进度。"""
        if self._progress >= 1.0:
            return 1.0
        pos_from_right = (n - 1 - i)
        delay = pos_from_right * self._stagger
        if delay >= 1.0:
            delay = 0.9
        if self._progress <= delay:
            return 0.0
        return min(1.0, (self._progress - delay) / (1.0 - delay))

    def _glyph(self, ch):
        """渲染（并缓存）单个字符的完整位图。"""
        if ch == '.':
            key = ('.', self._fg_color, self._dot_width(), self._digit_height)
        else:
            key = (ch, self._fg_color, self._digit_width, self._digit_height)
        if key in self._glyph_cache:
            return self._glyph_cache[key]

        w, h = key[2], key[3]
        pm = QtGui.QPixmap(w, h)
        pm.fill(QtCore.Qt.transparent)
        p = QtGui.QPainter(pm)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        p.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
        font = QtGui.QFont("Segoe UI")
        font.setBold(True)
        font.setPixelSize(int(h * 0.62))
        p.setFont(font)
        p.setPen(QtGui.QColor(self._fg_color))
        p.drawText(0, 0, w, h, QtCore.Qt.AlignCenter, ch)
        p.end()

        self._glyph_cache[key] = pm
        return pm

    # ------------------------------------------------------------------ #
    # 绘制
    # ------------------------------------------------------------------ #
    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)

        s_from = self._from_str
        s_to = self._to_str
        n = len(s_to)
        x = 0
        for i, to_ch in enumerate(s_to):
            j = i - (n - len(s_from))
            from_ch = s_from[j] if 0 <= j < len(s_from) else ' '
            if from_ch == ' ' or from_ch == to_ch:
                from_ch = to_ch

            w = self._dot_width() if to_ch == '.' else self._digit_width
            local = self._local_progress(i, n)
            if to_ch == '.':
                self._paint_dot(p, x, w)
            else:
                self._paint_cell(p, x, w, from_ch, to_ch, local)
            x += w + self._gap
        p.end()

    def _paint_cell(self, p, x, w, from_ch, to_ch, progress):
        # 数字未变化时保持静态
        if from_ch == to_ch:
            progress = 1.0
        h = self._digit_height

        # 卡片槽位背景（静态）
        p.setPen(QtGui.QColor(self._border_color))
        p.setBrush(QtGui.QColor(self._card_bg))
        p.drawRoundedRect(x, 0, w, h, 6, 6)

        # 裁剪到卡片内部
        p.save()
        p.setClipRect(x, 0, w, h)

        # 前后翻转：绕水平中轴 rotateX，垂直方向做 cos 投影
        if progress >= 1.0:
            ch, scale = to_ch, 1.0
        elif progress <= 0.0:
            ch, scale = from_ch, 1.0
        elif progress < 0.5:
            # 前半程：旧数字 0° → 90°（逐渐转到侧边消失）
            t = progress / 0.5
            ch, scale = from_ch, math.cos(t * math.pi / 2.0)
        else:
            # 后半程：新数字 90° → 0°（从侧边转回正面）
            t = (progress - 0.5) / 0.5
            ch, scale = to_ch, math.sin(t * math.pi / 2.0)

        disp_h = int(round(h * scale))
        if disp_h >= 2:
            # 锚定水平中轴，上下同时向中间收缩/展开
            ty = (h - disp_h) / 2.0
            target = QtCore.QRectF(x, ty, w, disp_h)
            # 翻转过程中稍微变暗，模拟侧向受光减弱，增强立体感
            p.setOpacity(0.55 + 0.45 * scale)
            p.drawPixmap(target, self._glyph(ch), QtCore.QRectF(0, 0, w, h))
            p.setOpacity(1.0)

        p.restore()

    def _paint_dot(self, p, x, w):
        h = self._digit_height
        p.setPen(QtGui.QColor(self._border_color))
        p.setBrush(QtGui.QColor(self._card_bg))
        p.drawRoundedRect(x, 0, w, h, 4, 4)
        p.setPen(QtGui.QColor(self._fg_color))
        p.setBrush(QtGui.QColor(self._fg_color))
        r = max(2, min(w, h) // 5)
        p.drawEllipse(QtCore.QPoint(int(x + w / 2), int(h / 2)), r, r)
