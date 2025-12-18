# 服务开发指南

## 1. 服务架构

MRI4ALL包含三个独立服务：

```
┌─────────────────────────────────────────────────────────────┐
│                          服务层                              │
├───────────────┬───────────────┬─────────────────────────────┤
│   UI Service  │  ACQ Service  │       RECON Service         │
│   (PyQt5)     │  (Asyncio)    │       (Asyncio)             │
│               │               │                             │
│ • 用户界面    │ • 序列执行    │ • 图像重建                  │
│ • 患者注册    │ • 硬件控制    │ • DICOM生成                 │
│ • 协议编辑    │ • 数据采集    │ • 后处理                    │
└───────────────┴───────────────┴─────────────────────────────┘
```

## 2. 服务模板

### 基本结构

```python
# services/myservice/main.py

import os
import sys
import signal
import asyncio

import common.logger as logger
import common.runtime as rt

# 1. 设置服务名称（必须在获取logger之前）
rt.set_service_name("myservice")
log = logger.get_logger()

# 2. 重定向输出
sys.stdout = logger.LoggerStdCapture(log.info)
sys.stderr = logger.LoggerStdCapture(log.warning)

# 3. 导入其他模块
import common.helper as helper
from common.version import mri4all_version
import common.queue as queue
from common.constants import *

# 全局变量
main_loop = None


def process_task(task_name: str) -> bool:
    """处理单个任务"""
    log.info(f"Processing task: {task_name}")
    
    try:
        # 执行任务逻辑
        pass
    except Exception as e:
        log.exception(e)
        return False
    
    return True


def run_main_loop():
    """主处理循环"""
    # 检查是否有待处理任务
    selected_task = get_next_task()
    
    if selected_task:
        log.info(f"Processing: {selected_task}")
        rt.set_current_task_id(selected_task)
        
        process_task(selected_task)
        
        rt.clear_current_task_id()
    
    if helper.is_terminated():
        return


async def terminate_process(signalNumber, frame) -> None:
    """处理终止信号"""
    log.info("Shutdown requested")
    if "main_loop" in globals() and main_loop.is_running:
        main_loop.stop()
    helper.trigger_terminate()


def prepare_service() -> bool:
    """服务初始化"""
    log.info("Preparing service...")
    
    if not queue.check_and_create_folders():
        log.error("Failed to create data folders")
        return False
    
    return True


def run():
    """服务入口点"""
    log.info(f"-- MRI4ALL {mri4all_version.get_version_string()} --")
    log.info("MyService started")
    
    if not prepare_service():
        log.error("Service preparation failed")
        sys.exit(1)
    
    # 注册信号处理
    signals = (signal.SIGTERM, signal.SIGINT)
    for s in signals:
        helper.loop.add_signal_handler(
            s, lambda s=s: asyncio.create_task(terminate_process(s, helper.loop))
        )
    
    # 启动主循环
    global main_loop
    main_loop = helper.AsyncTimer(0.1, run_main_loop)  # 100ms间隔
    
    try:
        main_loop.run_until_complete(helper.loop)
    except Exception as e:
        log.exception(e)
    finally:
        remaining_tasks = asyncio.all_tasks(helper.loop)
        if remaining_tasks:
            helper.loop.run_until_complete(asyncio.gather(*remaining_tasks))
    
    log.info("MyService terminated")
    sys.exit()


if __name__ == "__main__":
    run()
```

## 3. 采集服务 (ACQ)

### 核心流程

```python
def process_acquisition(scan_name: str) -> bool:
    """执行采集"""
    
    # 1. 读取任务定义
    scan_task = task.read_task(mri4all_paths.DATA_ACQ + "/" + scan_name)
    
    # 2. 记录开始时间
    scan_task.journal.acquisition_start = helper.get_datetime()
    task.write_task(folder, scan_task)
    
    # 3. 获取序列实例
    seq_instance = SequenceBase.get_sequence(scan_task.sequence)()
    
    # 4. 配置序列
    seq_instance.set_working_folder(folder)
    seq_instance.set_parameters(scan_task.parameters, scan_task)
    
    # 5. 计算序列
    seq_instance.calculate_sequence(scan_task)
    
    # 6. 执行序列
    seq_instance.run_sequence(scan_task)
    
    # 7. 记录结束时间
    scan_task.journal.acquisition_end = helper.get_datetime()
    task.write_task(folder, scan_task)
    
    # 8. 移动到重建队列
    queue.move_task(folder, mri4all_paths.DATA_QUEUE_RECON)
    
    return True
```

### 任务队列检查

```python
def get_scan_ready_for_acq() -> str:
    """获取准备好采集的扫描"""
    folders = sorted(
        Path(mri4all_paths.DATA_QUEUE_ACQ).iterdir(), 
        key=os.path.getmtime
    )
    
    for entry in folders:
        if (
            entry.is_dir()
            and (entry / mri4all_files.PREPARED).exists()    # 已准备
            and not (entry / mri4all_files.EDITING).exists() # 未编辑中
            and not (entry / mri4all_files.LOCK).exists()    # 未锁定
        ):
            return entry.name
    
    return ""
```

## 4. 重建服务 (RECON)

### 核心流程

```python
def process_reconstruction(scan_name: str) -> bool:
    """执行重建"""
    folder = mri4all_paths.DATA_RECON + "/" + scan_name
    
    # 1. 读取任务
    scan_task = task.read_task(folder)
    
    # 2. 记录开始时间
    scan_task.journal.reconstruction_start = helper.get_datetime()
    task.write_task(folder, scan_task)
    
    # 3. 执行重建
    if not reconstruction.run_reconstruction(folder, scan_task):
        raise Exception("Reconstruction failed")
    
    # 4. 记录结束时间
    scan_task.journal.reconstruction_end = helper.get_datetime()
    task.write_task(folder, scan_task)
    
    # 5. 移动到完成文件夹
    queue.move_task(folder, mri4all_paths.DATA_COMPLETE)
    
    return True
```

