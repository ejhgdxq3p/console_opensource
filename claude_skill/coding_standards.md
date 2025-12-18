# 代码规范与风格

## 1. 项目约定

### 1.1 Python版本
- **最低要求**: Python 3.10+
- **类型注解**: 必须使用类型注解

### 1.2 文件命名
```
模块文件: snake_case.py          # 如 scan_task.py
类文件:   与类名对应的snake_case  # 如 sequence_base.py
UI文件:   与窗口对应              # 如 registration.py
```

### 1.3 导入顺序
```python
# 1. 标准库
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# 2. 第三方库
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from pydantic import BaseModel

# 3. 本地模块 - common优先
import common.logger as logger
import common.runtime as rt
from common.constants import *
from common.types import ScanTask

# 4. 服务/序列特定模块
from sequences import SequenceBase
```

## 2. 类型定义规范

### 2.1 Pydantic模型

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class PatientInformation(BaseModel):
    """患者信息数据模型"""
    first_name: str = ""
    last_name: str = ""
    mrn: str = ""
    birth_date: str = ""
    gender: str = ""
    weight_kg: int = 0
    height_cm: int = 0
    age: int = 0

    def get_full_name(self) -> str:
        """返回格式化的全名"""
        return f"{self.last_name}, {self.first_name}"

    def clear(self) -> None:
        """重置所有字段"""
        self.first_name = ""
        self.last_name = ""
        # ...
```

### 2.2 Literal类型用于状态

```python
# 使用Literal定义有限状态集
ScanStatesType = Literal[
    "created",
    "scheduled_acq",
    "acq",
    "scheduled_recon",
    "recon",
    "complete",
    "failure",
    "invalid",
]

# 用于字段类型
class ScanQueueEntry(BaseModel):
    state: ScanStatesType = "created"
```

### 2.3 配置字段

```python
class Configuration(BaseModel):
    # 使用Field提供默认值和描述
    scanner_ip: str = Field(default="10.42.0.251", description="Scanner IP")
    debug_mode: str = Field(default="False", description="Debug Mode")
    
    # description="hidden" 表示在UI中隐藏
    internal_setting: str = Field(default="", description="hidden")
```

## 3. 日志规范

### 3.1 获取Logger

```python
import common.logger as logger

log = logger.get_logger()  # 在模块顶部获取一次
```

### 3.2 日志级别使用

```python
# DEBUG - 调试信息
log.debug("Sequence file stored")

# INFO - 正常流程
log.info("Acquisition completed with success")
log.info(f"Processing scan: {scan_name}")

# WARNING - 非致命问题
log.warning(f"Lock file exists: {lock_file}")
log.warn("Unable to update configuration")

# ERROR - 错误但可继续
log.error(f"Unable to create task folder {folder_name}")

# EXCEPTION - 带堆栈跟踪
log.exception(e)
```

### 3.3 日志格式

```
2024-02-22 21:09:10 | ui | INF | exam_id | Message here
```

## 4. 错误处理

### 4.1 返回布尔值模式

```python
def move_task(folder_path: str, target: str) -> bool:
    """
    移动任务文件夹
    
    Returns:
        bool: 成功返回True，失败返回False
    """
    if not os.path.isdir(folder_path):
        log.warn(f"Folder not found at {folder_path}")
        return False
    
    try:
        os.rename(folder_path, target + "/" + os.path.basename(folder_path))
    except Exception:
        log.error(f"Error moving folder {folder_path}")
        return False
    
    return True
```

### 4.2 异常处理

```python
def read_task(folder) -> Any:
    """读取任务文件"""
    scan_task = ScanTask()
    
    try:
        with open(task_filename, "r") as task_file:
            scan_task = ScanTask(**json.load(task_file))
    except Exception:
        log.error(f"Unable to read task file {task_filename}")
        return None  # 返回None表示失败
    
    return scan_task
```

### 4.3 带步骤跟踪的错误处理

```python
current_step = ""
try:
    current_step = "instantiation"
    seq_instance = SequenceBase.get_sequence(scan_task.sequence)()
    
    current_step = "set_parameters"
    if not seq_instance.set_parameters(scan_task.parameters, scan_task):
        raise Exception("Invalid protocol")
    
    current_step = "calculate_sequence"
    if not seq_instance.calculate_sequence(scan_task):
        raise Exception("Sequence calculation failed")
        
