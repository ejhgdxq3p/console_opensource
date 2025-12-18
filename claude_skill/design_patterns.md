# 设计模式详解

## 1. 注册器模式 (Registry Pattern)

### 用途
自动注册所有序列类，无需手动维护列表。

### 实现

```python
class SequenceBase(Generic[SequenceVar]):
    """序列基类，带自动注册功能"""
    
    _REGISTRY: Dict[str, SequenceVar] = {}  # 类级别注册表

    def __init_subclass__(cls, registry_key, **kwargs):
        """子类创建时自动调用"""
        super().__init_subclass__(**kwargs)
        if registry_key:
            cls._REGISTRY[registry_key] = cls  # 自动注册
            cls.seq_name = registry_key

    @classmethod
    def get_sequence(cls, registry_key):
        """根据key获取序列类"""
        return cls._REGISTRY[registry_key]

    @classmethod
    def installed_sequences(cls):
        """获取所有已注册序列"""
        return list(cls._REGISTRY.keys())
```

### 使用方式

```python
# 定义序列时自动注册
class SequenceFID(PulseqSequence, registry_key=Path(__file__).stem):
    pass

# 获取序列
seq_class = SequenceBase.get_sequence("FID")
seq_instance = seq_class()

# 列出所有序列
all_sequences = SequenceBase.installed_sequences()
```

### 自动导入机制

```python
# sequences/__init__.py 末尾
for f in Path(__file__).parent.glob("*.py"):
    module_name = f.stem
    if (not module_name.startswith("_")) and (module_name not in globals()):
        import_module(f".{module_name}", __package__)
```

## 2. 工厂模式 (Factory Pattern)

### 用途
根据配置动态创建序列实例。

### 实现

```python
# 工厂方法：根据名称创建序列实例
def create_sequence_instance(sequence_name: str) -> SequenceBase:
    """
    根据序列名称创建实例
    """
    if sequence_name not in SequenceBase.installed_sequences():
        raise ValueError(f"Unknown sequence: {sequence_name}")
    
    seq_class = SequenceBase.get_sequence(sequence_name)
    return seq_class()

# 使用
seq_instance = SequenceBase.get_sequence(scan_task.sequence)()
seq_instance.set_working_folder(working_folder)
seq_instance.set_parameters(parameters, scan_task)
```

## 3. 单例模式 (Singleton Pattern)

### 用途
全局唯一的配置和运行时状态。

### 实现方式1：模块级单例

```python
# common/config.py
mri4all_config_instance = None

def get_config():
    return mri4all_config_instance

def load_config():
    global mri4all_config_instance
    mri4all_config_instance = Configuration.load_from_file()
```

### 实现方式2：全局变量

```python
# common/runtime.py
service_name = "unknown"
current_task_id = ""
base_path = None
debugging_enabled = False

def set_service_name(name):
    global service_name
    service_name = name

def get_service_name():
    return service_name
```

### 实现方式3：类实例单例

```python
# common/version.py
class SemanticVersion:
    # 类实现...
    pass

# 模块级唯一实例
mri4all_version = SemanticVersion()
```

## 4. 状态机模式 (State Machine Pattern)

### 用途
管理扫描任务的生命周期状态。

### 状态定义

```python
ScanStatesType = Literal[
    "created",          # 初始状态
    "scheduled_acq",    # 等待采集
    "acq",              # 采集中
    "scheduled_recon",  # 等待重建
    "recon",            # 重建中
    "complete",         # 完成
    "failure",          # 失败
]
```

### 状态转换

```
                    ┌─────────────┐
                    │   created   │
                    └──────┬──────┘
                           │ set PREPARED flag
                           ▼
                    ┌─────────────────┐
                    │ scheduled_acq   │
                    └──────┬──────────┘
                           │ move to acq folder
                           ▼
                    ┌─────────────┐
              ┌─────│     acq     │─────┐
              │     └──────┬──────┘     │
              │            │            │
              │ success    │            │ failure
              ▼            ▼            ▼
    ┌─────────────────┐         ┌─────────────┐
    │ scheduled_recon │         │   failure   │
    └──────┬──────────┘         └─────────────┘
           │ move to recon folder
           ▼
    ┌─────────────┐
    │    recon    │─────┐
    └──────┬──────┘     │
           │            │ failure
           │ success    │
           ▼            ▼
    ┌─────────────┐  ┌─────────────┐
    │  complete   │  │   failure   │
    └─────────────┘  └─────────────┘
```

### 状态检查实现

```python
def update_scan_queue_list() -> bool:
    for entry in scan_queue_list:
        folder = entry.folder_name
        current_state = ""

        # 根据文件夹位置确定状态
        if os.path.isdir(mri4all_paths.DATA_QUEUE_ACQ + "/" + folder):
            if os.path.isfile(mri4all_paths.DATA_QUEUE_ACQ + "/" + folder + "/" + mri4all_files.PREPARED):
                current_state = mri4all_states.SCHEDULED_ACQ
            else:
                current_state = mri4all_states.CREATED
        
        if os.path.isdir(mri4all_paths.DATA_ACQ + "/" + folder):
            current_state = mri4all_states.ACQ
        
        # ... 其他状态检查
        
        entry.state = cast(ScanStatesType, current_state)
```

## 5. 观察者模式 (Observer Pattern)

### 用途
UI响应服务状态变化。

