import time
import re
import traceback
from functools import wraps

import httpx
import demjson
from bs4 import BeautifulSoup
import prettytable as pt
import numpy as np

import config


def repeated_login(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        time.sleep(0.15)  # 暂停一段时间，防止系统检测异常（间隔为 0.1s 会报 “请不要过快点击” ）
        r = func(*args, **kwargs)
        if '当前用户存在重复登录的情况' in r.text:
            print('[I] 当前用户存在重复登录的情况，之前登录已被踢出')
            soup = BeautifulSoup(r.text, features='lxml')
            new_url = soup.a['href']
            # arg[0]是self，arg[1]是url
            args = list(args)
            args[1] = new_url
            return func(*args, **kwargs)
        elif '请不要过快点击' in r.text:
            print('[W] 请求过于频繁，0.5s 后再次请求')
            time.sleep(0.5)
            return func(*args, **kwargs)
        else:
            return r

    return wrapper


class Client(httpx.Client):
    @repeated_login
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)

    @repeated_login
    def post(self, *args, **kwargs):
        return super().post(*args, **kwargs)


class Fudan:
    def __init__(self, username, password, xk=False):
        self.username = username
        self.password = password

        self.ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML like Gecko) Chrome/91.0.4472.114 Safari/537.36'
        self.xk = xk

        self.login_url = 'https://xk.fudan.edu.cn/xk/login.action' if xk else 'https://uis.fudan.edu.cn/authserver/login'
        self.logout_url = 'https://xk.fudan.edu.cn/xk/logout.action' if xk else 'https://uis.fudan.edu.cn/authserver/logout'

        self.profile_id = 0

        self.c = Client(headers={'User-Agent': self.ua})

    def login(self):
        data = {
            'username': self.username,
            'password': self.password,
        }

        if self.xk:
            pass
        else:
            r = self.c.get(self.login_url)
            assert r.status_code == 200, '网络错误'

            soup = BeautifulSoup(r.text, features='lxml')
            for item in soup.find_all(name='input', attrs={'type': 'hidden'}):
                data[item['name']] = item['value']

        r = self.c.post(
            self.login_url,
            data=data,
            allow_redirects=False
        )
        assert r.status_code == 302, '登录失败'

    def close(self):
        r = self.c.get(self.logout_url)
        if r.status_code == 200:
            print('已登出')
        self.c.close()

    def get_grade(self, semester_id):
        grade_url = 'https://jwfw.fudan.edu.cn/eams/teach/grade/course/person!search.action'
        r = self.c.get(grade_url, params={'semesterId': semester_id})

        soup = BeautifulSoup(r.text, features='lxml')
        result = []
        for item in soup.tbody.children:
            strings = list(item.stripped_strings)
            result.append(strings[3] + ' ' + strings[6])
        return result

    def get_gpa(self):
        gpa_url = 'https://jwfw.fudan.edu.cn/eams/myActualGpa!search.action'
        r = self.c.get(gpa_url)

        soup = BeautifulSoup(r.text, features='lxml')
        gpas = []
        major = ''
        gpa = ''

        for item in soup.tbody.children:
            strings = list(item.stripped_strings)
            if strings[0][0] != '*':
                major = strings[3]
                gpa = strings[5]
                break

        for item in soup.tbody.children:
            strings = list(item.stripped_strings)
            if strings[3] == major:
                gpas.append(strings[5])

        gpas.sort()
        gpas.reverse()
        percentage = (gpas.index(gpa) + 1) / len(gpas) * 100
        return '我的绩点为：{}\n专业排名为：{:.1f}%'.format(gpa, percentage)

    def get_xk(self):
        xk_url = 'https://xk.fudan.edu.cn/xk/stdElectCourse!defaultPage.action'

        # 获取 profile_id
        r = self.c.get(xk_url)
        soup = BeautifulSoup(r.text, features='lxml')
        tag = soup.find(name='input', attrs={'type': 'hidden'})
        self.profile_id = tag['value']
        data = {tag['name']: tag['value']}
        r = self.c.post(xk_url, data=data)  # 需要先访问选课页面才能获得已选课程
        assert r.status_code == 200, '访问选课页面失败！'

    def show_courses_table(self):
        # 获取已选课程
        query_course_url = 'https://xk.fudan.edu.cn/xk/stdElectCourse!queryLesson.action'
        r = self.c.get(query_course_url, params={'profileId': self.profile_id})
        assert r.status_code == 200, '查询课表失败！'
        text = re.search(r'\[.*]', r.text).group()
        selected_courses = demjson.decode(text)  # dict

        # 生成课表
        array = np.full((14, 7), '', dtype='object')  # numpy
        for course in selected_courses:
            start_unit = course['arrangeInfo'][0]['startUnit']
            end_unit = course['arrangeInfo'][0]['endUnit']
            weekday = course['arrangeInfo'][0]['weekDay']
            for i in range(start_unit - 1, end_unit):
                array[i][weekday - 1] = course['name']

        # 打印课表
        table = pt.PrettyTable(['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'])
        for row in array:
            table.add_row(row)
        print(table)

    def query_course(self, course_no):
        def search_course_id(_courses, _course_no):
            for course in _courses:
                if course['no'] == _course_no:
                    return course['id']
            raise Exception('没有找到这门课！{}'.format(_course_no))

        query_course_url = 'https://xk.fudan.edu.cn/xk/stdElectCourse!queryLesson.action'
        r = self.c.post(
            query_course_url,
            params={'profileId': self.profile_id},
            data={'lessonNo': course_no, 'courseCode': '', 'courseName': ''}
        )
        assert r.status_code == 200, '查询课程失败！'
        text = re.search(r'\[.*]', r.text).group()
        courses = demjson.decode(text)  # dict
        return search_course_id(courses, course_no)

    def operate_course(self, course_id, mode='select'):
        operate_course_url = 'https://xk.fudan.edu.cn/xk/stdElectCourse!batchOperator.action'
        data = {'optype': 'true', 'operator0': '{}:true:0'.format(course_id)} \
            if mode == 'select' else \
            {'optype': 'false', 'operator0': '{}:false'.format(course_id)}

        r = self.c.post(
            operate_course_url,
            params={'profileId': self.profile_id},
            data=data
        )
        soup = BeautifulSoup(r.text, features='lxml')
        message = re.sub(r'\s', '', soup.body.get_text())
        print(message)

        assertion_message = '选课失败！' if mode == 'select' else '退课失败！'
        assert '成功' in message, assertion_message


if __name__ == '__main__':
    c = Fudan(config.username, config.password, xk=True)
    try:
        c.login()
        c.get_xk()
        c.show_courses_table()
        _course_id = c.query_course('PTSS110087.11')
        c.operate_course(_course_id, 'select')
        c.operate_course(_course_id, 'drop')
    except Exception as e:
        traceback.print_exc()
        print('[E] {}'.format(e))
    finally:
        c.close()
