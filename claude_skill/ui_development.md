# UI开发指南

## 1. UI架构概览

```
services/ui/
├── main.py              # UI入口点
├── ui_runtime.py        # UI运行时状态（全局变量）
├── registration.py      # 患者注册窗口
├── examination.py       # 检查窗口
├── configuration.py     # 配置对话框
├── studyviewer.py       # 研究查看器
├── protocolbrowser.py   # 协议浏览器
├── taskviewer.py        # 任务查看器
├── flexviewer.py        # 图像查看器
├── logviewer.py         # 日志查看器
├── systemstatus.py      # 系统状态
├── about.py             # 关于对话框
├── control.py           # 服务控制
├── forms/               # Qt Designer UI文件
│   ├── registration.ui
│   ├── examination.ui
│   └── ...
└── assets/              # 图片资源
    ├── mri4all_logo.png
    └── ...
```

## 2. 主程序入口

### run_ui.py

```python
import services.ui.main

if __name__ == "__main__":
    services.ui.main.run()
```

### services/ui/main.py

```python
import sys
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import qdarktheme

import common.logger as logger
import common.runtime as rt

# 设置服务名称（必须在获取logger之前）
rt.set_service_name("ui")
log = logger.get_logger()

# 重定向stdout/stderr到日志
sys.stdout = logger.LoggerStdCapture(log.info)
sys.stderr = logger.LoggerStdCapture(log.warning)


def run():
    # 1. 启用高DPI支持
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    
    # 2. 创建应用实例
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(f"{rt.get_console_path()}/services/ui/assets/mri4all_icon.png"))
    
    # 3. 应用主题
    set_MRI4ALL_style(app)
    
    # 4. 准备系统
    if not prepare_system():
        show_error_and_exit()
        return
    
    # 5. 创建窗口栈
    ui_runtime.stacked_widget = QStackedWidget()
    ui_runtime.registration_widget = registration.RegistrationWindow()
    ui_runtime.examination_widget = examination.ExaminationWindow()
    
    ui_runtime.stacked_widget.addWidget(ui_runtime.registration_widget)
    ui_runtime.stacked_widget.addWidget(ui_runtime.examination_widget)
    ui_runtime.stacked_widget.setCurrentIndex(0)
    
    # 6. 显示全屏
    ui_runtime.stacked_widget.showFullScreen()
    
    # 7. 运行事件循环
    return_value = app.exec_()
    
    # 8. 清理
    shutdown_system()
    sys.exit(return_value)
```

## 3. 自定义主题

### 颜色定义

```python
def set_MRI4ALL_style(app):
    # QSS样式
    qss = """
    QWidget {
        font-size: 16px;
    }
    QPushButton:hover {
        color: #FFFFFF;
        background-color: #E0A526;    
    }
    QPushButton[type = "highlight"] {
        color: #FFFFFF;
        background-color: rgba(224, 165, 38, 120); 
    }
    QPushButton[type = "dimmed"] {
        color: #FFFFFF;
    }
    QGroupBox::title {
        color: #E0A526;    
    }
    """
    
    # 应用qdarktheme
    qdarktheme.setup_theme(
        corner_shape="sharp",
        custom_colors={
            "primary": "#E0A526",           # 主色调（金色）
            "background": "#040919",        # 背景（深蓝黑）
            "border": "#FFFFFF22",          # 边框
            "foreground": "#FFFFFF",        # 前景文字
            "input.background": "#00000022", # 输入框背景
        },
        additional_qss=qss,
    )
```

### 按钮类型

```python
# 高亮按钮（金色背景）
button.setProperty("type", "highlight")

# 暗淡按钮（低调样式）
button.setProperty("type", "dimmed")

# 工具栏按钮
button.setProperty("type", "toolbar")

# 可切换的暗淡按钮
button.setProperty("type", "dimmedcheck")
```

## 4. 窗口类模板

### 主窗口类

