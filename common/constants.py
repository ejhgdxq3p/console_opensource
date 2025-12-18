from enum import Enum
import common.runtime as rt


class mri4all_defs:
    SEP = "#"


import os as _os

class mri4all_paths:
    BASE = rt.get_base_path()
    DATA = _os.path.join(BASE, "data")
    DATA_QUEUE_ACQ = _os.path.join(DATA, "acq_queue")
    DATA_ACQ = _os.path.join(DATA, "acq")
    DATA_QUEUE_RECON = _os.path.join(DATA, "recon_queue")
    DATA_RECON = _os.path.join(DATA, "recon")
    DATA_COMPLETE = _os.path.join(DATA, "complete")
    DATA_FAILURE = _os.path.join(DATA, "failure")
    DATA_ARCHIVE = _os.path.join(DATA, "archive")
    DATA_STATE = _os.path.join(DATA, "state")


class mri4all_files:
    LOCK = "LOCK"
    PREPARED = "PREPARED"
    EDITING = "EDITING"
    STOP = "STOP"
    TASK = "scan.json"


class mri4all_scanfiles:
    RAWDATA = "raw.npy"
    PE_ORDER = "pe_order.npy"
    ADC_PHASE = "adc_phase.npy"
    TRAJ = "traj.csv"  # csv format with rows: z phase encode, columns: y phase encodes
    BDATA = "B0.npy"


class mri4all_taskdata:
    SEQ = "seq"
    RAWDATA = "rawdata"
    DICOM = "dicom"
    TEMP = "temp"
    OTHER = "other"


class mri4all_states:
    CREATED = "created"
    SCHEDULED_ACQ = "scheduled_acq"
    ACQ = "acq"
    SCHEDULED_RECON = "scheduled_recon"
    RECON = "recon"
    COMPLETE = "complete"
    FAILURE = "failure"


class Service(Enum):
    ACQ_SERVICE = "mri4all_acq"
    RECON_SERVICE = "mri4all_recon"


class ServiceAction(Enum):
    START = "start"
    STOP = "stop"
    KILL = "kill"
    STATUS = "status"
