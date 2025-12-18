# 序列开发指南

## 1. 序列架构概览

```
sequences/
├── __init__.py          # SequenceBase基类 + 自动加载
├── FID.py               # FID序列 (最简单的示例)
├── se_2D.py             # 2D自旋回波
├── tse_3D.py            # 3D TSE
├── adj_frequency.py     # 调整序列 (adj_前缀)
├── FID/                  # 序列资源文件夹
│   └── interface.ui     # Qt Designer UI文件
└── common/              # 共享代码
    ├── make_tse_3D.py
    └── get_trajectory.py
```

## 2. 创建新序列步骤

### 步骤1：创建序列文件

```python
# sequences/my_sequence.py

import os
from pathlib import Path
from PyQt5 import uic
import pypulseq as pp

from sequences import PulseqSequence
import common.logger as logger
from common.types import ResultItem
from common.ipc import Communicator

log = logger.get_logger()
ipc_comm = Communicator(Communicator.ACQ)


class MySequence(PulseqSequence, registry_key=Path(__file__).stem):
    """
    我的自定义序列
    
    registry_key=Path(__file__).stem 使用文件名作为注册键
    这意味着序列会以 "my_sequence" 注册
    """
    
    # 1. 定义序列参数
    param_tr: int = 500
    param_te: int = 20
    param_flip_angle: int = 90
    
    # 2. 实现必要的方法...
```

### 步骤2：实现元信息方法

```python
@classmethod
def get_readable_name(self) -> str:
    """UI中显示的名称"""
    return "My Custom Sequence"

@classmethod
def get_description(self) -> str:
    """鼠标悬停时显示的描述"""
    return "A custom MRI sequence for demonstration"
```

### 步骤3：实现参数管理

```python
def get_parameters(self) -> dict:
    """返回当前参数"""
    return {
        "TR": self.param_tr,
        "TE": self.param_te,
        "FlipAngle": self.param_flip_angle,
    }

@classmethod
def get_default_parameters(self) -> dict:
    """返回默认参数（用于新建协议）"""
    return {
        "TR": 500,
        "TE": 20,
        "FlipAngle": 90,
    }

def set_parameters(self, parameters: dict, scan_task) -> bool:
    """从字典设置参数"""
    self.problem_list = []  # 清空问题列表
    
    try:
        self.param_tr = parameters["TR"]
        self.param_te = parameters["TE"]
        self.param_flip_angle = parameters["FlipAngle"]
    except KeyError as e:
        self.problem_list.append(f"Missing parameter: {e}")
        return False
    
    return self.validate_parameters(scan_task)

def validate_parameters(self, scan_task) -> bool:
    """验证参数有效性"""
    if self.param_tr < self.param_te:
        self.problem_list.append("TR must be greater than TE")
    
    if self.param_flip_angle < 1 or self.param_flip_angle > 180:
        self.problem_list.append("Flip angle must be between 1 and 180")
    
    return self.is_valid()
```

### 步骤4：实现UI交互

```python
def setup_ui(self, widget) -> bool:
    """加载UI文件"""
    seq_path = os.path.dirname(os.path.abspath(__file__))
    uic.loadUi(f"{seq_path}/{self.get_name()}/interface.ui", widget)
    return True

def write_parameters_to_ui(self, widget) -> bool:
    """将参数写入UI控件"""
    widget.TR_SpinBox.setValue(self.param_tr)
    widget.TE_SpinBox.setValue(self.param_te)
    widget.FlipAngle_SpinBox.setValue(self.param_flip_angle)
    return True

def read_parameters_from_ui(self, widget, scan_task) -> bool:
    """从UI控件读取参数"""
    self.problem_list = []
    self.param_tr = widget.TR_SpinBox.value()
    self.param_te = widget.TE_SpinBox.value()
    self.param_flip_angle = widget.FlipAngle_SpinBox.value()
    return self.validate_parameters(scan_task)
```

### 步骤5：实现序列计算

