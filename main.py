import os
import sys
from PyQt5 import QtWidgets, QtGui
from app import KillSayApp
from utils import get_base_dir

# 导入资源文件（包含嵌入的图标）
import resource_rc

def main():
    app = QtWidgets.QApplication(sys.argv)
    
    # 使用嵌入的资源图标
    icon = QtGui.QIcon(":/icon.ico")
    app.setWindowIcon(icon)
    
    window = KillSayApp()
    window.setWindowIcon(icon)
    window.run()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
