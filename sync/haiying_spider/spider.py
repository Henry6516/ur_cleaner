#! usr/bin/env/python3
# coding:utf-8
# @Time: 2019-11-08 17:02
# Author: turpure


import datetime
import asyncio
from abc import ABCMeta, abstractmethod
from pymongo import MongoClient
import motor.motor_asyncio
import copy
from src.services.base_service import BaseService
from configs.config import Config
from sync.haiying_spider.config import headers


class BaseSpider(BaseService):

    def __init__(self, rule_id=None):
        super().__init__()
        self.rule_id = rule_id
        self.headers = headers
        config = Config()
        self.haiying_info = config.get_config('haiying')
        self.mongo = MongoClient('192.168.0.150', 27017)
        self.mongo = motor.motor_asyncio.AsyncIOMotorClient('192.168.0.150', 27017)
        self.mongodb = self.mongo['product_engine']

    @abstractmethod
    async def get_rule(self):
        pass

    async def log_in(self, session):
        base_url = 'http://www.haiyingshuju.com/auth/login'
        form_data = {
            'username': self.haiying_info['username'],
            'password': self.haiying_info['password']
        }
        ret = await session.post(base_url, data=form_data)
        return ret.headers['token']

    async def parse_rule(self, rules):
        ret = []
        for rl in rules:
            published_site = rl['site']
            for site in published_site:
                row = copy.deepcopy(rl)
                if not row['popularStatus']:
                    row['popularStatus'] = ""
                row['marketplace'] = []
                row['country'] = list(site.values())[0]
                row['storeLocation'] = self.parse_store_location(row['country'], row['storeLocation'])
                ret.append(row)
        return ret

    @staticmethod
    def parse_store_location(country, store_locations):
        location_map = {
            1: {"中国": "中国", "香港": "香港"},  # 美國
            5: {"中国": "China", "香港": "Hong Kong"},  # 英国
            3: {"中国": "China", "香港": "Hong Kong"},  # 德国
            4: {"中国": "China", "香港": "Hong Kong"},  # 澳大利亚
        }
        ret = []
        for sl in store_locations:
            ele = location_map[country][sl]
            ret.append(ele)
        return ret

    @abstractmethod
    async def get_product(self, rule,sema):
        pass

    @staticmethod
    def _get_date_some_days_ago(number):
        today = datetime.datetime.today()
        ret = today - datetime.timedelta(days=int(number))
        return str(ret)[:10]

    @abstractmethod
    async def save(self, session, rows, page, rule):
        pass

    async def run(self, sema):
        try:
            rules = await self.get_rule()
            # for rls in rules:
            tasks  = [asyncio.ensure_future(self.get_product(rls, sema)) for rls in rules]
            await asyncio.wait(tasks)
        except Exception as why:
            self.logger.error(f'fail to get ebay products cause of {why} in async way')
        finally:
            self.close()
            self.mongo.close()






