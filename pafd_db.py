import pymysql

from config import db_host, db_port, db_name, db_user, db_password, email
from pafd import Pafd
from utils.email import send_email


def fetch_data():
    con = pymysql.connect(host=db_host, port=db_port, database=db_name, user=db_user, password=db_password)
    cursor = con.cursor()
    cursor.execute('select uid, password, name from student')
    data = cursor.fetchall()
    con.close()
    return data


if __name__ == '__main__':
    for datum in fetch_data():
        pafd = Pafd(username=datum[0], password=datum[1])
        name = datum[2]
        print('[I]', name, '开始提交')
        result = pafd.main()
        print(result.get('message'))
        if result.get('code') == -1:
            print('[I] 提交失败，再次提交')
            result = pafd.main()
            print(result.get('message'))
            if result.get('code') == -1:
                send_email(
                    '平安复旦提交失败',
                    f'{name}今天的平安复旦提交失败，原因为：{result.get("message")}，请手动提交！',
                    [f'{datum[0]}@fudan.edu.cn', email]
                )
