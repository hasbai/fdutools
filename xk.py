import re
import time
from io import BytesIO

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

    def login(self):
        data = {
            'username': self.username,
            'password': self.password,
        }

        r = self.c.post(
            self.login_url,
            data=data,
            allow_redirects=False
        )
        assert r.status_code == 302, '登录失败'

    def get_xk(self):
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

    def show_courses_table(self):
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

    def operate_course(self, course_no, mode='select'):
        course_id = self.query_course(course_no)
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

    def captcha(self):
        captcha_url = 'https://xk.fudan.edu.cn/xk/captcha/image.action'
        r = self.c.get(captcha_url)
        image = Image.open(BytesIO(r.content))
        image.show()

        result = input('请输入验证码（不区分大小写）')
        return result

    def main(self, course_id):
        try:
            self.login()
            self.get_xk()
            self.operate_course(course_id, 'drop')
            self.operate_course(course_id, 'select')
            self.show_courses_table()

        except Exception as e:
            print('[E] {}'.format(e))
        finally:
            self.close()


if __name__ == '__main__':
    xk = Xk(config.username, config.password)
    xk.main('FORE110068.01')

    # try:
    #     xk.login()
    #     xk.captcha()
    # except Exception as e:
    #     traceback.print_exc()
    #     print('[E] {}'.format(e))
    # finally:
    #     xk.close()
