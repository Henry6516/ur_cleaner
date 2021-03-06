#! usr/bin/env/python3
# coding:utf-8
# Author: turpure

import os
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.services.base_service import CommonService
import requests


class Worker(CommonService):
    """
    worker
    """

    def __init__(self):
        super().__init__()
        self.base_name = 'mssql'
        self.cur = self.base_dao.get_cur(self.base_name)
        self.con = self.base_dao.get_connection(self.base_name)

    def close(self):
        self.base_dao.close_cur(self.cur)

    def get_joom_token(self):
        sql = 'select top 1 AccessToken from S_JoomSyncInfo'
        self.cur.execute(sql)
        ret = self.cur.fetchall()
        for row in ret:
            yield row

    def get_order(self, token):
        token = token['AccessToken']
        url = 'https://api-merchant.joom.com/api/v2/order/multi-get'
        headers = {'content-type': 'application/json', 'Authorization': 'Bearer ' + token}
        yesterday = str(datetime.datetime.today() - datetime.timedelta(days=1))[:10]
        date = str(datetime.datetime.strptime(yesterday[:8] + '01', '%Y-%m-%d'))[:10]
        limit = 300
        start = 0
        try:
            while True:
                param = {
                    "since": date,
                    "limit": limit,
                    'start': start * limit
                }
                start = start + 1
                response = requests.get(url, params=param, headers=headers)
                ret = response.json()
                if ret['code'] == 0 and ret['data']:
                    orders = ret['data']
                    for order in orders:
                        try:
                            order_detail = order["Order"]
                            if order_detail['state'] == 'REFUNDED':
                                refunded = dict()
                                refunded['transaction_id'] = order_detail['transaction_id']
                                refunded['refunded_time'] = order_detail['refunded_time']
                                refunded['order_total'] = order_detail['order_total']
                                refunded['currencyCode'] = 'USD'
                                refunded['plat'] = 'joom'
                                yield refunded
                        except Exception as e:
                            self.logger.debug(e)
                    if len(ret['data']) < limit:
                        break
                else:
                    break

        except Exception as e:
            self.logger.error(e)

    def save_refund_order(self,row):
        sql = ("if not EXISTS (select id from y_refunded_joom_test(nolock) where "
               "order_id=%s and refund_time= %s) "
               'insert into y_refunded_joom_test(order_id, refund_time, total_value,currencyCode, plat) '
               'values(%s,%s,%s,%s,%s)'
               "else update y_refunded_joom_test set "
               "total_value=%s,currencyCode=%s where order_id=%s and refund_time= %s")
        try:
            self.cur.execute(sql,
                             (
                              row['transaction_id'], row['refunded_time'],
                              row['order_total'], row['currencyCode'], row['plat']))
            self.con.commit()
            self.logger.info("success to get joom refunded order!")
        except Exception as e:
            self.logger.error("failed to get joom refunded order cause of %s" % e)

    def work(self):
        try:
            tokens = self.get_joom_token()
            with ThreadPoolExecutor(16) as pool:
                future = {pool.submit(self.get_order, token): token for token in tokens}
                for fu in as_completed(future):
                    try:
                        data = fu.result()
                        for row in data:
                            self.save_refund_order(row)
                    except Exception as e:
                        self.logger.error(e)
        except Exception as why:
            self.logger.error('fail to count sku cause of {} '.format(why))
            name = os.path.basename(__file__).split(".")[0]
            raise Exception(f'fail to finish task of {name}')
        finally:
            self.close()


if __name__ == "__main__":
    worker = Worker()
    worker.work()


