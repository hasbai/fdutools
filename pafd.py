import sys
import time
import traceback
from io import StringIO

import demjson

import config
from fudan import Fudan
from utils.captcha import recognize

MAX_CAPTCHA_RETRY = 5


class Pafd(Fudan):
    def __init__(self, username, password):
        super().__init__(username, password)
        self.has_submitted = False
        self.form_data = {}
        self.code = -1

    def captcha(self):
        captcha_url = 'https://zlapp.fudan.edu.cn/backend/default/code'
        r = self.c.get(captcha_url)
        return recognize(r.content)

    def check(self):
        """
        检查今日是否已提交
        """
        r = self.c.get('https://zlapp.fudan.edu.cn/ncov/wap/fudan/get-info', follow_redirects=True)
        last_info = r.json()["d"]["info"]

        date = last_info["date"]
        today = time.strftime("%Y%m%d", time.localtime())
        address = demjson.decode(last_info['geo_api_info'])['formattedAddress']
        message = "  日期：{}，地址：{}".format(date, address)

        if date == today and not self.has_submitted:
            print("[I] 今日已提交", message)
            self.code = 1
        elif date == today and self.has_submitted:
            print("[I] 提交成功", message)
            self.code = 0
        elif date != today and self.has_submitted:
            print("[E] 提交失败", message)
            self.code = -1
        else:
            self.form_data = last_info

    def submit(self):
        """
        执行提交
        """
        if not self.form_data:
            return

        address = demjson.decode(self.form_data["geo_api_info"])["addressComponent"]
        province = address.get("province", "")
        district = address.get("district", "")
        city = address.get("city", "") or province  # 防止缺少 city 字段报错
        sfzx = self.form_data.get('sfzx') or 1
        self.form_data.update({
            "province": province,
            "city": city,
            "area": " ".join((province, city, district)),
            'sfzx': sfzx,
        })

        for i in range(MAX_CAPTCHA_RETRY + 1):
            self.form_data['code'] = self.captcha()  # 填写验证码
            r = self.c.post(
                'https://zlapp.fudan.edu.cn/ncov/wap/fudan/save',
                data=self.form_data
            )
            error = r.json()['e'] != 0
            message = r.json()["m"]
            if error:
                if '验证码' in message:
                    print('[W] 验证码识别失败，', end='')
                    if i == MAX_CAPTCHA_RETRY:
                        print('达到最大重试次数')
                    else:
                        print(f'重试中...[{i + 1}/{MAX_CAPTCHA_RETRY}]')
                        continue
                print('[E] 提交失败', message)
                self.code = -1
                break
            else:
                self.has_submitted = True
                self.check()  # 再检查一次
                break

    def main(self):
        sys.stdout = message = StringIO()
        try:
            self.login()
            self.check()
            self.submit()
            self.close()
        except Exception as e:
            traceback.print_exc()
            print(f'[E] {e}')
            self.code = -1
        finally:
            sys.stdout = sys.__stdout__
            return {'message': message.getvalue(), 'code': self.code}


if __name__ == '__main__':
    pafd = Pafd(config.username, config.password)
    result = pafd.main()
    print(result['message'], result['code'])
