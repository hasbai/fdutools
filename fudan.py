import os
import time
from functools import wraps

import httpx
from bs4 import BeautifulSoup

import config

HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'DNT': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML like Gecko) Chrome/91.0.4472.114 Safari/537.36'
}


def proxies():
    if os.environ.get('ENV') == 'development':
        return os.environ.get('HTTP_PROXY')
    else:
        return None


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
            print('[W] 请求过于频繁，0.2s 后再次请求')
            time.sleep(0.2)
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

        self.login_url = 'https://uis.fudan.edu.cn/authserver/login'
        self.logout_url = 'https://uis.fudan.edu.cn/authserver/logout'
        self.login_service = ''
        self.logout_service = ''

        self.c = Client(headers=HEADERS, proxies=proxies())

    def __enter__(self):
        self.login()
        return self

    def __exit__(self, *args):
        self.close()

    def login(self):
        data = {
            'username': self.username,
            'password': self.password,
        }

        r = self.c.get(self.login_url, timeout=10.0)
        assert r.status_code == 200, '网络错误'

        soup = BeautifulSoup(r.text, features='lxml')
        for item in soup.find_all(name='input', attrs={'type': 'hidden'}):
            data[item['name']] = item['value']

        r = self.c.post(
            self.login_url,
            data=data
        )
        assert r.status_code == 302, '登录失败'
        # print('[I] 已登录')

    def close(self):
        r = self.c.get(self.logout_url, params={'service': self.logout_service}, timeout=10.0)  # 有时会超时
        if r.status_code == 302:
            # print('[I] 已登出')
            pass
        else:
            print('[W] 登出失败！')
        self.c.close()


if __name__ == '__main__':
    with Fudan(config.username, config.password) as fd:
        pass
