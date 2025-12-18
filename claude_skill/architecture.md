# 系统架构设计

## 1. 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              MRI4ALL Console                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐               │
│  │   UI Service │      │  ACQ Service │      │ RECON Service│               │
│  │   (PyQt5)    │      │  (Asyncio)   │      │  (Asyncio)   │               │
│  └──────┬───────┘      └──────┬───────┘      └──────┬───────┘               │
│         │                     │                     │                        │
│         └─────────────────────┼─────────────────────┘                        │
│                               │                                              │
│  ┌────────────────────────────┴────────────────────────────────────────┐    │
│  │                        Common Module                                  │    │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐        │    │
│  │  │ config  │ │ logger  │ │  types  │ │  task   │ │  queue  │        │    │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘        │    │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                    │    │
│  │  │ runtime │ │ helper  │ │constants│ │   ipc   │                    │    │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘                    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     File-based Queue System                          │    │
│  │                                                                       │    │
│  │   acq_queue → acq → recon_queue → recon → complete/failure           │    │
│  │                                                                       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2. 目录结构

```
console_opensource/
├── common/                     # 共享模块 - 所有服务都使用
│   ├── __init__.py
│   ├── config.py              # 配置管理 (Pydantic)
│   ├── constants.py           # 常量定义 (路径、状态、文件名)
│   ├── helper.py              # 工具函数 (UUID、时间、锁文件)
│   ├── logger.py              # 日志系统 (RotatingFileHandler)
│   ├── queue.py               # 队列操作 (文件夹移动、状态检查)
│   ├── runtime.py             # 运行时状态 (服务名、路径)
│   ├── state.py               # 状态管理
│   ├── task.py                # 任务CRUD操作
│   ├── types.py               # 数据类型定义 (Pydantic Models)
│   ├── version.py             # 语义化版本管理
│   └── ipc/                   # 进程间通信
│       ├── ipc.py             # 命名管道通信器
│       └── messages.py        # 消息类型定义
│
├── services/                   # 服务模块
│   ├── ui/                    # UI服务 (PyQt5)
│   │   ├── main.py            # 入口点
│   │   ├── registration.py    # 患者注册窗口
│   │   ├── examination.py     # 检查窗口
│   │   ├── ui_runtime.py      # UI运行时状态
│   │   ├── forms/             # Qt Designer UI文件 (.ui)
│   │   └── assets/            # 图片资源
│   │
│   ├── acq/                   # 采集服务
│   │   └── main.py            # 采集循环
│   │
│   └── recon/                 # 重建服务
│       ├── main.py            # 重建循环
│       ├── reconstruction.py  # 重建算法
│       └── utils.py           # 工具函数
│
├── sequences/                  # MRI序列 (插件式)
│   ├── __init__.py            # SequenceBase基类 + 自动加载
│   ├── FID.py                 # FID序列示例
│   ├── se_2D.py               # 2D自旋回波
│   ├── tse_3D.py              # 3D TSE
│   └── common/                # 序列共享代码
│
├── recon/                      # 重建算法库
│   ├── B0Correction/          # B0校正
│   ├── DICOM/                 # DICOM写入
│   ├── kspaceFiltering/       # k空间滤波
│   └── image_filters/         # 图像滤波
│
├── external/                   # 外部依赖
│   ├── marcos_client/         # MaRCoS硬件客户端
│   ├── pypulseq/              # Pulseq序列库
│   └── sigpy/                 # 信号处理库
│
├── run_ui.py                   # UI启动脚本
├── run_acq.py                  # 采集服务启动脚本
├── run_recon.py                # 重建服务启动脚本
└── requirements.txt            # Python依赖
```

## 3. 数据流

### 3.1 扫描任务生命周期

```
[创建] → [acq_queue] → [acq] → [recon_queue] → [recon] → [complete]
                                                           ↓
                                                       [failure]
```

### 3.2 状态流转