```python
def calculate_sequence(self, scan_task) -> bool:
    """计算Pulseq序列"""
    log.info(f"Calculating sequence {self.get_name()}")
    ipc_comm.send_status("Calculating sequence...")
    
    # 设置重建模式
    scan_task.processing.recon_mode = "cartesian"
    scan_task.processing.trajectory = "cartesian"
    
    # 设置输出文件路径
    self.seq_file_path = self.get_working_folder() + "/seq/acq0.seq"
    
    try:
        if not self._generate_pulseq():
            log.error("Failed to generate Pulseq sequence")
            return False
    except Exception as e:
        log.exception(e)
        return False
    
    self.calculated = True
    log.info("Sequence calculation completed")
    return True

def _generate_pulseq(self) -> bool:
    """生成Pulseq序列文件"""
    # 创建序列对象
    seq = pp.Sequence()
    
    # 设置系统参数
    system = pp.Opts(
        max_grad=100, grad_unit="mT/m",
        max_slew=4000, slew_unit="T/m/s",
        rf_ringdown_time=20e-6,
        rf_dead_time=100e-6,
    )
    
    # 创建RF脉冲
    rf = pp.make_block_pulse(
        flip_angle=self.param_flip_angle * 3.14159 / 180,
        duration=200e-6,
        system=system,
    )
    
    # 创建ADC
    adc = pp.make_adc(num_samples=256, duration=3.2e-3, system=system)
    
    # 构建序列
    seq.add_block(rf)
    seq.add_block(pp.make_delay(self.param_te / 1000))
    seq.add_block(adc)
    seq.add_block(pp.make_delay(self.param_tr / 1000 - self.param_te / 1000))
    
    # 检查时序
    ok, error_report = seq.check_timing()
    if not ok:
        for e in error_report:
            log.error(e)
        return False
    
    # 写入文件
    seq.write(self.seq_file_path)
    return True
```

### 步骤6：实现序列执行

```python
def run_sequence(self, scan_task) -> bool:
    """执行序列采集"""
    log.info(f"Running sequence {self.get_name()}")
    ipc_comm.send_status("Preparing scan...")
    
    from external.seq.adjustments_acq.scripts import run_pulseq
    import external.seq.adjustments_acq.config as cfg
    
    try:
        # 执行Pulseq序列
        rxd, rx_t = run_pulseq(
            seq_file=self.seq_file_path,
            rf_center=cfg.LARMOR_FREQ,
            tx_t=1,
            grad_t=10,
            tx_warmup=100,
            shim_x=scan_task.adjustment.shim.shim_x,
            shim_y=scan_task.adjustment.shim.shim_y,
            shim_z=scan_task.adjustment.shim.shim_z,
            case_path=self.get_working_folder(),
            raw_filename="raw",
        )
    except Exception as e:
        log.exception(e)
        return False
    
    # 保存原始数据
    import numpy as np
    np.save(self.get_working_folder() + "/rawdata/raw.npy", rxd)
    
    log.info("Sequence execution completed")
    return True
```

## 3. UI文件创建

### 创建UI文件夹

```
sequences/my_sequence/
└── interface.ui
```

### Qt Designer UI文件示例

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>Form</class>
 <widget class="QWidget" name="Form">
  <layout class="QFormLayout" name="formLayout">
   <item row="0" column="0">
    <widget class="QLabel" name="label_TR">
     <property name="text"><string>TR (ms)</string></property>
    </widget>
   </item>
   <item row="0" column="1">
    <widget class="QSpinBox" name="TR_SpinBox">
     <property name="minimum"><number>10</number></property>
     <property name="maximum"><number>10000</number></property>
     <property name="value"><number>500</number></property>
    </widget>
   </item>
   <item row="1" column="0">
    <widget class="QLabel" name="label_TE">
     <property name="text"><string>TE (ms)</string></property>
    </widget>
   </item>
   <item row="1" column="1">
    <widget class="QSpinBox" name="TE_SpinBox">
     <property name="minimum"><number>1</number></property>
     <property name="maximum"><number>500</number></property>
     <property name="value"><number>20</number></property>
    </widget>
   </item>
  </layout>
 </widget>
</ui>
```

## 4. 调整序列

调整序列（Adjustment Sequences）用于系统校准：

```python
class AdjFrequency(PulseqSequence, registry_key="adj_frequency"):
    """
    频率调整序列
    
    以adj_开头的序列会被识别为调整序列
    """
    
    def is_adjustment_sequence(self) -> bool:
        """基类会根据名称自动判断"""
        return self.seq_name.startswith("adj_")
```

## 5. 结果输出

### 添加DICOM结果

```python
# 在run_sequence或reconstruction中
from common.types import ResultItem

result = ResultItem()
result.name = "Images"
result.description = "Reconstructed MRI images"
result.type = "dicom"
result.primary = True
result.autoload_viewer = 1  # 自动在viewer 1中打开
result.file_path = "dicom/"
scan_task.results.append(result)
```

### 添加绘图结果

```python
import pickle
import matplotlib.pyplot as plt

plt.figure()
plt.plot(signal_data)
plt.title("Signal Plot")

# 保存为pickle
file = open(self.get_working_folder() + "/other/signal.plot", "wb")
pickle.dump(plt.gcf(), file)
file.close()

