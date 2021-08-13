import pymysql

from config import db_host, db_port, db_name, db_user, db_password
from pafd import Pafd


def fetch_data():
    con = pymysql.connect(host=db_host, port=db_port, database=db_name, user=db_user, password=db_password)
    cursor = con.cursor()
    cursor.execute('select uid, password, name from student')
    data = cursor.fetchall()
    con.close()
    return data


if __name__ == '__main__':
    for datum in fetch_data():
        name = datum[2]
        pafd = Pafd(username=datum[0], password=datum[1])
        print('[I]', name, '开始提交')
        print(pafd.main().get('message'))
