# -*- coding: utf-8 -*-
# time: 2023/12/19 10:07
# file: package_copy.py
# author: xin.liu
# email: xin.liu@high-flyer.cn

import subprocess

# 导入线程池
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def check_bin_dir():
    """
    如果bin目录存在 则删除并重新创建
    """
    if Path("bin").exists():
        # 强制删除 bin目录
        subprocess.getoutput(f"rm -rf bin")
    Path("bin").mkdir()


def compile(src_file_path, output_file_path):
    # 编译文件

    res = subprocess.getoutput(
        f"nuitka3 --onefile  --standalone  --lto=no   -j 8  -o {output_file_path}  {src_file_path}"
    )

    print(res)
    res = subprocess.getoutput(f"mv {output_file_path} bin/")
    print(res)


def package_and_copy():
    print("开始打包")
    res = subprocess.getoutput(f"tar -zcvf bin.tgz bin")
    print(res)
    print("打包完成")
    print("开始复制")
    res = subprocess.getoutput(f"cp bin.tgz  /mnt/smb/")
    print(res)
    print("复制完成")


if __name__ == "__main__":
    # 线程池 启动 compile 函数
    with ThreadPoolExecutor(max_workers=10) as pool:
        check_bin_dir()
        for src_file_path in Path("get_machine_info").glob("*.py"):
            output_file_path = Path((src_file_path.name[:-3]))
            pool.submit(compile, src_file_path, output_file_path)

        src_file_path = Path("get_machine_info_from_huaweicloud").joinpath(
            "get_machine_info_from_huaweicloud.py"
        )
        output_file_path = Path((src_file_path.name[:-3]))
        pool.submit(compile, src_file_path, output_file_path)

        print("编译任务已提交请等待...")
    package_and_copy()
