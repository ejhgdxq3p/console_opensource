# 最佳实践与常见陷阱

## 1. 初始化顺序

### ✅ 正确顺序

```python
import common.runtime as rt

# 1. 首先设置服务名（在获取logger之前！）
rt.set_service_name("my_service")

# 2. 然后获取logger
import common.logger as logger
log = logger.get_logger()

# 3. 重定向输出
import sys
sys.stdout = logger.LoggerStdCapture(log.info)
sys.stderr = logger.LoggerStdCapture(log.warning)

# 4. 最后导入其他模块
from common.constants import *
import common.queue as queue
```

### ❌ 错误顺序

```python
import common.logger as logger
log = logger.get_logger()  # ❌ 服务名还是"unknown"

import common.runtime as rt
rt.set_service_name("my_service")  # ❌ 太晚了，logger已创建
```

## 2. 文件锁使用

### ✅ 正确使用

```python
def safe_file_operation(folder):
    lock_file = Path(folder) / mri4all_files.LOCK
    
    try:
        lock = helper.FileLock(lock_file)
    except:
        log.error("Cannot acquire lock")
        return False
    
    try:
        # 执行操作
        do_something()
        return True
    except Exception as e:
        log.exception(e)
        return False
    finally:
        lock.free()  # 确保释放锁
```

### ❌ 常见错误

```python
def unsafe_operation(folder):
    lock_file = Path(folder) / mri4all_files.LOCK
    lock = helper.FileLock(lock_file)
    
    do_something()  # 如果这里抛异常，锁不会释放
    lock.free()
```

## 3. 任务状态检查

### ✅ 完整检查

```python
def get_scan_ready_for_acq() -> str:
    for entry in folders:
        if (
            entry.is_dir()                                      # 是目录
            and (entry / mri4all_files.PREPARED).exists()       # 已准备
            and not (entry / mri4all_files.EDITING).exists()    # 未编辑中
            and not (entry / mri4all_files.LOCK).exists()       # 未锁定
        ):
            return entry.name
    return ""
```

### ❌ 不完整检查

```python
def get_scan_ready_for_acq() -> str:
    for entry in folders:
        if (entry / mri4all_files.PREPARED).exists():  # ❌ 可能正在编辑或锁定
            return entry.name
```

## 4. Pydantic模型使用

### ✅ 正确的模型操作

```python
# 从JSON创建
with open(file, "r") as f:
    scan_task = ScanTask(**json.load(f))

# 或使用model_validate_json
with open(file, "r") as f:
    scan_task = ScanTask.model_validate_json(f.read())

# 导出为字典
data = scan_task.model_dump()

# 导出为JSON
json_str = scan_task.model_dump_json(indent=4)
```

### ❌ 直接修改嵌套字典

```python
# ❌ 不要这样做
scan_task.parameters["TR"] = 500  # 如果parameters不存在会出错

# ✅ 安全方式
if "TR" in scan_task.parameters:
    scan_task.parameters["TR"] = 500
else:
    scan_task.parameters = {"TR": 500}
```

## 5. 路径处理

### ✅ 使用Path和os.path

```python
from pathlib import Path
import os

# 组合路径
folder = Path(mri4all_paths.DATA_ACQ) / scan_name / mri4all_files.TASK

# 或使用os.path
folder = os.path.join(mri4all_paths.DATA_ACQ, scan_name, mri4all_files.TASK)

# 检查存在
if folder.exists():
    pass
if os.path.isfile(folder):
    pass
```

### ❌ 字符串拼接

```python
# ❌ 不安全，跨平台问题
folder = mri4all_paths.DATA_ACQ + "/" + scan_name + "/" + mri4all_files.TASK
```

## 6. 序列参数验证

### ✅ 完整验证

```python
def set_parameters(self, parameters, scan_task) -> bool:
    self.problem_list = []  # 重置问题列表
    
    # 检查必需参数
    try:
        self.param_tr = parameters["TR"]
        self.param_te = parameters["TE"]
    except KeyError as e:
        self.problem_list.append(f"Missing required parameter: {e}")
        return False
    
    # 验证参数范围
    if self.param_tr < self.param_te:
        self.problem_list.append("TR must be greater than TE")
    
    if self.param_tr < 10 or self.param_tr > 10000:
        self.problem_list.append("TR must be between 10 and 10000 ms")
    
    return self.is_valid()  # len(self.problem_list) == 0
```

### ❌ 无验证

```python
def set_parameters(self, parameters, scan_task) -> bool:
    self.param_tr = parameters["TR"]  # ❌ 可能KeyError
    self.param_te = parameters["TE"]
    return True  # ❌ 没有验证
```

## 7. IPC通信

### ✅ 检查Windows兼容性

```python
from common.ipc import Communicator
import platform

IS_WINDOWS = platform.system() == "Windows"

if not IS_WINDOWS:
    communicator = Communicator(Communicator.ACQ)
    communicator.send_status("Processing...")
else:
    # Windows下跳过IPC
    log.info("IPC disabled on Windows")
```

