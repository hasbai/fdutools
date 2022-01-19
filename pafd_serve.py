import sys
import time
from io import StringIO

import pymysql

import config
from config import db_host, db_port, db_name, db_user, db_password
from pafd import Pafd
from utils.mail import send_email

MAX_RETRY = 5


def fetch_data():
    con = pymysql.connect(host=db_host, port=db_port, database=db_name, user=db_user, password=db_password)
    cursor = con.cursor()
    cursor.execute('select uid, password, name from student')
    data = cursor.fetchall()
    con.close()
    return data


def serialize(student):
    uid = student[0]
    domain = 'm.fudan.edu.cn' if int(uid[:2]) > 20 else 'fudan.edu.cn'
    email = f'{uid}@{domain}'
    return {
        'uid': student[0],
        'password': student[1],
        'name': student[2],
        'email': email
    }


if __name__ == '__main__':
    for datum in fetch_data():
        datum = serialize(datum)
        uid = datum['uid']
        password = datum['password']
        name = datum['name']
        email = datum['email']
        print('[I]', name, '开始提交')

        sys.stdout = message = StringIO()
        for i in range(MAX_RETRY + 1):
            time.sleep(1)
            pafd = Pafd(username=uid, password=password)
            result = pafd.main()
            print(result.get('message'))
            if result.get('code') == -1:
                print('[W] 提交失败，', end='')
                if i < MAX_RETRY:
                    print(f'重试中...[{i + 1}/{MAX_RETRY}]')
                else:
                    print('达到最大重试次数')
                    send_email(
                        '平安复旦提交失败',
                        f'{name}今天的平安复旦提交失败，原因为：\n{message.getvalue()}\n请手动提交！',
                        [email, config.email]
                    )
            else:
                break

        sys.stdout = sys.__stdout__
        print(message.getvalue())