result = ResultItem()
result.name = "Signal"
result.type = "plot"
result.file_path = "other/signal.plot"
scan_task.results.append(result)
```

## 6. 与用户交互

### 发送状态更新

```python
from common.ipc import Communicator
ipc_comm = Communicator(Communicator.ACQ)

ipc_comm.send_status("Calculating sequence...")
ipc_comm.send_status("Acquiring data: 50%")
```

### 发送采集进度

```python
import common.helper as helper

ipc_comm.send_acq_data(
    start_time=helper.get_datetime(),
    expected_duration_sec=60,
    disable_statustimer=False
)
```

### 查询用户输入

```python
# 查询文本
value = ipc_comm.query_user("Enter patient name", input_type="text")

# 查询数值
value = ipc_comm.query_user("Enter flip angle", input_type="int", in_min=1, in_max=180)

# 显示警告
ipc_comm.send_user_alert("Calibration required!", type="warning")
```

## 7. 完整示例

```python
# sequences/simple_fid.py

import os
from pathlib import Path
import numpy as np
from PyQt5 import uic
import pypulseq as pp

from sequences import PulseqSequence
import common.logger as logger
from common.types import ResultItem

log = logger.get_logger()


class SimpleFID(PulseqSequence, registry_key=Path(__file__).stem):
    """简单FID序列示例"""
    
    param_flip_angle: int = 90
    param_adc_samples: int = 4096
    
    @classmethod
    def get_readable_name(self) -> str:
        return "Simple FID"
    
    @classmethod
    def get_description(self) -> str:
        return "Acquires a simple Free Induction Decay signal"
    
    @classmethod
    def get_default_parameters(self) -> dict:
        return {
            "flip_angle": 90,
            "adc_samples": 4096,
        }
    
    def get_parameters(self) -> dict:
        return {
            "flip_angle": self.param_flip_angle,
            "adc_samples": self.param_adc_samples,
        }
    
    def set_parameters(self, parameters, scan_task) -> bool:
        self.problem_list = []
        try:
            self.param_flip_angle = parameters["flip_angle"]
            self.param_adc_samples = parameters["adc_samples"]
        except:
            self.problem_list.append("Invalid parameters")
            return False
        return True
    
    def setup_ui(self, widget) -> bool:
        seq_path = os.path.dirname(os.path.abspath(__file__))
        uic.loadUi(f"{seq_path}/{self.get_name()}/interface.ui", widget)
        return True
    
    def write_parameters_to_ui(self, widget) -> bool:
        widget.flipAngleSpinBox.setValue(self.param_flip_angle)
        widget.adcSamplesSpinBox.setValue(self.param_adc_samples)
        return True
    
    def read_parameters_from_ui(self, widget, scan_task) -> bool:
        self.problem_list = []
        self.param_flip_angle = widget.flipAngleSpinBox.value()
        self.param_adc_samples = widget.adcSamplesSpinBox.value()
        return True
    
    def calculate_sequence(self, scan_task) -> bool:
        log.info("Calculating SimpleFID sequence")
        scan_task.processing.recon_mode = "bypass"
        self.seq_file_path = self.get_working_folder() + "/seq/acq0.seq"
        
        # 创建Pulseq序列
        seq = pp.Sequence()
        system = pp.Opts(max_grad=100, grad_unit="mT/m", max_slew=4000, slew_unit="T/m/s")
        
        rf = pp.make_block_pulse(
            flip_angle=self.param_flip_angle * np.pi / 180,
            duration=200e-6,
            system=system
        )
        adc = pp.make_adc(num_samples=self.param_adc_samples, duration=6.4e-3, system=system)
        
        seq.add_block(rf)
        seq.add_block(pp.make_delay(150e-6))
        seq.add_block(adc)
        
        seq.write(self.seq_file_path)
        return True
    
    def run_sequence(self, scan_task) -> bool:
        log.info("Running SimpleFID sequence")
        # 在实际硬件上运行序列...
        return True
```

## 8. 序列开发检查清单

- [ ] 继承 `PulseqSequence` 并设置 `registry_key`
- [ ] 实现 `get_readable_name()` 和 `get_description()`
- [ ] 实现 `get_default_parameters()` 和 `get_parameters()`
- [ ] 实现 `set_parameters()` 并包含参数验证
- [ ] 创建UI文件夹和 `interface.ui`
- [ ] 实现 `setup_ui()`, `write_parameters_to_ui()`, `read_parameters_from_ui()`
- [ ] 实现 `calculate_sequence()` 生成Pulseq文件
- [ ] 实现 `run_sequence()` 执行采集
- [ ] 设置正确的 `scan_task.processing` 参数
- [ ] 添加结果到 `scan_task.results`
- [ ] 测试序列在UI中的显示和编辑