```python
from PyQt5 import uic
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import qtawesome as qta

import common.runtime as rt
import common.logger as logger

log = logger.get_logger()


class MyWindow(QMainWindow):
    def __init__(self):
        super(MyWindow, self).__init__()
        
        # 1. 加载UI文件
        uic.loadUi(f"{rt.get_console_path()}/services/ui/forms/mywindow.ui", self)
        
        # 2. 设置控件
        self._setup_buttons()
        self._setup_connections()
        self._setup_styles()
    
    def _setup_buttons(self):
        """设置按钮图标和文本"""
        self.saveButton.setIcon(qta.icon("fa5s.save"))
        self.saveButton.setIconSize(QSize(20, 20))
        self.saveButton.setText(" Save")
    
    def _setup_connections(self):
        """连接信号槽"""
        self.saveButton.clicked.connect(self.on_save)
        self.cancelButton.clicked.connect(self.close)
    
    def _setup_styles(self):
        """设置样式属性"""
        self.saveButton.setProperty("type", "highlight")
        self.cancelButton.setProperty("type", "dimmed")
```

### 对话框类

```python
class MyDialog(QDialog):
    def __init__(self, parent=None):
        super(MyDialog, self).__init__(parent)
        uic.loadUi(f"{rt.get_console_path()}/services/ui/forms/mydialog.ui", self)
        
        # 设置对话框属性
        self.setWindowTitle("My Dialog")
        self.setModal(True)
    
    def accept(self):
        """确定按钮处理"""
        if self.validate():
            super().accept()
    
    def validate(self) -> bool:
        """验证输入"""
        return True


# 使用对话框
def show_my_dialog():
    dialog = MyDialog()
    if dialog.exec_() == QDialog.Accepted:
        # 处理确认
        pass
```

## 5. 使用QtAwesome图标

```python
import qtawesome as qta

# 设置图标
button.setIcon(qta.icon("fa5s.check"))        # 勾选
button.setIcon(qta.icon("fa5s.power-off"))    # 电源
button.setIcon(qta.icon("fa5s.play"))         # 播放
button.setIcon(qta.icon("fa5s.stop"))         # 停止
button.setIcon(qta.icon("fa5s.undo-alt"))     # 撤销
button.setIcon(qta.icon("fa5s.flask"))        # 烧瓶
button.setIcon(qta.icon("fa5s.sign-out-alt")) # 退出

# 带颜色的图标
icon = qta.icon("fa5s.exclamation-triangle", color="#E5554F")

# 设置图标大小
button.setIconSize(QSize(20, 20))
button.setIconSize(QSize(32, 32))
```

## 6. UI运行时状态管理

### ui_runtime.py

```python
# 全局变量存储UI状态
app = None
stacked_widget = None
registration_widget = None
examination_widget = None

patient_information = PatientInformation()
exam_information = ExamInformation()
system_information = SystemInformation()

scan_queue_list: List[ScanQueueEntry] = []
editor_active: bool = False
editor_readonly: bool = False

status_acq_active = False
status_recon_active = False


def get_screen_size() -> Tuple[int, int]:
    """获取屏幕尺寸"""
    screen = QDesktopWidget().screenGeometry()
    return screen.width(), screen.height()


def register_patient():
    """注册患者并切换到检查窗口"""
    global exam_information
    
    if not queue.clear_folders():
        log.error("Failed to clear data folders")
        return
    
    scan_queue_list.clear()
    examination_widget.prepare_examination_ui()
    stacked_widget.setCurrentIndex(1)  # 切换到检查窗口


def close_patient():
    """关闭当前检查"""
    stacked_widget.setCurrentIndex(0)  # 返回注册窗口
    patient_information.clear()
    exam_information.clear()
```

## 7. 定时器与更新

### 周期性更新UI

```python
class ExaminationWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 创建定时器
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_queue_status)
        self.update_timer.start(1000)  # 每秒更新
    
    def update_queue_status(self):
        """更新扫描队列状态"""
        ui_runtime.update_scan_queue_list()
        self.refresh_queue_display()
```

