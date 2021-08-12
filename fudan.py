import time
from functools import wraps

import httpx
from bs4 import BeautifulSoup


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
    def __init__(self, username, password):
        self.username = username
        self.password = password

        self.ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML like Gecko) Chrome/91.0.4472.114 Safari/537.36'
        self.login_url = 'https://uis.fudan.edu.cn/authserver/login'
        self.logout_url = 'https://uis.fudan.edu.cn/authserver/logout'

        self.c = Client(headers={'User-Agent': self.ua})

    def login(self):
        data = {
            'username': self.username,
            'password': self.password,
        }

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
            print('[I] 已登出')
        else:
            print('[W] 登出失败！')
        self.c.close()
