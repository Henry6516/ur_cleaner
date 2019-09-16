#! usr/bin/env/python3
# coding:utf-8
# @Time: 2018-10-18 14:44
# Author: turpure


from configs.config import Config
from src.services.log import SysLogger

config = Config()


class DataBase(object):
    """
    database singleton connection
    """
    connect = None
    used_count = 0

    def __init__(self, base_name):
        self.base_name = base_name
        if not self.connect:
            self.used_count += 1
            SysLogger().log.info('not existing {} connection...'.format(self.base_name))
            self.connect = self._connect()

    def _connect(self):
        try:
            SysLogger().log.info('connect {}...'.format(self.base_name))

            if self.base_name == 'mssql':

                import pymssql
                return pymssql.connect(**config.get_config('mssql'))

            if self.base_name == 'mysql':

                import pymysql
                return pymysql.connect(**config.get_config('mysql'))

        except Exception as why:
            SysLogger().log.info('can not connect {} cause of {}'.format(self.base_name, why))
            return None

    @property
    def connection(self):
        return self.connect

    def close(self):
        if self.used_count == 1:
            SysLogger().log.info('close {}...'.format(self.base_name))
            self.connect.close()
        if self.used_count > 1:
            SysLogger().log.info('close {} by decreasing one connection'.format(self.base_name))
            self.used_count -= 1


if __name__ == '__main__':
    import pymysql
    con = DataBase('mysql')
    cur = con.connection.cursor(pymysql.cursors.DictCursor)
    cur.execute('select * from requirement')
    ret = cur.fetchall()
    for row in ret:
        print(row)
    con.close()