except Exception as e:
    log.error(f"Failure during step {current_step}")
    log.exception(e)
    return False
```

## 5. 文件操作

### 5.1 文件锁机制

```python
class FileLock:
    """文件锁实现，确保析构时释放锁"""
    
    def __init__(self, path_for_lockfile: Path):
        self.lockfile = path_for_lockfile
        self.lockfile.touch(exist_ok=False)
        self.lockCreated = True

    def __del__(self) -> None:
        self.free()

    def free(self) -> None:
        if self.lockCreated:
            self.lockfile.unlink()
            self.lockCreated = False
```

### 5.2 使用锁保护文件操作

```python
def write_task(folder, scan_task: ScanTask) -> bool:
    lock_file = Path(folder) / mri4all_files.LOCK
    
    try:
        lock = helper.FileLock(lock_file)
    except:
        log.error(f"Unable to create lock file {lock_file}")
        return False

    try:
        with open(task_filename, "w") as task_file:
            json.dump(scan_task.model_dump(), task_file, indent=4)
    except Exception:
        log.error(f"Unable to write task file")
        return False
    finally:
        lock.free()  # 确保释放锁

    return True
```

## 6. PyQt5规范

### 6.1 窗口类结构

```python
class RegistrationWindow(QMainWindow):
    def __init__(self):
        super(RegistrationWindow, self).__init__()
        
        # 1. 加载UI文件
        uic.loadUi(f"{rt.get_console_path()}/services/ui/forms/registration.ui", self)
        
        # 2. 设置控件属性
        self.registerButton.setProperty("type", "highlight")
        self.registerButton.setIcon(qta.icon("fa5s.check"))
        
        # 3. 连接信号
        self.registerButton.clicked.connect(self.register_clicked)
        
        # 4. 安装事件过滤器
        self.mrnEdit.installEventFilter(self)
```

### 6.2 属性用于样式

```python
# 使用setProperty设置样式类型
self.button.setProperty("type", "highlight")
self.button.setProperty("type", "dimmed")
self.button.setProperty("type", "toolbar")

# QSS中对应
# QPushButton[type = "highlight"] { ... }
```

### 6.3 信号槽连接

```python
# 简单连接
self.button.clicked.connect(self.on_click)

# 带参数
self.timer.timeout.connect(lambda: self.update_status())

# IPC信号
self.communicator.received.connect(self.handle_message)
```

## 7. 常量命名

### 7.1 路径常量类

```python
class mri4all_paths:
    BASE = rt.get_base_path()
    DATA = os.path.join(BASE, "data")
    DATA_QUEUE_ACQ = os.path.join(DATA, "acq_queue")
```

### 7.2 文件名常量类

```python
class mri4all_files:
    LOCK = "LOCK"
    PREPARED = "PREPARED"
    EDITING = "EDITING"
    TASK = "scan.json"
```

### 7.3 状态常量类

```python
class mri4all_states:
    CREATED = "created"
    SCHEDULED_ACQ = "scheduled_acq"
    ACQ = "acq"
```

## 8. 注释规范

### 8.1 文档字符串

```python
def create_task(
    exam_id: str,
    scan_id: str,
    scan_counter: int,
    sequence: str,
    patient_information: PatientInformation,
    default_seq_parameters: dict,
    default_protocol_name: str,
    system_information: SystemInformation,
    exam_information: ExamInformation,
) -> str:
    """
    Creates a new scan task for the given exam ID.
    
    Args:
        exam_id: 检查唯一标识
        scan_id: 扫描唯一标识
        ...
    
    Returns:
        str: 成功返回scan_name，失败返回空字符串
    """
```

### 8.2 TODO注释

```python
# TODO: Add missing entries from registration form
# TODO: Secure file access with LOCK file
# TODO: Handle case if lock file cannot be created
```

### 8.3 类型忽略注释

```python
from PyQt5.QtGui import *  # type: ignore
import qdarktheme  # type: ignore
remaining_tasks = helper.asyncio.all_tasks(helper.loop)  # type: ignore[attr-defined]
```

