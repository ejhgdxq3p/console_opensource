# 模块开发指南

## 1. Common模块详解

### 1.1 runtime.py - 运行时状态

```python
import common.runtime as rt

# 服务标识
rt.set_service_name("ui")      # 设置服务名
name = rt.get_service_name()   # 获取服务名

# 路径管理
base_path = rt.get_base_path()        # 数据基础路径
console_path = rt.get_console_path()  # 代码路径

# 任务追踪
rt.set_current_task_id("exam123#scan_1")
task_id = rt.get_current_task_id()
rt.clear_current_task_id()

# 调试模式
rt.set_debug(True)
is_debug = rt.is_debugging_enabled()
```

### 1.2 logger.py - 日志系统

```python
import common.logger as logger

# 获取logger实例（单例）
log = logger.get_logger()

# 日志级别
log.debug("Debug message")
log.info("Info message")
log.warning("Warning message")
log.error("Error message")
log.exception(exception_object)

# 重定向stdout/stderr
sys.stdout = logger.LoggerStdCapture(log.info)
sys.stderr = logger.LoggerStdCapture(log.warning)
```

### 1.3 config.py - 配置管理

```python
import common.config as config

# 加载配置
config.load_config()

# 获取配置实例
cfg = config.get_config()

# 访问配置项
scanner_ip = cfg.scanner_ip
is_sim = cfg.is_hardware_simulation()

# 更新配置
cfg.update({"debug_mode": "True"})
cfg.save_to_file()
```

#### 配置类定义

```python
from pydantic import BaseModel, Field

class Configuration(BaseModel):
    scanner_ip: str = Field(default="10.42.0.251", description="Scanner IP")
    debug_mode: str = Field(default="False", description="Debug Mode")
    hardware_simulation: str = Field(default="False", description="Hardware Simulation")
    
    # description="hidden" 在UI中隐藏
    internal_setting: str = Field(default="", description="hidden")
    
    @classmethod
    def load_from_file(cls):
        with open(config_path, "r") as f:
            return cls.model_validate_json(f.read())
    
    def save_to_file(self):
        with open(config_path, "w") as f:
            f.write(self.model_dump_json(indent=4))
```

### 1.4 constants.py - 常量定义

```python
from common.constants import *

# 路径常量
mri4all_paths.BASE           # 基础路径
mri4all_paths.DATA           # 数据目录
mri4all_paths.DATA_QUEUE_ACQ # 采集队列
mri4all_paths.DATA_ACQ       # 采集中
mri4all_paths.DATA_COMPLETE  # 已完成

# 文件名常量
mri4all_files.LOCK           # "LOCK"
mri4all_files.PREPARED       # "PREPARED"
mri4all_files.TASK           # "scan.json"

# 状态常量
mri4all_states.CREATED
mri4all_states.SCHEDULED_ACQ
mri4all_states.ACQ
mri4all_states.COMPLETE

# 扫描文件
mri4all_scanfiles.RAWDATA    # "raw.npy"
mri4all_scanfiles.PE_ORDER   # "pe_order.npy"
mri4all_scanfiles.TRAJ       # "traj.csv"
```

### 1.5 types.py - 数据类型

```python
from common.types import (
    PatientInformation,
    ExamInformation,
    SystemInformation,
    ScanTask,
    ScanQueueEntry,
    ResultItem,
    ProcessingConfig,
    AdjustmentSettings,
)

# 患者信息
patient = PatientInformation()
patient.first_name = "John"
patient.last_name = "Doe"
patient.mrn = "12345"
full_name = patient.get_full_name()  # "Doe, John"

# 扫描任务
task = ScanTask()
task.id = "unique-id"
task.sequence = "FID"
task.parameters = {"TR": 500, "TE": 20}
task.results.append(ResultItem(...))

# 结果项
result = ResultItem()
result.type = "dicom"  # "dicom" | "plot" | "rawdata" | "empty"
result.name = "Images"
result.primary = True
result.autoload_viewer = 1
```

### 1.6 task.py - 任务操作

```python
import common.task as task

# 创建任务
folder_name = task.create_task(
    exam_id="exam123",
    scan_id="scan-uuid",
    scan_counter=1,
    sequence="FID",
    patient_information=patient,
    default_seq_parameters={"TR": 500},
    default_protocol_name="FID",
    system_information=system,
    exam_information=exam,
)

# 读取任务
scan_task = task.read_task("/path/to/task/folder")

# 写入任务
success = task.write_task("/path/to/task/folder", scan_task)

# 删除任务
success = task.delete_task("/path/to/task/folder")

# 状态管理
task.set_task_state(folder, mri4all_files.PREPARED, True)
task.set_task_state(folder, mri4all_files.EDITING, False)
is_prepared = task.has_task_state(folder, mri4all_files.PREPARED)

# 清空子文件夹
task.clear_task_subfolder(folder, mri4all_taskdata.TEMP)
```

### 1.7 queue.py - 队列操作

