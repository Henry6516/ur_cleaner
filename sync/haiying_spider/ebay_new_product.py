#! usr/bin/env/python3
# coding:utf-8
# @Time: 2019-10-19 14:23
# Author: turpure


import requests
import json
import datetime
from pymongo import MongoClient
from src.services.base_service import BaseService
from configs.config import Config


class Worker(BaseService):

    def __init__(self):
        super().__init__()
        config = Config()
        self.haiying_info = config.get_config('haiying')
        # self.mongo = MongoClient('localhost', 27017)
        self.mongo = MongoClient('192.168.0.150', 27017)

    def get_rule(self):
        sql = 'select listedTime from proEngine.recommend_ebayNewProductRule where isUsed=1'
        self.warehouse_cur.execute(sql)
        ret = self.warehouse_cur.fetchone()
        return ret

    def log_in(self):
        base_url = 'http://www.haiyingshuju.com/auth/login'
        form_data = {
            'username': self.haiying_info['username'],
            'password': self.haiying_info['password']
        }
        ret = requests.post(base_url, data=form_data)
        return ret.headers['token']

    def get_product(self):
        url = "http://www.haiyingshuju.com/ebay/newProduct/list"
        token = self.log_in()
        rule = self.get_rule()
        time_range = rule['listedTime'].split(',')
        payload = {
            "cids":"","index":1,"title":"","itemId":"","soldEnd":"","country":5,"visitEnd":"","priceEnd":"",
            "soldStart":"","titleType":"","sort":"DESC","pageSize":20,"priceStart":"","visitStart":"",
            "marketplace":["EBAY_GB","EBAY_DE","EBAY_US"],"popularStatus":"","sellerOrStore":"","storeLocation":["China"],
            "salesThreeDayFlag":"","orderColumn":"last_modi_time",
            "listedTime":[self._get_date_some_days_ago(i) for i in time_range],"itemLocation":[]}
        headers = {
            'Accept': "application/json, text/plain, */*",
            'Accept-Encoding': "gzip, deflate",
            'Accept-Language': "zh-CN,zh;q=0.9,en;q=0.8",
            'Connection': "keep-alive",
            'Content-Type': "application/json",
            'Host': "www.haiyingshuju.com",
            'Origin': "http://www.haiyingshuju.com",
            'Referer': "http://www.haiyingshuju.com/ebay/index.html",
            'token': token,
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36",
            'Cache-Control': "no-cache",
            'cache-control': "no-cache"
        }

        response = requests.post(url, data=json.dumps(payload), headers=headers)

        return response.json()['data']

    @staticmethod
    def _get_date_some_days_ago(number):
        today = datetime.datetime.today()
        ret = today - datetime.timedelta(days=int(number))
        return str(ret)[:10]

    def save(self, rows):
        db = self.mongo["product_engine"]
        collection = db["ebay_new_product"]
        collection.insert_many(rows)

    def run(self):
        try:
            rows = self.get_product()
            self.save(rows)
        except Exception as why:
            self.logger.error(f'fail to get ebay products cause of {why}')
        finally:
            self.close()
            self.mongo.close()


if __name__ == '__main__':
    worker = Worker()
    worker.run()
