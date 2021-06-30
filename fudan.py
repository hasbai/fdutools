from bs4 import BeautifulSoup
import httpx
import config
from functools import wraps


def repeated_login(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        r = func(*args, **kwargs)
        if '当前用户存在重复登录的情况' in r.text:
            soup = BeautifulSoup(r.text, features='lxml')
            new_url = soup.a['href']
            args = list(args)
            args[1] = new_url
            return func(*args, **kwargs)
        else:
            return r

    return wrapper


class Client(httpx.Client):
    @repeated_login
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)


class Fudan:
    def __init__(self, username, password):
        self.c = Client(headers={'User-Agent': config.ua})

        self.username = username
        self.password = password

    def login(self):
        r = self.c.get(config.login_url)
        assert r.status_code == 200, '网络错误'

        data = {
            'username': self.username,
            'password': self.password,
        }
        soup = BeautifulSoup(r.text, features='lxml')
        for item in soup.find_all(name='input', attrs={'type': 'hidden'}):
            data[item['name']] = item['value']

        r = self.c.post(
            config.login_url,
            data=data,
            allow_redirects=False
        )
        assert r.status_code == 302, '登录失败'

    def close(self):
        r = self.c.get(config.logout_url)
        if r.status_code == 200: print('已登出')
        self.c.close()

    def get_grade(self, semester_id):
        r = self.c.get(config.grade_url,
                       params={'semesterId': semester_id})

        soup = BeautifulSoup(r.text, features='lxml')
        result = []
        for item in soup.tbody.children:
            strings = list(item.stripped_strings)
            result.append(strings[3] + ' ' + strings[6])
        return result

    def get_gpa(self):
        r = self.c.get(config.gpa_url)

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


if __name__ == '__main__':
    c = Fudan(config.username, config.password)
    try:
        c.login()
        print(c.get_grade(config.semester_id))
    except Exception as e:
        print(e)
    finally:
        c.close()
