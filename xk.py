import re
import time
from io import BytesIO
from threading import Thread

import dataframe_image as dfi
import demjson
import pandas as pd
from PIL import Image
from bs4 import BeautifulSoup

import config
from fudan import Fudan


class Xk(Fudan):
    def __init__(self, username, password):
        super().__init__(username, password)
        self.login_url = 'https://xk.fudan.edu.cn/xk/login.action'
        self.logout_url = 'https://xk.fudan.edu.cn/xk/logout.action'

        self.profile_id = 0

        # 实例化时自动登录
        self.login()
        self.init_xk()

    def login(self):
        data = {
            'username': self.username,
            'password': self.password,
        }

        r = self.c.post(
            self.login_url,
            data=data
        )
        assert r.status_code == 302, '登录失败'
        print('[I] 已登录')

    def init_xk(self):
        xk_url = 'https://xk.fudan.edu.cn/xk/stdElectCourse!defaultPage.action'

        # 获取 profile_id
        r = self.c.get(xk_url)
        soup = BeautifulSoup(r.text, features='lxml')
        tag = soup.find(name='input', attrs={'type': 'hidden'})
        self.profile_id = tag['value']

        time.sleep(0.2)  # 等待 0.2s

        # 需要先访问选课页面才能获得已选课程
        data = {tag['name']: tag['value']}
        r = self.c.post(xk_url, data=data)
        assert r.status_code == 200, '访问选课页面失败！'

    def class_schedule(self):
        # 获取已选课程
        query_course_url = 'https://xk.fudan.edu.cn/xk/stdElectCourse!queryLesson.action'
        r = self.c.get(query_course_url, params={'profileId': self.profile_id})
        assert r.status_code == 200, '查询课表失败！'
        text = re.search(r'\[.*]', r.text).group()
        selected_courses = demjson.decode(text)  # dict

        # 生成课表
        array = [[''] * 7 for i in range(14)]
        for course in selected_courses:
            start_unit = course['arrangeInfo'][0]['startUnit']
            end_unit = course['arrangeInfo'][0]['endUnit']
            weekday = course['arrangeInfo'][0]['weekDay']
            for i in range(start_unit - 1, end_unit):
                array[i][weekday - 1] = course['name']

        # 打印课表
        df = pd.DataFrame(
            data=array,
            columns=['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'],
            index=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
        )

        bytes_buffer = BytesIO()
        dfi.export(df.style, bytes_buffer)
        image = Image.open(bytes_buffer)
        image.show()

    def query_course_id(self, course_no):
        """
        Args:
            course_no: 唯一课程 id （例：FORE110068.01）

        Returns:
            内部课程 id，用于选课
        """

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

    def operate_course(self, course_no, mode='select'):
        """
        Args:
            course_no: 唯一课程 id （例：FORE110068.01）
            mode: select 或 drop

        Returns: Boolean
        """
        course_id = self.query_course_id(course_no)
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

        is_success = '成功' in message
        suffix = '[I]' if is_success else '[W]'
        print(f'{suffix} {self.username}: {message}')
        return is_success

    def select(self, course_no):
        return self.operate_course(course_no, mode='select')

    def drop(self, course_no):
        return self.operate_course(course_no, mode='drop')

    # def captcha(self):
    #     captcha_url = 'https://xk.fudan.edu.cn/xk/captcha/image.action'
    #     r = self.c.get(captcha_url)
    #     image = Image.open(BytesIO(r.content))
    #     image.show()
    #
    #     result = input('请输入验证码（不区分大小写）')
    #     return result


def simple_select(username, password, course):
    success = False
    try:
        # 每个 session 的第一次选课不需要验证码，故每次操作都实例化一次
        xk = Xk(username, password)
        success = xk.select(course)
        xk.close()
    except Exception as e:
        print(f'[E] {e}')
    finally:
        return success


def main(username, password, courses):
    flags = [False for i in range(len(courses))]

    # 主循环
    while True:
        for i in range(len(courses)):
            if flags[i]:
                continue
            flags[i] = simple_select(username, password, courses[i])

        # 退出条件
        success = True
        for flag in flags:
            success = success and flag
        if success:
            break


if __name__ == '__main__':
    thread_pool = []
    for user in config.users:
        username = user.get('username', '')
        password = user.get('password', '')
        courses = user.get('courses', [])
        thread = Thread(target=main, args=(username, password, courses))
        thread.name = username
        thread_pool.append(thread)
        thread.start()
    for thread in thread_pool:
        thread.join()
