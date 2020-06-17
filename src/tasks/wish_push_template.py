#! usr/bin/env/python3
# coding:utf-8
# @Time: 2019-02-22 11:30
# Author: turpure

from src.services.base_service import BaseService
from configs.config import Config
import requests
import json
import datetime
from pymongo import MongoClient


mongo = MongoClient('192.168.0.150', 27017)
mongodb = mongo['operation']
col = mongodb['wish_template']


class Worker(BaseService):
    """
    push wish template
    """
    def __init__(self):
        super().__init__()
        config = Config().config
        self.token = config['ur_center']['token']
        self.op_token = config['op_center']['token']

    def get_products(self):
        return [54252]

    def get_data_by_id(self, product_id):
        base_url = 'http://127.0.0.1:8089/v1/oa-goodsinfo/plat-export-wish-data'
        headers = {'content-type': 'application/json', 'Authorization': 'Bearer ' + self.token}
        data = json.dumps({"condition": {"id": product_id}})
        try:
            ret = requests.post(base_url, data=data, headers=headers)
            templates = ret.json()['data']['data']
            for tm in templates:
                tm['inventory'] = int(tm['inventory'])
                self.push(tm, product_id)
            self.logger.info(f'success to save  template of {product_id}')
        except Exception as why:
            self.logger.error(f'failed to  push template of {product_id} cause of {why}')

    def push(self, data, product_id):
        base_url = 'http://127.0.0.1:18881/v1/operation/wish-publish-trans-save'
        headers = {'content-type': 'application/json', 'Authorization': 'Bearer ' + self.op_token}
        body = json.dumps({"condition": data})
        try:
            ret = requests.post(base_url, data=body, headers=headers)
            content = ret.json()
            code = content['code']
            if code != 200:
                self.logger.error(f'failed to save  template of {data["sku"]} cause of {content["message"]}')
            else:
                self.logger.info(f'success to save  template of {data["sku"]}')

        except Exception as why:
            self.logger.error(f'failed to  push template of {data["sku"]} cause of {why}')

    # def push(self, data):
    #     col.save(data)

    def work(self):
        try:
            products = self.get_products()
            for pt in products:
                self.get_data_by_id(pt)

        except Exception as why:
                self.logger.error('fail to push wish template  cause of {} '.format(why))
        finally:
            self.close()
            mongo.close()


if __name__ == "__main__":
    worker = Worker()
    worker.work()