### ✅ Communicator内部已处理

```python
# Communicator类内部已经处理了Windows兼容性
class Communicator:
    def __init__(self, pipe_end):
        self._disabled = IS_WINDOWS
        if self._disabled:
            return  # 跳过初始化
    
    def send_status(self, message):
        if self._disabled:
            return False  # 静默失败
        # ...正常发送
```

## 8. 异步操作

### ✅ 正确的异步处理

```python
async def terminate_process(signalNumber, frame) -> None:
    log.info("Shutdown requested")
    if "main_loop" in globals() and main_loop.is_running:
        main_loop.stop()
    helper.trigger_terminate()

# 注册信号
for s in (signal.SIGTERM, signal.SIGINT):
    helper.loop.add_signal_handler(
        s, lambda s=s: asyncio.create_task(terminate_process(s, helper.loop))
    )

# 清理未完成的任务
finally:
    remaining_tasks = asyncio.all_tasks(helper.loop)
    if remaining_tasks:
        helper.loop.run_until_complete(asyncio.gather(*remaining_tasks))
```

## 9. UI更新

### ✅ 使用信号槽更新UI

```python
class MyWindow(QMainWindow):
    def __init__(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_status)
        self.timer.start(1000)
    
    def update_status(self):
        # 在主线程中更新UI
        self.statusLabel.setText("Updated")
```

### ❌ 从其他线程直接更新

```python
# ❌ 不要从非主线程直接更新UI
def background_task():
    # 这会导致崩溃
    self.statusLabel.setText("Updated")

# ✅ 使用信号
class MyWindow(QMainWindow):
    status_changed = pyqtSignal(str)
    
    def __init__(self):
        self.status_changed.connect(self.statusLabel.setText)
    
    def background_task(self):
        self.status_changed.emit("Updated")  # 安全
```

## 10. 错误处理模式

### ✅ 返回布尔值 + 日志

```python
def some_operation() -> bool:
    try:
        do_something()
        return True
    except SpecificException as e:
        log.error(f"Operation failed: {e}")
        return False
    except Exception as e:
        log.exception(e)  # 记录完整堆栈
        return False
```

### ✅ 返回Optional + 日志

```python
def get_something() -> Optional[SomeThing]:
    try:
        return do_something()
    except Exception as e:
        log.error(f"Failed to get something: {e}")
        return None
```

### ❌ 静默失败

```python
def bad_operation():
    try:
        do_something()
    except:
        pass  # ❌ 静默吞掉错误
```

## 11. 配置访问

### ✅ 每次需要时重新加载

```python
def process_task():
    # 重新加载配置，获取最新设置
    config.load_config()
    cfg = config.get_config()
    
    if cfg.is_hardware_simulation():
        # 模拟模式
        pass
```

### ❌ 启动时加载一次

```python
# ❌ 配置可能在运行时改变
cfg = config.get_config()  # 只在启动时获取一次

def process_task():
    if cfg.is_hardware_simulation():  # ❌ 可能是过时的配置
        pass
```

## 12. 资源清理

### ✅ 使用try-finally

```python
def process_with_cleanup():
    resource = None
    try:
        resource = acquire_resource()
        do_something(resource)
    finally:
        if resource:
            release_resource(resource)
```

### ✅ 上下文管理器

```python
class ManagedResource:
    def __enter__(self):
        self.resource = acquire_resource()
        return self.resource
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        release_resource(self.resource)
        return False

# 使用
with ManagedResource() as resource:
    do_something(resource)
```

## 13. 常见陷阱速查表

| 陷阱 | 症状 | 解决方案 |
|------|------|----------|
| Logger初始化顺序 | 日志显示"unknown"服务名 | 先设置`rt.set_service_name()` |
| 文件锁未释放 | 任务永久锁定 | 使用try-finally释放锁 |
| Windows IPC | 程序崩溃 | 检查`platform.system()` |
| UI线程更新 | 随机崩溃 | 使用信号槽机制 |
| 路径分隔符 | Windows路径错误 | 使用`Path`或`os.path.join` |
| 配置过时 | 设置不生效 | 每次使用前`load_config()` |
| 异步任务泄漏 | 程序无法退出 | 清理`asyncio.all_tasks()` |
| 参数未验证 | 运行时错误 | 在`set_parameters`中验证 |

## 14. 调试技巧

### 启用调试模式

```bash
# 环境变量
export MRI4ALL_DEBUG=true
export MRI4ALL_LOG_LEVEL=debug
```

```python
# 代码中
import common.runtime as rt
rt.set_debug(True)
```

### 查看日志

```bash
# 日志位置
<base_path>/logs/ui.log
<base_path>/logs/acq.log
<base_path>/logs/recon.log
```

### 检查任务状态

```bash
# 查看任务文件
cat <data_path>/acq_queue/<task_name>/scan.json

# 查看状态文件
ls <data_path>/acq_queue/<task_name>/
# LOCK, PREPARED, EDITING
```

