#!/usr/bin/env python3
# coding=utf-8
# @File    : get_hw_gpu_info.py
# @Time    : 23-3-3 PM 3:00
# @Email   : xin.liu@high-flyer.cn
# @Description : 23-9-25 重构完成&测试通过
# @Cmd : nvidia-smi
import subprocess
from copy import copy

from pydantic import BaseModel


class HwGPUInfoModel(BaseModel):
    name: str = None
    pn: str = None
    video_mem: str = None
    bn: str = None
    driver_version: str = None


class GetHwGpuInfo:
    # GPU部分实现没问题，不用重构

    def get_gpu_info(self):
        gpu_info_list = []
        gpu_sn_list = []
        gpu_info = subprocess.getoutput(
            "nvidia-smi --query-gpu=pci.bus_id,name,serial,memory.total,driver_version,count"
            " --format=csv,noheader"
        ).split("\n")

        for line in gpu_info:
            hw_gpu_info_model = HwGPUInfoModel()
            hw_gpu_info_model.bn = line.split(", ")[0]
            hw_gpu_info_model.pn = line.split(", ")[1]
            hw_gpu_info_model.name = line.split(", ")[2]
            gpu_sn_list.append(hw_gpu_info_model.name)
            if line.split(", ")[3] == "40536 MiB":
                hw_gpu_info_model.video_mem = "40 GB"
            else:
                hw_gpu_info_model.video_mem = line.split(", ")[3]
            hw_gpu_info_model.driver_version = line.split(", ")[4]

            gpu_info_list.append(copy(hw_gpu_info_model.model_dump()))

        final_dict = {
            "plugin_name": self.__class__.__name__,
            "contains": gpu_info_list,
        }

        return final_dict


if __name__ == "__main__":
    import json

    get_gpu_info = GetHwGpuInfo().get_gpu_info()

    # 重构返回json结构
    # 获取contians 中的 list
    data_list = get_gpu_info["contains"]
    # 再存入新列表
    new_list = []
    for data in data_list:
        tmp_dict = {
            "name": data["name"],
            "type": "gpu",
            "updatedAt": None,
        }
        data.pop("name")
        tmp_dict["data"] = data
        new_list.append(tmp_dict)
    final_dict = {
        "plugin_name": get_gpu_info["plugin_name"],
        "contains": new_list,
    }
    print(json.dumps(final_dict, indent=4))
