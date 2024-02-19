# -*- coding: utf-8 -*-
# time: 2024/1/9 11:54
# file: get_machine_info_from_huaweicloud.py
# author: xin.liu
# email: xin.liu@high-flyer.cn
# coding: utf-8

import logging as llog
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from huaweicloudsdkcore.exceptions import exceptions
from huaweicloudsdkecs.v2 import *
from pydantic import BaseModel

from huaweicloud_auth import HuaweiCouldAuth


class EcsInfoModel(BaseModel):
    """
    云主机信息模型
    """

    id: Optional[str] = None
    name: Optional[str] = None
    pn: Optional[str] = None
    cpu: Optional[str] = None
    mem: Optional[str] = None
    disk: Optional[str] = None
    private_ip: Optional[str] = None
    floating_ip: Optional[str] = None
    mac: Optional[str] = None
    region: Optional[str] = None
    project: Optional[str] = None


# 新加波 "ap-southeast-3"
# 上海 "cn-east-3"


class GetEcsInfoFromCloud(HuaweiCouldAuth):
    def get_ecs_info(self, host):
        private_ip, floating_ip, mac = self.private_ip_and_floating_ip_and_mac(host)

        ecs_info_model = EcsInfoModel(
            id=host["id"],
            name=host["name"],
            pn=host["flavor"]["name"],
            cpu=host["flavor"]["vcpus"],
            mem=f'{int(host["flavor"]["ram"]) / 1024} GB',
            disk=self.get_disk_size(host["id"]),
            project=self.project_name(host),
            region=self.zone_name(host),
            private_ip=private_ip,
            floating_ip=floating_ip,
            mac=mac,
        )
        return ecs_info_model

    def get_ecs_info_from_cloud_by_zone(self):
        try:
            request = ListServersDetailsRequest(limit=1000)
            response = self.client.list_servers_details(request)

            res = response.to_dict()
            res_list = []

            # 创建一个线程池，最大工作线程数为20
            with ThreadPoolExecutor(max_workers=100) as executor:
                # 创建一个字典来存储每个future和对应的host
                future_to_host = {
                    executor.submit(self.get_ecs_info, host): host
                    for host in res["servers"]
                }

                # 遍历future对象
                for future in as_completed(future_to_host):
                    host = future_to_host[future]

                    result = future.result()
                    res_list.append(result)
                return res_list

        except exceptions.ClientRequestException as e:
            print(e)
            print(e.status_code)
            print(e.request_id)
            print(e.error_code)
            print(e.error_msg)

    @staticmethod
    def project_name(host_info):
        project_id = os.environ.get(host_info["enterprise_project_id"])
        if project_id:
            return project_id
        elif host_info["enterprise_project_id"] == "0":
            return "默认分组"
        else:
            return project_id

    @staticmethod
    def zone_name(host_info):
        zone = os.environ.get(host_info["os_ext_a_zavailability_zone"])
        if zone:
            return zone
        else:
            return host_info["os_ext_a_zavailability_zone"]

    @staticmethod
    def private_ip_and_floating_ip_and_mac(host_info):
        network_list = [value for key, value in host_info["addresses"].items()]

        def flatten(lst):
            return (
                [item for sublist in lst for item in flatten(sublist)]
                if isinstance(lst, list)
                else [lst]
            )

        tmp_list = flatten(network_list)
        private_ip, floating_ip, mac = None, None, None
        for network in tmp_list:
            if network.os_ext_ip_stype == "fixed":
                private_ip = network.addr
                mac = network.os_ext_ips_ma_cmac_addr
            elif network.os_ext_ip_stype == "floating":
                floating_ip = network.addr
                mac = network.os_ext_ips_ma_cmac_addr
            else:
                llog.error("未知IP地址类型")
        return private_ip, floating_ip, mac

    def get_disk_size(self, host_id):
        request = ListServerBlockDevicesRequest()
        request.server_id = host_id
        response = self.client.list_server_block_devices(request)
        res = response.to_dict()
        tmp_disk_size = 0
        for disk in res["volume_attachments"]:
            # print(f'磁盘ID {disk["id"]}')
            tmp_disk_size += int(disk["size"])
        return f"{tmp_disk_size} GB"


if __name__ == "__main__":
    import json

    zone_list = ["cn-east-3", "ap-southeast-3"]
    all_results = []
    # 创建线程池

    for zone in zone_list:
        host_info = GetEcsInfoFromCloud(project_id="", zone=zone)
        all_results.extend(host_info.get_ecs_info_from_cloud_by_zone())
    # print(all_results)

    final_data_list = []
    for results in all_results:
        final_data_list.append(results.model_dump())

    final_dict = {
        "plugin_name": "get_host_info_from_huaweicloud",
        "name": "huaweicloud",
        "type": "huaweicloud",
        "desc": None,
        "updatedAt": None,
        "data": final_data_list,
    }

    print(json.dumps(final_dict, indent=4, ensure_ascii=False))
