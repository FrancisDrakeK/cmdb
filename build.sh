#!/bin/bash
nuitka3 --onefile  --standalone  --lto=no   -j 8 -o get_hw_ib_info  get_hw_ib_info.py &
nuitka3 --onefile  --standalone  --lto=no   -j 8 -o get_hw_disk_info  get_hw_disk_info.py &
nuitka3 --onefile  --standalone  --lto=no   -j 8 -o get_hw_mem_info  get_hw_mem_info.py &
nuitka3 --onefile  --standalone  --lto=no   -j 8 -o get_hw_gpu_info  get_hw_gpu_info.py &
nuitka3 --onefile  --standalone  --lto=no   -j 8 -o get_host_info  get_host_info.py &


wait
