#!/usr/bin/env python3
# coding=utf-8
# @File    : get_hw_mem_info.py
# @Time    : 23-3-3 PM 3:00
# @Email   : xin.liu@high-flyer.cn
# @Description : 23-9-25 重构完成&测试通过
# @Cmd : dmidecode

import re
import subprocess
from copy import copy

from pydantic import BaseModel


class HwMemInfoModel(BaseModel):
    """
    内存信息模型
    """

    # sn重构为name
    name: str = None
    pn: str = None
    size: str = None
    speed: str = None
    slot: str = None
    vendor: str = None
    rank: str = None


class GetHwMemInfo:
    # 获取内存信息部分重构完成

    def get_mem_info(self):
        # 如函数名获取内存信息
        mem_dump_list = []

        mem_info = subprocess.getoutput("sudo dmidecode -t memory")

        def get_all_mem_info(mem):
            """
            获取已存在内存的全部信息
            """
            mem_info_list = re.split(r"Memory Device", mem)[1:]
            copy_mem_info_list = copy(mem_info_list)
            # 遍历匹配到的内存槽位，并判断是否存在内存，如果不存在（Unknown），将其从全量拷贝的list中剔除
            for item in mem_info_list:
                if re.search("Total Width: Unknown", str(item)):
                    copy_mem_info_list.remove(item)

            # 定义一个变量名与正则匹配关键词对应的字典
            var_name_pattern_map = {
                "size": "Size",
                "slot": "Locator",
                "vendor": "Manufacturer",
                "name": "Serial Number",
                "pn": "Part Number",
                "rank": "Rank",
                "speed": "Configured Memory Speed",
            }
            # 遍历存在的内存
            for item in copy_mem_info_list:
                # 实例化内存的模型
                hw_mem_info_model = HwMemInfoModel()
                # 遍历对应字典，如过匹配成功则调用setattr 给对应的变量赋值
                for var_name in var_name_pattern_map:
                    pattern = (
                        f"{var_name_pattern_map[var_name]}:\\s*([a-zA-Z0-9_\\s^\\n]+)"
                    )

                    res = re.search(pattern, str(item))
                    if res:
                        if re.search("802C", res.group(1)) or re.search(
                            "00AD", res.group(1)
                        ):
                            # 针对dell内存的覆盖
                            setattr(hw_mem_info_model, var_name, "Dell Inc.")
                        else:
                            result = re.sub(r"\n.*", "", res.group(1))
                            setattr(hw_mem_info_model, var_name, result)

                mem_dump_list.append(hw_mem_info_model.model_dump())

        get_all_mem_info(mem_info)

        final_dict = {
            "plugin_name": self.__class__.__name__,
            "contains": mem_dump_list,
        }

        return final_dict


if __name__ == "__main__":
    import json

    get_mem_info = GetHwMemInfo().get_mem_info()

    # 重构返回json结构
    # 获取contians 中的 list
    data_list = get_mem_info["contains"]
    # 再存入新列表
    new_list = []
    for data in data_list:
        tmp_dict = {
            "name": data["name"],
            "type": "mem",
            "updatedAt": None,
        }
        data.pop("name")
        tmp_dict["data"] = data
        new_list.append(tmp_dict)
    final_dict = {
        "plugin_name": get_mem_info["plugin_name"],
        "contains": new_list,
    }
    print(json.dumps(final_dict, indent=4))
