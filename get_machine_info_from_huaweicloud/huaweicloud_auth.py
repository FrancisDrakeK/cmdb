# -*- coding: utf-8 -*-
# time: 2024/1/18 11:26
# file: huaweicloud_auth.py
# author: xin.liu
# email: xin.liu@high-flyer.cn
import os
from os.path import join, dirname

from dotenv import load_dotenv
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2 import *
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion

dotenv_path = join(dirname(__file__), ".env")
load_dotenv(dotenv_path)


class HuaweiCouldAuth:
    """
    华为云鉴权 父类
    :param project_id: 项目id
    :param zone: 区域
    """

    def __init__(self, project_id, zone):
        self.ak = os.environ.get("ak")
        self.sk = os.environ.get("sk")
        if project_id:
            self.credentials = BasicCredentials(self.ak, self.sk, project_id)
        else:
            self.credentials = BasicCredentials(self.ak, self.sk)
        self.client = (
            EcsClient.new_builder()
            .with_credentials(self.credentials)
            .with_region(EcsRegion.value_of(zone))
            .build()
        )
