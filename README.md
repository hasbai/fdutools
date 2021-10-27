# FDUTOOLS 复旦学生实用工具

- 平安复旦
- 选课
- 成绩查询

## Get started

本项目使用 `poetry` 包管理工具，详见 https://python-poetry.org/docs/

安装虚拟环境与依赖

```shell
poetry install
poetry shell
```

## Features

### 平安复旦自动填写

参考了 https://github.com/k652/daily_fudan

- 支持验证码识别
- 提交失败后发送邮件
- 提供数据库支持，详见 `pafd_db.py`

```python
from pafd import Pafd

pafd = Pafd('username', 'password')
result = pafd.main()
print(result['message'])
'''
[I] 已登录
[I] 今日已提交   日期：20211026，地址：上海市杨浦区五角场街道复旦大学新闻学院复旦大学邯郸校区
[I] 已登出
'''
print(result['code'])
'''
0: 提交成功
1: 今日已提交
-1: 提交失败
'''
```

### 选课

原理：循环请求，抢到为止

特性：多用户多线程同时抢多门

使用：在 config.py 中填写好相应配置（见下文）后运行 xk.py 即可

### 成绩查询

- 考试成绩
- 绩点排名

```python
from grade import Grade
import config

grade = Grade(config.username, config.password)
grade.login()
print(grade.get_grade(config.semester_id))
print(grade.get_gpa())
grade.close()

'''
Returns:
[]  # 目前还没有出成绩，所以没有数据
我的绩点为：*.**
专业排名为：**.*%
'''
```

## config.py 参考

```python
# 多用户（多线程选课）
users = [
    {
        'username': '学号', 'password': '密码', 'email': '邮箱',
        'courses': ['完整课程代码']
    },
]

# 单用户
username = '学号'
password = '密码'
email = '邮箱'

# 教务服务/我的成绩，打开 devtools 找 POST 表单数据里的 semesterId
# 每个学期不一样，摆烂了懒得写
semester_id = 385

# 发送邮件相关
mail_host = ''
mail_port = ''
mail_user = ''
mail_password = ''
mail_sender = ''

# 数据库相关
db_host = ''
db_port = 3306
db_name = ''
db_user = ''
db_password = ''

```
