#! usr/bin/env/python3
# coding:utf-8
# @Time: 2018-10-30 15:07
# Author: turpure

import os
import datetime
from src.services.base_service import CommonService


class Fetcher(CommonService):
    """
    fetch developer sold detail from erp and put them into data warehouse
    """

    def __init__(self):
        super().__init__()
        self.base_name = 'mssql'
        self.warehouse = 'mysql'
        self.cur = self.base_dao.get_cur(self.base_name)
        self.con = self.base_dao.get_connection(self.base_name)
        self.warehouse_cur = self.base_dao.get_cur(self.warehouse)
        self.warehouse_con = self.base_dao.get_connection(self.warehouse)

    def close(self):
        self.base_dao.close_cur(self.cur)
        self.base_dao.close_cur(self.warehouse_cur)

    def fetch(self, date_flag, begin_date, end_date):
        sql = 'oauth_oauth_devGoodsSoldDetail @dateFlag=%s, @beginDate=%s, @endDate=%s'
        self.cur.execute(sql, (date_flag, begin_date, end_date))
        ret = self.cur.fetchall()
        for row in ret:
            yield (row['developer'],
                   row['goodsCode'],
                   row['devDate'],
                   row['goodsStatus'],
                   row['tradeNid'],
                   row['plat'],
                   row['suffix'],
                   int(row['sold']) if row['sold'] else 0,
                   float(row['amt']) if row['amt'] else 0,
                   float(row['profit']) if row['profit'] else 0,
                   row['dateFlag'],
                   row['orderTime'],
                   )

    def push(self, rows):
        sql = ('insert into cache_devGoodsSoldDetail('
               'developer,goodsCode,developDate,goodsStatus,tradeNid,plat,suffix,sold,amt,profit,dateFlag,orderTime) '
               'values(%s,%s,%s, %s,%s,%s,%s,%s,%s,%s,%s,%s)'
                ' ON DUPLICATE KEY UPDATE sold=values(sold),amt=values(amt),profit=values(profit)'
               )
        self.warehouse_cur.executemany(sql, list(rows))
        self.warehouse_con.commit()

    def clean(self):
        sql = 'truncate table cache_devGoodsSoldDetail'
        self.warehouse_cur.execute(sql)
        self.warehouse_con.commit()

    def work(self):
        try:
            today = str(datetime.datetime.today())
            some_days_ago = str(datetime.datetime.today() - datetime.timedelta(days=30))[:10]
            self.clean()
            for date_flag in [0, 1]:
                # rows = self.fetch(date_flag, '2015-01-01', today)
                rows = self.fetch(date_flag, some_days_ago, today)
                self.push(rows)
                self.logger.info('success to fetch dev sold details')
        except Exception as why:
            self.logger.error('fail to fetch dev sold details of {}'.format(why))
            name = os.path.basename(__file__).split(".")[0]
            raise Exception(f'fail to finish task of {name}')
        finally:
            self.close()


if __name__ == '__main__':
    worker = Fetcher()
    worker.work()