```python
import common.queue as queue

# 检查并创建文件夹
success = queue.check_and_create_folders()

# 移动任务
success = queue.move_task(
    "/path/from/task",
    mri4all_paths.DATA_QUEUE_RECON
)

# 清空文件夹（移动到archive）
success = queue.clear_folder(mri4all_paths.DATA_ACQ)
success = queue.clear_folders()  # 清空所有工作文件夹

# 获取待处理任务
scan_name = queue.get_scan_ready_for_acq()
scan_name = queue.get_scan_ready_for_recon()
```

### 1.8 helper.py - 工具函数

```python
import common.helper as helper

# 生成UUID
uid = helper.generate_uid()  # "a1b2c3d4-e5f6-..."

# 获取ISO时间
timestamp = helper.get_datetime()  # "2024-02-22T21:09:10.123456"

# 文件锁
lock = helper.FileLock(Path("/path/to/LOCK"))
# ... 操作 ...
lock.free()  # 或让析构函数自动释放

# 进程终止控制
helper.trigger_terminate()
if helper.is_terminated():
    return

# 异步定时器
timer = helper.AsyncTimer(0.1, callback_function)
timer.start()
timer.stop()
timer.run_until_complete(loop)
```

### 1.9 version.py - 版本管理

```python
from common.version import mri4all_version

# 获取版本字符串
version_str = mri4all_version.get_version_string()  # "1.0.0-beta.1"

# 获取版本签名（用于比较）
signature = mri4all_version.get_version_signature()  # [1, 0, 0, 3, 1]

# 版本状态
is_dev = mri4all_version.is_dev_version()
is_release = mri4all_version.is_release()
is_valid = mri4all_version.is_valid_version()
```

## 2. IPC模块

### 2.1 消息类型

```python
from common.ipc.messages import (
    SetStatusMessage,
    UserQueryMessage,
    UserAlertMessage,
    ShowPlotMessage,
    AcqDataMessage,
)

# 状态消息
msg = SetStatusMessage(message="Processing...")

# 用户查询
msg = UserQueryMessage(
    request="Enter value",
    input_type="int",  # "text" | "int" | "float"
    in_min=0,
    in_max=100
)

# 警告消息
msg = UserAlertMessage(
    message="Warning!",
    alert_type="warning"  # "information" | "warning" | "critical"
)
```

### 2.2 通信器使用

```python
from common.ipc import Communicator

# 服务端 (ACQ/RECON)
comm = Communicator(Communicator.ACQ)
comm.send_status("Processing...")
value = comm.query_user("Enter value", input_type="int")
comm.send_user_alert("Done!", type="information")

# 客户端 (UI)
comm = Communicator(Communicator.UI_ACQ)
comm.received.connect(self.handle_message)
comm.listen()

def handle_message(self, envelope):
    if envelope.value.type == "set_status":
        self.status_label.setText(envelope.value.message)
```

## 3. 创建新模块

### 模块结构

```python
# common/my_module.py

import common.runtime as rt
import common.logger as logger

log = logger.get_logger()


class MyModuleClass:
    """模块类文档"""
    
    def __init__(self):
        pass
    
    def do_something(self) -> bool:
        """方法文档"""
        log.info("Doing something")
        return True


# 模块级函数
def utility_function(param: str) -> str:
    """函数文档"""
    return param.upper()


# 模块级单例（如需要）
_instance = None

def get_instance():
    global _instance
    if _instance is None:
        _instance = MyModuleClass()
    return _instance
```

### 导入约定

```python
# 其他模块中使用
import common.my_module as my_module

result = my_module.utility_function("test")
instance = my_module.get_instance()
```

## 4. 数据模型扩展

### 添加新的Pydantic模型

```python
# common/types.py

from pydantic import BaseModel
from typing import Optional, List, Literal

class MyNewType(BaseModel):
    """新数据类型"""
    
    field1: str = ""
    field2: int = 0
    field3: Optional[float] = None
    field4: List[str] = []
    field5: Literal["option1", "option2"] = "option1"
    
    def custom_method(self) -> str:
        return f"{self.field1}-{self.field2}"
    
    def clear(self) -> None:
        self.field1 = ""
        self.field2 = 0
        self.field3 = None
        self.field4 = []
```

### 在ScanTask中使用

```python
class ScanTask(BaseModel):
    # ... 现有字段 ...
    my_new_data: MyNewType = MyNewType()  # 添加新字段
```

## 5. 常量扩展

### 添加新常量

```python
# common/constants.py

class mri4all_custom:
    """自定义常量"""
    MY_CONST = "value"
    ANOTHER_CONST = 123

class MyEnum(Enum):
    OPTION1 = "option1"
    OPTION2 = "option2"
```

## 6. 模块开发检查清单

- [ ] 遵循导入顺序约定
- [ ] 使用类型注解
- [ ] 添加文档字符串
- [ ] 使用 `common.logger` 记录日志
- [ ] 遵循错误处理模式（返回bool或None）
- [ ] 如需配置，扩展 `Configuration` 类
- [ ] 如需数据模型，使用 `Pydantic`
- [ ] 编写单元测试

