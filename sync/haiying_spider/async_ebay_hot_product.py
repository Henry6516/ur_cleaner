#! usr/bin/env/python3
# coding:utf-8
# @Time: 2019-10-19 14:23
# Author: turpure


import asyncio
import datetime
import json
import math

import aiohttp
from bson.objectid import ObjectId
from sync.haiying_spider.spider import BaseSpider
from pymongo.errors import DuplicateKeyError


class Worker(BaseSpider):

    def __init__(self, rule_id=None):
        super().__init__()

    async def get_rule(self):
        col = self.mongodb['ebay_hot_rule']
        if self.rule_id:
            rule = await col.find_one(ObjectId(self.rule_id))
            rules = [rule]
        else:
            rules = await col.find({'isUsed': 1, 'type': 'auto'}).to_list(length=None)
        return await self.parse_rule(rules)

    async def get_product(self, rule,sema):
        url = "http://www.haiyingshuju.com/ebay/product/list"
        async  with sema:
            async with aiohttp.ClientSession() as session:
                token = await self.log_in(session)
                self.headers['token'] = token
                rule_id = rule['_id']
                ruleData = {'id': rule['_id'], 'ruleName': rule['ruleName']}
                del rule['_id']
                gen_end = self._get_date_some_days_ago(rule.get('genTimeStart', ''))
                gen_start = self._get_date_some_days_ago(rule.get('genTimeEnd', ''))
                rule['genTimeEnd'] = gen_end
                rule['genTimeStart'] = gen_start

                response = await session.post(url, data=json.dumps(rule), headers=self.headers)


                ret = await response.json()
                total_page = math.ceil(ret['total'] / 20)
                rows = ret['data']
                await self.save(session, rows, page=1, rule=ruleData)
                if total_page > 1:
                    for page in range(2, total_page + 1):
                        try:
                            rule['index'] = page
                            response = await session.post(url, data=json.dumps(rule), headers=self.headers)

                            # 等待一下
                            asyncio.sleep(1)

                            res = await response.json()
                            rows = res['data']
                            await self.save(session, rows, page, ruleData)

                        except Exception as why:
                            self.logger.error(f'fail to get page {page} cause of {why}')

    @staticmethod
    def _get_date_some_days_ago(number):
        if number:
            today = datetime.datetime.today()
            ret = today - datetime.timedelta(days=int(number))
            return str(ret)[:10]
        return number

    async def save(self, session, rows, page, rule):
        countryList = {'EBAY_US':1, 'EBAY_GB':5, 'EBAY_DE':3, 'EBAY_AU':4}
        collection = self.mongodb.ebay_hot_product
        today = str(datetime.datetime.now())
        for row in rows:
            row['ruleType'] = "ebay_hot_rule",
            row["rules"] = [rule['id']]
            row["ruleName"] = rule['ruleName']
            row['recommendDate'] = today
            row['recommendToPersons'] = []

            try:
                country = countryList[row['marketplace']]
            except:
                country = 1

            params = {'itemId':row['itemId'],'genTime': row['genTime'],'country': country}
            #获取走势数据
            url = "http://www.haiyingshuju.com/ebay/product/chart"
            response = await session.post(url, data=json.dumps(params), headers=self.headers)
            ret = await response.json()
            row['soldChart'] = {'soldDate':ret['soldDate'],'soldData':ret['soldData']}
            try:
                await collection.insert_one(row)
                self.logger.debug(f'success to save {row["itemId"]}')
            except DuplicateKeyError:
                doc = await  collection.find_one({'itemId': row['itemId']})
                rules = list(set(doc['rules'] + row['rules']))
                row['rules'] = rules
                row['recommendDate'] = today
                del row['recommendToPersons']
                del row['_id']
                await collection.find_one_and_update({'itemId': row['itemId']}, {"$set": row})
                self.logger.debug(f'update {row["itemId"]}')
            except Exception as why:
                self.logger.debug(f'fail to save {row["itemId"]} cause of {why}')
        self.logger.info(f"success to save page {page} in async way of rule {rule['id']} ")


if __name__ == '__main__':
    import time
    start = time.time()
    worker = Worker()
    loop = asyncio.get_event_loop()
    sema = asyncio.Semaphore(3)
    loop.run_until_complete(worker.run(sema))
    end = time.time()
    print(f'it takes {end - start} seconds')
