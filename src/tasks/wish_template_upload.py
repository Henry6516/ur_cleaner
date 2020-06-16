#! usr/bin/env/python3
# coding:utf-8
# @Time: 2019-02-22 11:30
# Author: turpure


import math
import time
import datetime
from src.services.base_service import BaseService
import requests
from multiprocessing.pool import ThreadPool as Pool
from bson import ObjectId
from pymongo import MongoClient

mongo = MongoClient('192.168.0.150', 27017)
mongodb = mongo['operation']
col_temp = mongodb['wish_template']
col_task = mongodb['wish_task']
col_log = mongodb['wish_log']


class Worker(BaseService):
    """
    worker template
    """

    def __init__(self):
        super().__init__()
        # self.today = str(datetime.datetime.today())[:19]
        self.today = int(time.time()) * 1000
        self.log_type = {1:"刊登商品",2:"添加多属性"}



    def get_wish_tasks(self):
        ret = col_task.find({'status':{'$in':['', None]}})
        for row in ret:
            yield row

    def get_wish_template(self, id):
        try:
            template = col_temp.find_one({'_id': ObjectId(id)})
            sql = "SELECT AccessToken as token,aliasname as suffix FROM S_WishSyncInfo WHERE  " \
               " aliasname is not null and  AliasName = %s  and aliasname not in " \
               " (select DictionaryName from B_Dictionary where CategoryID=12 and used=1 and FitCode='Wish')"
            self.cur.execute(sql,(template['selleruserid']))
            ret = self.cur.fetchone()
            template['access_token'] = ret['token']
            template['localized_currency_code'] = template['local_currency']
            template['localized_price'] = template['local_price']
            template['localized_shipping'] = template['local_shippingfee']

            del template['_id']
            del template['creator']
            del template['created']
            del template['updated']
            del template['local_currency']
            del template['local_price']
            del template['local_shippingfee']

            return template
        except Exception as e:
            self.logger.error(e)
            return {}


    def check_wish_template(self, row):
        url = "https://merchant.wish.com/api/v2/product"
        params = {'access_token':row['access_token'],'parent_sku':row['sku']}
        try:
            response = requests.get(url, params=params)
            ret = response.json()
            # print(ret)
            if ret['code'] == 0:
                return ret['data']['Product']['id']
            return False
        except Exception as why:
            self.logger.error(why)
            return False

    def upload_template(self, row):

        try:
            params = {}
            task_id = row['_id']
            params['task_id'] = str(task_id)
            params['template_id'] = str(row['template_id'])
            params['selleruserid'] = row['selleruserid']
            params['type'] = self.log_type[1]

            # 获取模板和token信息
            template = self.get_wish_template(row['template_id'])
            # print(template)
            if template:
                parent_sku = template['sku']
                task_params = {'id':task_id}
                # 判断是否有该产品
                check = self.check_wish_template(template)
                if not check:
                    try:
                        url = 'https://merchant.wish.com/api/v2/product/add'
                        response = requests.post(url, params=template)
                        ret = response.json()
                        # print(ret)
                        if ret['code'] == 0:
                            task_params['item_id'] = ret['data']['Product']['id']
                            task_params['status'] = 'success'
                            self.upload_variation(template['variants'], template['access_token'], parent_sku, params)
                            self.update_task_status(task_params)
                            self.update_template_status(row['template_id'])
                        else:
                            params['info'] = ret['message']
                            self.add_log(params)
                            self.logger.error(f"fail to upload product cause of {ret['message']}")
                    except Exception as why:
                        self.logger.error(f"fail to upload of products {parent_sku}  cause of {why}")
                else:
                    task_params['item_id'] = check
                    task_params['status'] = 'failed'
                    self.update_task_status(task_params)
                    params['info'] = f'products {parent_sku} already exists'
                    self.add_log(params)
                    self.logger.error(f"fail cause of products {parent_sku} already exists")
            else:
                params['info'] = f"can not fund template {row['template_id']}"
                self.add_log(params)
                self.logger.error(f"fail cause of can not fund template {row['template_id']}")
        except Exception as e:
            self.logger.error(e)

    def upload_variation(self, rows, token, parent_sku, params):
        params['type'] = self.log_type[2]
        try:
            url = "https://merchant.wish.com/api/v2/variant/add"
            for row in rows:
                row['access_token'] = token
                row['parent_sku'] = parent_sku
                del row['shipping']
                response = requests.post(url, params=row)
                ret = response.json()
                if ret['code'] != 0:
                    params['info'] = ret['message']
                    self.add_log(params)
                    self.logger.error(f"fail to upload of products variant {row['sku']} cause of {ret['message']}")
        except Exception as why:
            params['info'] = why
            self.add_log(params)
            self.logger.error(f"fail to upload of products variants {parent_sku}  cause of {why}")

    def update_task_status(self, row):
        col_task.update_one({'_id': row['id']}, {"$set": {'item_id':row['item_id'],'status':row['status'],'updated':self.today}}, upsert=True)
    def update_template_status(self, id):
        col_temp.update_one({'_id': id}, {"$set": {'status':'刊登成功','updated':self.today}}, upsert=True)

    # 添加日志
    def add_log(self, params):
        params['created'] = self.today
        col_log.insert_one(params)


    def work(self):
        try:
            tasks = self.get_wish_tasks()
            pl = Pool(16)
            pl.map(self.upload_template, tasks)
            pl.close()
            pl.join()
        except Exception as why:
            self.logger.error('fail to upload wish template cause of {} '.format(why))
        finally:
            self.close()


if __name__ == "__main__":
    worker = Worker()
    worker.work()

