import os

# MKL 2025's default (OpenMP) threading layer fails to load on this Windows
# setup (pypardiso raises WinError 0xc06d007f on every solve); the TBB layer
# works and stays multi-threaded. Must be set before MKL's first call, hence
# before numpy/bw2calc are imported. setdefault so an explicit setting wins.
if os.name == "nt":
    os.environ.setdefault("MKL_THREADING_LAYER", "TBB")
    # If MKL is already loaded (e.g. under Streamlit, where numpy runs long
    # before this module), the env var is read too late - switch the layer
    # through MKL's own API instead. A no-op when MKL is absent or already
    # on a working layer.
    try:
        import ctypes as _ctypes
        import sys as _sys
        from pathlib import Path as _Path
        _mkl = _Path(_sys.prefix) / "Library" / "bin" / "mkl_rt.2.dll"
        if _mkl.exists():
            _ctypes.CDLL(str(_mkl)).MKL_Set_Threading_Layer(_ctypes.c_int(4))  # 4 = TBB
    except Exception:
        pass