### 重建策略选择

```python
def run_reconstruction(folder: str, task: ScanTask) -> bool:
    """根据配置选择重建方法"""
    
    if task.processing.recon_mode == "bypass":
        return True
    
    if task.processing.recon_mode == "basic3d":
        return run_reconstruction_basic3d(folder, task)
    
    if task.processing.trajectory == "cartesian":
        return run_reconstruction_cartesian(folder, task)
    
    return False
```

## 5. IPC通信

### 服务端（ACQ/RECON）

```python
from common.ipc import Communicator

# 创建通信器
communicator = Communicator(Communicator.ACQ)

# 发送状态
communicator.send_status("Calculating sequence...")

# 发送采集进度
communicator.send_acq_data(
    start_time=helper.get_datetime(),
    expected_duration_sec=60
)

# 发送警告
communicator.send_user_alert("Warning message", type="warning")

# 查询用户输入
value = communicator.query_user(
    "Enter value",
    input_type="int",
    in_min=0,
    in_max=100
)
```

### 客户端（UI）

```python
class ExaminationWindow(QMainWindow):
    def __init__(self):
        # 创建UI端通信器
        self.comm_acq = Communicator(Communicator.UI_ACQ)
        self.comm_acq.received.connect(self.handle_message)
        self.comm_acq.listen()
    
    def handle_message(self, envelope):
        """处理接收到的消息"""
        msg = envelope.value
        
        if msg.type == "set_status":
            self.update_status(msg.message)
        
        elif msg.type == "user_alert":
            self.show_alert(msg)
        
        elif msg.type == "user_query":
            response = self.get_user_input(msg)
            self.comm_acq.send_user_response(response)
```

## 6. 错误处理

### 失败任务处理

```python
def move_to_fail(scan_name: str) -> bool:
    """移动任务到失败文件夹"""
    if not queue.move_task(
        mri4all_paths.DATA_ACQ + "/" + scan_name,
        mri4all_paths.DATA_FAILURE
    ):
        log.error(f"Failed to move {scan_name} to failure folder")
        return False
    return True


def process_with_error_handling(scan_name: str) -> bool:
    try:
        return process_task(scan_name)
    except Exception as e:
        log.exception(e)
        
        # 更新任务状态
        scan_task = task.read_task(folder)
        scan_task.journal.failed_at = helper.get_datetime()
        scan_task.journal.fail_stage = "acquisition"
        task.write_task(folder, scan_task)
        
        # 移动到失败文件夹
        move_to_fail(scan_name)
        
        # 通知UI
        communicator.send_status("Scan failed.")
        
        return False
```

### 步骤追踪

```python
current_step = ""
try:
    current_step = "loading"
    data = load_data()
    
    current_step = "processing"
    result = process_data(data)
    
    current_step = "saving"
    save_result(result)
    
except Exception as e:
    log.error(f"Failed during step: {current_step}")
    log.exception(e)
    return False
```

## 7. 异步定时器

```python
class AsyncTimer:
    """异步定时器，周期性执行函数"""
    
    def __init__(self, interval: float, func):
        self.func = func
        self.time = interval
        self.is_running = False
        self._task = None
    
    def start(self) -> None:
        if not self.is_running:
            self.is_running = True
            self._task = asyncio.ensure_future(self._run())
    
    def stop(self) -> None:
        self.is_running = False
    
    async def _run(self) -> None:
        while self.is_running:
            await asyncio.sleep(self.time)
            
            if helper.is_terminated():
                self.stop()
                break
            
            # 执行函数（支持异步）
            if inspect.isawaitable(res := self.func()):
                await res
    
    def run_until_complete(self, loop=None) -> None:
        self.start()
        loop = loop or asyncio.get_event_loop()
        loop.run_until_complete(self._task)
```

## 8. 服务控制

### Linux服务控制

```python
import subprocess
import platform

def control_services(action: ServiceAction):
    """控制ACQ和RECON服务"""
    
    if platform.system() == "Windows":
        log.info("Service control skipped on Windows")
        return
    
    for service in [Service.ACQ_SERVICE, Service.RECON_SERVICE]:
        cmd = ["sudo", "systemctl", action.value, service.value]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                log.error(f"Failed to {action.value} {service.value}")
        except Exception as e:
            log.exception(e)
```

### 服务操作

```python
class ServiceAction(Enum):
    START = "start"
    STOP = "stop"
    KILL = "kill"
    STATUS = "status"

class Service(Enum):
    ACQ_SERVICE = "mri4all_acq"
    RECON_SERVICE = "mri4all_recon"
```

## 9. 日志记录

### 任务ID关联

```python
# 设置当前任务ID（会自动添加到日志）
rt.set_current_task_id(scan_name)

log.info("Processing scan")  # 日志会包含任务ID

rt.clear_current_task_id()
```

### 日志格式

```
2024-02-22 21:09:10 | acq | INF | exam123#scan_1 | Processing scan
```

## 10. 服务开发检查清单

- [ ] 设置 `rt.set_service_name()` 在获取logger之前
- [ ] 重定向 stdout/stderr 到日志
- [ ] 实现 `prepare_service()` 初始化检查
- [ ] 实现 `run_main_loop()` 主循环
- [ ] 注册信号处理器 (SIGTERM, SIGINT)
- [ ] 使用 `AsyncTimer` 周期性执行
- [ ] 实现错误处理和失败任务移动
- [ ] 使用IPC与UI通信
- [ ] 清理 asyncio 任务
- [ ] 测试优雅关闭