### 实现 (PyQt5信号槽)

```python
class Communicator(QObject, Helper):
    """IPC通信器，继承QObject以使用信号"""
    
    # 定义信号
    received = pyqtSignal(object)
    
    def _listen_emit(self):
        """监听线程，接收消息后发射信号"""
        for message in self._listen():
            self.received.emit(message)

# UI端订阅
class ExaminationWindow(QMainWindow):
    def __init__(self):
        self.communicator = Communicator(Communicator.UI_ACQ)
        self.communicator.received.connect(self.handle_message)
        self.communicator.listen()
    
    def handle_message(self, envelope):
        """处理接收到的消息"""
        if envelope.value.type == "set_status":
            self.update_status_bar(envelope.value.message)
```

## 6. 模板方法模式 (Template Method Pattern)

### 用途
定义序列的标准执行流程，子类实现具体步骤。

### 基类模板

```python
class SequenceBase:
    """序列基类定义执行模板"""
    
    # 模板方法定义的步骤（子类必须实现）
    
    def get_readable_name(self) -> str:
        """返回序列可读名称 - 子类必须实现"""
        return "INVALID"
    
    def get_default_parameters(self) -> dict:
        """返回默认参数 - 子类必须实现"""
        return {}
    
    def set_parameters(self, parameters, scan_task) -> bool:
        """设置参数 - 子类必须实现"""
        return True
    
    def calculate_sequence(self, scan_task) -> bool:
        """计算序列 - 子类必须实现"""
        return True
    
    def run_sequence(self, scan_task) -> bool:
        """执行序列 - 子类必须实现"""
        return True
    
    # 公共方法（所有序列共享）
    
    def set_working_folder(self, folder: str) -> bool:
        """设置工作目录 - 基类实现"""
        self.working_folder = folder
        # 创建必要的子目录...
        return True
    
    def is_valid(self) -> bool:
        """检查参数是否有效"""
        return len(self.problem_list) == 0
```

### 子类实现

```python
class SequenceFID(PulseqSequence, registry_key="FID"):
    
    @classmethod
    def get_readable_name(self) -> str:
        return "FID"
    
    @classmethod
    def get_default_parameters(self) -> dict:
        return {"FA": 90, "ADC_samples": 4096}
    
    def set_parameters(self, parameters, scan_task) -> bool:
        self.param_FA = parameters["FA"]
        return self.validate_parameters(scan_task)
    
    def calculate_sequence(self, scan_task) -> bool:
        # 实现Pulseq序列计算
        return self.generate_pulseq()
    
    def run_sequence(self, scan_task) -> bool:
        # 执行采集
        return True
```

## 7. 策略模式 (Strategy Pattern)

### 用途
根据处理模式选择不同的重建算法。

### 实现

```python
def run_reconstruction(folder: str, task: ScanTask) -> bool:
    """根据配置选择重建策略"""
    
    if task.processing.recon_mode == "bypass":
        # 策略1：跳过重建
        log.info("Bypassing reconstruction")
        return True

    if task.processing.recon_mode == "fake_dicoms":
        # 策略2：生成假DICOM
        utils.generate_fake_dicoms(folder, task)
        return True

    if task.processing.recon_mode == "basic3d":
        # 策略3：基础3D重建
        run_reconstruction_basic3d(folder, task)
        return True

    if task.processing.trajectory == "cartesian":
        # 策略4：笛卡尔轨迹重建
        run_reconstruction_cartesian(folder, task)
        return True

    log.error(f"Unknown trajectory: {task.processing.trajectory}")
    return False
```

## 8. 消息模式 (Message Pattern)

### 用途
服务间类型安全的消息传递。

### 消息基类

```python
class FifoMessageType(BaseModel):
    """消息基类"""
    pass

class SetStatusMessage(FifoMessageType):
    type: Literal["set_status"] = "set_status"
    message: str

class UserQueryMessage(FifoMessageType):
    type: Literal["user_query"] = "user_query"
    input_type: Literal["text", "int", "float"] = "text"
    in_min: Union[float, int] = 0
    in_max: Union[float, int] = 1000
    request: str

class UserAlertMessage(FifoMessageType):
    type: Literal["user_alert"] = "user_alert"
    message: str
    alert_type: Literal["information", "warning", "critical"] = "information"
```

### 消息封装

```python
class CommunicatorEnvelope(BaseModel):
    """消息信封，包含ID和错误标志"""
    id: str = str(uuid.uuid1())
    value: Union[
        UserResponseMessage,
        UserQueryMessage,
        UserAlertMessage,
        SetStatusMessage,
        # ...
    ]
    error: bool = False
```

## 9. 模式应用场景总结

| 模式 | 应用场景 | 文件位置 |
|------|----------|----------|
| 注册器 | 序列自动注册 | `sequences/__init__.py` |
| 工厂 | 创建序列实例 | `services/acq/main.py` |
| 单例 | 配置、运行时状态 | `common/config.py`, `common/runtime.py` |
| 状态机 | 任务生命周期 | `services/ui/ui_runtime.py` |
| 观察者 | UI更新 | `common/ipc/ipc.py` |
| 模板方法 | 序列执行流程 | `sequences/__init__.py` |
| 策略 | 重建算法选择 | `services/recon/reconstruction.py` |
| 消息 | IPC通信 | `common/ipc/messages.py` |