```python
ScanStatesType = Literal[
    "created",          # 任务已创建，未准备好
    "scheduled_acq",    # 已加入采集队列
    "acq",              # 正在采集
    "scheduled_recon",  # 已加入重建队列
    "recon",            # 正在重建
    "complete",         # 完成
    "failure",          # 失败
]
```

### 3.3 文件夹结构 (单个扫描任务)

```
{exam_id}#scan_{counter}/
├── scan.json              # 任务定义文件
├── LOCK                   # 锁文件 (可选)
├── PREPARED               # 准备就绪标志
├── EDITING                # 正在编辑标志
├── seq/                   # 序列文件 (.seq)
├── rawdata/               # 原始数据
│   ├── raw.npy
│   ├── pe_order.npy
│   └── traj.csv
├── dicom/                 # DICOM输出
├── temp/                  # 临时文件
└── other/                 # 其他结果
```

## 4. 服务通信

### 4.1 基于文件的队列

服务间通过监控文件夹实现松耦合通信：

```python
# ACQ服务检查是否有待处理任务
def get_scan_ready_for_acq() -> str:
    folders = sorted(Path(mri4all_paths.DATA_QUEUE_ACQ).iterdir(), key=os.path.getmtime)
    for entry in folders:
        if (
            entry.is_dir()
            and (entry / mri4all_files.PREPARED).exists()      # 已准备好
            and (not (entry / mri4all_files.EDITING).exists())  # 未在编辑
            and (not (entry / mri4all_files.LOCK).exists())     # 未被锁定
        ):
            return entry.name
    return ""
```

### 4.2 IPC通信 (仅Linux)

用于UI与服务间的实时通信：

```python
# 服务端发送状态
communicator = Communicator(Communicator.ACQ)
communicator.send_status("Calculating sequence...")

# UI接收并显示
communicator.received.connect(self.handle_message)
```

## 5. 配置管理

### 5.1 配置类 (Pydantic)

```python
class Configuration(BaseModel):
    scanner_ip: str = Field(default="10.42.0.251", description="Scanner IP")
    debug_mode: str = Field(default="False", description="Debug Mode")
    hardware_simulation: str = Field(default="False", description="Hardware Simulation")
    dicom_targets: List[DicomTarget] = []
    
    @classmethod
    def load_from_file(cls):
        # 从JSON加载配置
        pass
    
    def save_to_file(self):
        # 保存到JSON
        pass
```

### 5.2 路径常量

```python
class mri4all_paths:
    BASE = rt.get_base_path()
    DATA = os.path.join(BASE, "data")
    DATA_QUEUE_ACQ = os.path.join(DATA, "acq_queue")
    DATA_ACQ = os.path.join(DATA, "acq")
    DATA_QUEUE_RECON = os.path.join(DATA, "recon_queue")
    DATA_RECON = os.path.join(DATA, "recon")
    DATA_COMPLETE = os.path.join(DATA, "complete")
    DATA_FAILURE = os.path.join(DATA, "failure")
```

## 6. 运行时环境

### 6.1 路径检测

```python
def _get_paths():
    if getattr(sys, 'frozen', False):
        # PyInstaller打包模式
        bundle_dir = sys._MEIPASS
        exe_dir = os.path.dirname(sys.executable)
        return bundle_dir, exe_dir
    else:
        # 开发模式
        console_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        base_path = os.path.dirname(console_path)
        return console_path, base_path
```

### 6.2 服务标识

```python
# 每个服务启动时设置
rt.set_service_name("ui")      # UI服务
rt.set_service_name("acq")     # 采集服务
rt.set_service_name("recon")   # 重建服务
```

## 7. 跨平台支持

### Windows兼容性处理

```python
IS_WINDOWS = platform.system() == "Windows"

class Communicator:
    def __init__(self, pipe_end: PipeEnd):
        self._disabled = IS_WINDOWS  # Windows禁用IPC
        if self._disabled:
            log.info("IPC disabled on Windows (mkfifo not supported)")
            return
        # Linux正常初始化
```

