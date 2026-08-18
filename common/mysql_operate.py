import pymysql
import os
from common.read_data import data
from common.logger import logger
from core.mock_data import DB_ROWS, get_db_backend

BASE_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
data_file_path = os.path.join(BASE_PATH, "config", "setting.ini")
_ini = data.load_ini(data_file_path)
data = _ini["mysql"]
USE_MOCK = str(_ini["mock"].get("USE_MOCK", "false")).lower() == "true"

DB_CONF = {
    "host": data["MYSQL_HOST"],
    "port": int(data["MYSQL_PORT"]),
    "user": data["MYSQL_USER"],
    "password": data["MYSQL_PASSWD"],
    "db": data["MYSQL_DB"]
}


class MysqlDb():

    def __init__(self, db_conf=DB_CONF):
        if USE_MOCK:
            # 离线学习模式：不连真实数据库，与接口共享同一份内存假库
            self.conn = None
            self.cur = None
            self._backend = get_db_backend()
            logger.info("MySQL 使用 mock 模式，不连接真实数据库")
            return
        # 通过字典拆包传递配置信息，建立数据库连接
        self.conn = pymysql.connect(**db_conf, autocommit=True)
        # 通过 cursor() 创建游标对象，并让查询结果以字典格式输出
        self.cur = self.conn.cursor(cursor=pymysql.cursors.DictCursor)

    def __del__(self):  # 对象资源被释放时触发，在对象即将被删除时的最后操作
        if self.conn is None:
            return
        # 关闭游标
        self.cur.close()
        # 关闭数据库连接
        self.conn.close()

    def select_db(self, sql):
        """查询"""
        if USE_MOCK:
            logger.info("MySQL mock 返回预设数据: {}".format(sql))
            return DB_ROWS
        # 检查连接是否断开，如果断开就进行重连
        self.conn.ping(reconnect=True)
        # 使用 execute() 执行sql
        self.cur.execute(sql)
        # 使用 fetchall() 获取查询结果
        data = self.cur.fetchall()
        return data

    def execute_db(self, sql):
        """更新/新增/删除"""
        if USE_MOCK:
            # 离线模式：把 fixture 的 SQL 同步到接口假库，保证数据联动
            logger.info("MySQL mock 执行（联动假库）: {}".format(sql))
            self._backend.exec_sql(sql)
            return
        try:
            # 检查连接是否断开，如果断开就进行重连
            self.conn.ping(reconnect=True)
            # 使用 execute() 执行sql
            self.cur.execute(sql)
            # 提交事务
            self.conn.commit()
        except Exception as e:
            logger.info("操作MySQL出现错误，错误原因：{}".format(e))
            # 回滚所有更改
            self.conn.rollback()


db = MysqlDb(DB_CONF)
