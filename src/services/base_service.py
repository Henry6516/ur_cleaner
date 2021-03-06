#! usr/bin/env/python3
# coding:utf-8
# @Time: 2018-10-30 15:09
# Author: turpure

from dao.base_dao import BaseDao
from src.services import log, db
import pymysql
from configs.config import Config
config = Config()


class CommonService(object):
    """
    wrap log and db service
    """
    base_dao = BaseDao()

    def __init__(self):
        self.logger = self.base_dao.logger


class BaseService(object):
    """
    wrap log and db service
    """
    def __init__(self):
        self.logger = log.SysLogger().log
        self.mssql = db.DataBase('mssql')
        self.con = self.mssql.connection
        if self.con:
            self.cur = self.con.cursor(as_dict=True)
        self.mysql = db.DataBase('mysql')
        self.warehouse_con = self.mysql.connection
        if self.warehouse_con:
            self.warehouse_cur = self.warehouse_con.cursor(pymysql.cursors.DictCursor)

        erp = config.get_config('erp')
        if erp:
            self.erp = db.DataBase('erp')
            self.erp_con = self.erp.connection
            if self.erp_con:
                self.erp_cur = self.erp_con.cursor(pymysql.cursors.DictCursor)

        self.ibay = db.DataBase('ibay')
        self.ibay_con = self.ibay.connection
        if self.ibay_con:
            self.ibay_con.set_client_encoding('utf8')
            self.ibay_cur = self.ibay_con.cursor()

    def close(self):
        try:
            # self.cur.close()
            # self.con.close()
            # self.warehouse_cur.close()
            # self.warehouse_con.close()
            self.mysql.close()
            self.mssql.close()
            erp = config.get_config('erp')
            if erp:
                self.erp.close()
            ibay = config.get_config('ibay')
            if ibay:
                self.ibay.close()

            self.logger.info('close connection')
        except Exception as e:
            self.logger.error('fail to close connection cause of {}'.format(e))