### 处理IPC消息

```python
from common.ipc import Communicator

class ExaminationWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 创建通信器
        self.communicator_acq = Communicator(Communicator.UI_ACQ)
        self.communicator_acq.received.connect(self.handle_acq_message)
        self.communicator_acq.listen()
    
    def handle_acq_message(self, envelope):
        """处理来自ACQ服务的消息"""
        message = envelope.value
        
        if message.type == "set_status":
            self.statusBar.showMessage(message.message)
        
        elif message.type == "user_alert":
            QMessageBox.information(self, "Alert", message.message)
        
        elif message.type == "user_query":
            self.handle_user_query(message)
```

## 8. 消息框

### 标准消息框

```python
# 信息框
QMessageBox.information(self, "Info", "Operation completed")

# 警告框
QMessageBox.warning(self, "Warning", "Something needs attention")

# 错误框
QMessageBox.critical(self, "Error", "Operation failed")

# 确认框
reply = QMessageBox.question(
    self, 
    "Confirm", 
    "Are you sure?",
    QMessageBox.Yes | QMessageBox.No,
    QMessageBox.No
)
if reply == QMessageBox.Yes:
    # 用户确认
    pass
```

### 自定义消息框

```python
msg = QMessageBox()
dialog_icon = qta.icon("fa5s.power-off", color="#E0A526")
msg.setIconPixmap(dialog_icon.pixmap(64, 64))
msg.setWindowTitle("Shutdown Console?")
msg.setText("Do you really want to shutdown?")
msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
msg.setDefaultButton(QMessageBox.No)
msg.setContentsMargins(12, 12, 12, 6)

if msg.exec() == QMessageBox.Yes:
    # 执行关闭
    pass
```

## 9. 事件过滤器

```python
class RegistrationWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # 安装事件过滤器
        self.mrnEdit.installEventFilter(self)
    
    def eventFilter(self, source, event):
        """处理特定控件的事件"""
        if source == self.mrnEdit and event.type() == QEvent.MouseButtonPress:
            # 点击时选中文本
            self.mrnEdit.setFocus(Qt.MouseFocusReason)
            self.mrnEdit.setCursorPosition(0)
            return True  # 事件已处理
        
        return super().eventFilter(source, event)
```

## 10. 日期选择器样式

```python
# 设置日历控件样式
fmt = self.dobEdit.calendarWidget().weekdayTextFormat(Qt.Sunday)
fmt.setForeground(QColor("white"))
self.dobEdit.calendarWidget().setWeekdayTextFormat(Qt.Saturday, fmt)
self.dobEdit.calendarWidget().setWeekdayTextFormat(Qt.Sunday, fmt)
```

## 11. 窗口切换

```python
# 使用QStackedWidget管理多个窗口
stacked_widget = QStackedWidget()
stacked_widget.addWidget(registration_widget)  # index 0
stacked_widget.addWidget(examination_widget)   # index 1

# 切换窗口
stacked_widget.setCurrentIndex(0)  # 显示注册窗口
stacked_widget.setCurrentIndex(1)  # 显示检查窗口
```

## 12. 异常处理

```python
def excepthook(exc_type, exc_value, exc_tb):
    """全局异常处理"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        shutdown_system()
        sys.exit()
    
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    log.exception(tb)
    
    errorbox = QMessageBox()
    errorbox.setText(f"An unexpected error occurred:\n{tb}")
    errorbox.exec_()

sys.excepthook = excepthook
```

## 13. UI开发检查清单

- [ ] 使用 `uic.loadUi()` 加载 `.ui` 文件
- [ ] 使用 `setProperty("type", "...")` 设置按钮样式
- [ ] 使用 `qtawesome` 设置图标
- [ ] 连接所有必要的信号槽
- [ ] 实现表单验证和错误提示
- [ ] 测试高DPI显示效果
- [ ] 测试全屏模式
- [ ] 处理异常情况并显示友好消息

