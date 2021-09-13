import time

import demjson

import config
from fudan import Fudan


class Pafd(Fudan):
    def __init__(self, username, password):
        super().__init__(username, password)
        self.has_submitted = False
        self.message = ''
        self.code = -1

    def check(self):
        """
        检查今日是否已提交
        """
        r = self.c.get('https://zlapp.fudan.edu.cn/ncov/wap/fudan/get-info')
        last_info = r.json()["d"]["info"]

        date = last_info["date"]
        today = time.strftime("%Y%m%d", time.localtime())
        address = demjson.decode(last_info['geo_api_info'])['formattedAddress']
        message = "  日期：{}，地址：{}".format(date, address)

        if date == today and not self.has_submitted:
            self.message = "[I] 今日已提交" + message
            self.code = 1
        elif date == today and self.has_submitted:
            self.message = "[I] 提交成功" + message
            self.code = 0
        elif date != today and self.has_submitted:
            self.message = '[E] 提交失败' + message
            self.code = -1
        else:
            return last_info

    def submit(self):
        """
        执行提交
        """
        data = self.check()
        if not data:
            return

        address = demjson.decode(data["geo_api_info"])["addressComponent"]
        province = address.get("province", "")
        district = address.get("district", "")
        city = address.get("city", "")
        if not city:
            city = province

        data.update({
            "province": province,
            "city": city,
            "area": " ".join((province, city, district))
        })

        r = self.c.post(
            'https://zlapp.fudan.edu.cn/ncov/wap/fudan/save',
            data=data,
            allow_redirects=False
        )

        if r.json()['e'] != 0:
            self.message = '[E] 提交失败 ' + r.json()["m"]
            self.code = -1
        else:
            self.has_submitted = True
            self.check()  # 再检查一次

    def main(self):
        try:
            self.login()
            self.submit()
        except Exception as e:
            self.message += '[E] {}'.format(e)
            self.code = -1
        finally:
            self.close()
            return {'message': self.message, 'code': self.code}


if __name__ == '__main__':
    pafd = Pafd(config.username, config.password)
    print(pafd.main())
