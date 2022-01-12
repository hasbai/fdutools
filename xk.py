import re
import time
from io import BytesIO
from threading import Thread
from typing import Union

import dataframe_image as dfi
import demjson3
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

    def __enter__(self):
        # with环境下自动登录
        self.login()
        self.init_xk()
        return self

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

    def init_xk(self):
        xk_url = 'https://xk.fudan.edu.cn/xk/stdElectCourse!defaultPage.action'

        # 获取 profile_id
        r = self.c.get(xk_url, follow_redirects=True)
        soup = BeautifulSoup(r.text, features='lxml')
        tag = soup.find(name='input', attrs={'type': 'hidden'})

        self.profile_id = tag['value']

        time.sleep(0.2)  # 等待 0.2s

        # 需要先访问选课页面才能获得已选课程
        data = {tag['name']: tag['value']}
        r = self.c.post(xk_url, data=data)
        assert r.status_code == 200, '访问选课页面失败！'

    def query_courses(self, no='', code='', name='') -> list[dict]:
        """
        Args:
            no:     课程序号    eg. ECON130213.01
            code:   课程代码    eg. ECON130213
            name:   课程名称    eg. 计量经济学

        Returns:
            list 包含所有已选的课再加上满足查询条件的课

        """
        query_course_url = 'https://xk.fudan.edu.cn/xk/stdElectCourse!queryLesson.action'
        r = self.c.post(
            query_course_url,
            params={'profileId': self.profile_id},
            data={'lessonNo': no, 'courseCode': code, 'courseName': name}
        )
        assert r.status_code == 200, '查询课程失败！'
        texts = r.text.split('\n')
        courses = demjson3.decode(re.search(r'\[.*]', texts[0]).group())  # 课程信息
        amounts = demjson3.decode(re.search(r'{.*}', texts[1]).group())  # 已选/上限 人数

        # 将已选/上限信息添加进课程信息中，默认为 0
        for course in courses:
            has_key = str(course['id']) in amounts.keys()
            course['current_amount'] = amounts[str(course['id'])]['sc'] if has_key else 0
            course['maximum_amount'] = amounts[str(course['id'])]['lc'] if has_key else 0

        return courses

    def class_schedule(self, print_schedule=True) -> list[list[str]]:
        # 生成课表
        array = [[''] * 7 for i in range(14)]
        for course in self.query_courses():
            start_unit = course['arrangeInfo'][0]['startUnit']
            end_unit = course['arrangeInfo'][0]['endUnit']
            weekday = course['arrangeInfo'][0]['weekDay']
            for i in range(start_unit - 1, end_unit):
                array[i][weekday] = course['name']

        # 打印课表
        if print_schedule:
            df = pd.DataFrame(
                data=array,
                columns=['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'],
                index=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
            )

            bytes_buffer = BytesIO()
            dfi.export(df.style, bytes_buffer)
            image = Image.open(bytes_buffer)
            image.show()

        return array

    def query_inner_id(self, courses=None, many=False, **kwargs) -> Union[str, set[str]]:
        if not courses:
            courses = self.query_courses(**kwargs)
        results = set()
        for course in courses:
            for field in ('no', 'code', 'name'):
                if course[field] == kwargs.get(field):
                    results.add(course['id'])
        if len(results) == 0:
            raise Exception('没有找到这门课！{}'.format(kwargs))
        return results if many else results.pop()

    def _operate_course(self, inner_id: str, mode='select') -> bool:
        """
        Args:
            inner_id: 内部 id
            mode: select 或 drop

        Returns: Boolean
        """
        operate_course_url = 'https://xk.fudan.edu.cn/xk/stdElectCourse!batchOperator.action'
        data = {'optype': 'true', 'operator0': '{}:true:0'.format(inner_id)} \
            if mode == 'select' else \
            {'optype': 'false', 'operator0': '{}:false'.format(inner_id)}

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

    def operate_course(self, *args, **kwargs) -> bool:
        try:
            return self._operate_course(*args, **kwargs)
        except Exception as e:
            print(f'[E] {e}')
            return False

    def select(self, inner_id: str) -> bool:
        return self.operate_course(inner_id, mode='select')

    def drop(self, inner_id: str) -> bool:
        return self.operate_course(inner_id, mode='drop')


class User:
    def __init__(self, username: str, password: str, courses=None, **kwargs):
        self.username = username
        self.password = password
        if courses is None:
            courses = []
        self.course_names = courses
        with Xk(username, password) as xk:
            self.class_schedule = xk.class_schedule(print_schedule=False)
            self.selected_courses = xk.query_courses()

    def filter_available(self, xk) -> set[str]:
        ids = set()

        for course_name in self.course_names:
            if '.' in course_name:
                kwargs = {'no': course_name}
            elif course_name[0].isascii():
                kwargs = {'code': course_name}
            else:
                kwargs = {'name': course_name}
            courses = xk.query_courses(**kwargs)
            key = list(kwargs.keys())[0]  # 仅限 kwargs 只有一个元素
            for course in filter(lambda i: i[key] == kwargs[key], courses):
                start_unit = course['arrangeInfo'][0]['startUnit']
                end_unit = course['arrangeInfo'][0]['endUnit']
                weekday = course['arrangeInfo'][0]['weekDay']
                occupied = False
                for i in range(start_unit - 1, end_unit):
                    occupied = occupied or self.class_schedule[i][weekday]
                available = course['current_amount'] < course['maximum_amount']
                if not occupied and available:
                    ids.add(course['id'])

        return ids

    def simple_select(self):
        with Xk(self.username, self.password) as xk:
            while True:
                available_ids = self.filter_available(xk=xk)
                print('available ids:', available_ids)
                for id in available_ids:
                    # 每个 session 的第一次选课不需要验证码，故每次操作都实例化一次
                    with Xk(self.username, self.password) as inner_xk:
                        success = inner_xk.select(inner_id=id)


def threading():
    thread_pool = []
    for user_config in config.users:
        user = User(**user_config)
        thread = Thread(target=user.simple_select)
        thread_pool.append(thread)
        thread.start()
    for thread in thread_pool:
        thread.join()


if __name__ == '__main__':
    user = User(**config.users[0])
    user.simple_select()
    # user = User(**config.users[0])
    # print(user.target_ids)
