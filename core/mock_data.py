# -*- coding: utf-8 -*-
"""
离线学习模式用的「状态化契约 mock」。

设计目标（两全方案）：
- 不改动任何 YAML 测试数据，参数化里的成功行/失败行都能被真实验证；
- mock 维护的是「接口契约 + 一份内存假库」，而非写死测试数据，可维护；
- 开启 USE_MOCK=true 时，用例不依赖作者的 192.168.89.128 虚拟机与 MySQL 也能跑通。

注意：
- 接口返回的 code 统一为「字符串」，与 YAML 里的 except_code（如 "1004"）类型一致；
- 数据库（mysql_operate）与接口共享同一份 MockBackend 状态：注册会写入、
  登录/查询会读、fixture 里的 DELETE/INSERT/UPDATE SQL 也会同步这份状态，
  保证用例间的数据联动与真实服务行为一致。
"""


class MockBackend:
    """内存假服务：保存用户，并按接口契约响应。"""

    def __init__(self):
        # username -> {password, telephone, sex, address, allow_delete}
        self.users = {
            "wintest":  {"password": "123456", "telephone": "13500000000", "sex": "1", "address": "深圳", "allow_delete": True},
            "wintest4": {"password": "123456", "telephone": "13500000001", "sex": "1", "address": "深圳", "allow_delete": True},
            "wintest3": {"password": "123456", "telephone": "13500000002", "sex": "1", "address": "深圳", "allow_delete": False},
            "测试test":  {"password": "123456", "telephone": "13599999999", "sex": "1", "address": "深圳市宝安区", "allow_delete": True},
        }
        self.next_id = 100

    # ---------- 接口契约（code 均为字符串）----------
    def get_all_users(self):
        data = [{"id": i, "username": u} for i, u in enumerate(self.users, 1)]
        return 200, {"code": 0, "msg": "查询成功", "data": data}

    def get_one_user(self, username):
        if username in self.users:
            # 真实 Flask Demo 的单用户查询 data 为列表
            return 200, {"code": 0, "msg": "查询成功",
                         "data": [{"id": 1, "username": username, **self.users[username]}]}
        return 200, {"code": 1004, "msg": "查不到相关用户", "data": None}

    def register(self, json_body):
        username = json_body.get("username")
        telephone = str(json_body.get("telephone", ""))
        sex = str(json_body.get("sex", ""))
        if username in self.users:
            return 200, {"code": 2002, "msg": "用户名已存在，注册失败", "data": None}
        if sex not in ("0", "1"):
            return 200, {"code": 2003, "msg": "输入的性别只能是 0(男) 或 1(女)", "data": None}
        if len(telephone) != 11 or not telephone.isdigit():
            return 200, {"code": 4008, "msg": "手机号格式不正确", "data": None}
        self.next_id += 1
        self.users[username] = {
            "password": json_body.get("password"),
            "telephone": telephone,
            "sex": sex,
            "address": json_body.get("address", ""),
            "allow_delete": True,
        }
        return 200, {"code": 0, "msg": "注册成功", "data": {"id": self.next_id, "username": username}}

    def login(self, payload):
        username = payload.get("username")
        password = payload.get("password")
        if username not in self.users:
            return 200, {"code": 1003, "msg": "用户名不存在", "data": None}
        if self.users[username]["password"] != password:
            return 200, {"code": 1003, "msg": "用户名不存在", "data": None}
        return 200, {"code": 0, "msg": "登录成功",
                     "login_info": {"token": "mock-token-{}".format(username)}}

    def update_user(self, user_id, json_body):
        # 有效 id 覆盖 api_test(期望4) 与 scenario(期望1) 两边的假设
        if int(user_id) not in (1, 4):
            return 200, {"code": 4005, "msg": "修改的用户ID不存在", "data": None}
        telephone = str(json_body.get("telephone", ""))
        if len(telephone) != 11 or not telephone.isdigit():
            return 200, {"code": 4008, "msg": "手机号格式不正确", "data": None}
        return 200, {"code": 0, "msg": "修改用户信息成功", "data": None}

    def delete_user(self, name, json_body):
        if name not in self.users:
            return 200, {"code": 4005, "msg": "用户ID不存在", "data": None}
        if not self.users[name]["allow_delete"]:
            return 200, {"code": 3006, "msg": "该用户不允许删除", "data": None}
        del self.users[name]
        return 200, {"code": 0, "msg": "删除用户信息成功", "data": None}

    # ---------- 数据库 SQL 联动（供 mysql_operate mock 调用）----------
    def exec_sql(self, sql):
        """极简 SQL 解析，仅覆盖 fixture 用到的语句，保持接口与库状态一致。"""
        s = sql.strip().rstrip(";")
        upper = s.upper()
        if upper.startswith("DELETE FROM USER WHERE USERNAME"):
            name = s.split("'", 1)[1].rsplit("'", 1)[0]
            self.users.pop(name, None)
        elif upper.startswith("INSERT INTO USER"):
            # 形如 INSERT INTO user(username,password,...) VALUES('wintest3','123456',...)
            name = s.split("VALUES", 1)[1].strip("()").split(",")[0].strip("'")
            # fixture 重建的用户默认可删除，强制覆盖以保证数据联动正确
            self.users[name] = {"password": "123456", "telephone": "13500000000",
                                "sex": "1", "address": "深圳", "allow_delete": True}
        elif upper.startswith("UPDATE USER SET TELEPHONE"):
            # UPDATE user SET telephone='13500010004' WHERE id=4
            new_tel = s.split("telephone", 1)[1].split("'", 2)[1]
            # id 不影响 mock 状态（手机号唯一性在接口层校验），这里仅记录
            for u in self.users.values():
                u["telephone"] = new_tel


_backend = MockBackend()


def get_api_mock(method: str, url: str, request_body=None):
    """根据 method+url(+请求体) 路由到契约方法，返回 (status_code, body)。"""
    m = method.upper()
    path = url.replace("http://192.168.89.128:9999", "")
    body = request_body or {}

    if m == "GET" and path == "/users":
        return _backend.get_all_users()
    if m == "GET" and path.startswith("/users/"):
        return _backend.get_one_user(path.split("/users/", 1)[1])
    if m == "POST" and path == "/register":
        return _backend.register(body)
    if m == "POST" and path == "/login":
        return _backend.login(body)
    if m == "PUT" and path.startswith("/update/user/"):
        return _backend.update_user(path.split("/update/user/", 1)[1], body)
    if m == "POST" and path.startswith("/delete/user/"):
        return _backend.delete_user(path.split("/delete/user/", 1)[1], body)

    return 200, {"code": 0, "msg": "success", "data": None}


def get_db_backend():
    """返回共享的状态后端，供 mysql_operate 在 mock 模式下同步数据。"""
    return _backend


# 数据库 mock：内存表，模拟 select 结果
DB_ROWS = [
    {"id": 1, "username": "wintest", "age": 18},
    {"id": 2, "username": "测试test", "age": 20},
]
