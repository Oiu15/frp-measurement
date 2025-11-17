import os
import ctypes
from ctypes import c_double, c_int, Structure


class FrpResult(Structure):
    _fields_ = [
        ("outer_diameter_avg", c_double),
        ("inner_diameter_avg", c_double),
        ("roundness_outer", c_double),
        ("roundness_inner", c_double),
        ("straightness", c_double),
        ("concentricity", c_double),
        ("length", c_double),
        ("ok_flag", c_int),
    ]


def _load_lib():
    base_dir = os.path.dirname(__file__)
    if os.name == "nt":
        lib_name = "frp_core.dll"
    else:
        lib_name = "libfrp_core.so"
    path = os.path.join(base_dir, lib_name)
    return ctypes.CDLL(path)


_lib = None


def get_lib():
    global _lib
    if _lib is None:
        _lib = _load_lib()
        _lib.frp_init()
        _lib.frp_reset()
        _lib.frp_add_sample.argtypes = [c_double, c_double, c_double]
        _lib.frp_compute.argtypes = [ctypes.POINTER(FrpResult)]
    return _lib


def reset():
    get_lib().frp_reset()


def add_sample(angle_deg: float, outer_d: float, inner_d: float):
    get_lib().frp_add_sample(angle_deg, outer_d, inner_d)


def compute() -> FrpResult:
    res = FrpResult()
    get_lib().frp_compute(ctypes.byref(res))
    return res
