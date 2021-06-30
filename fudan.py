from bs4 import BeautifulSoup
import httpx
import config


class Fudan:
    def __init__(self, username, password):
        self.c = httpx.Client(headers={'User-Agent': config.ua})

        self.username = username
        self.password = password

    def login(self, service_url):
        r = self.c.get(config.uis_url, params={'service': service_url})
        assert r.status_code == 200, '网络错误'

        data = {
            'username': self.username,
            'password': self.password,
        }
        soup = BeautifulSoup(r.text, features='lxml')
        for item in soup.find_all(name='input', attrs={'type': 'hidden'}):
            data[item['name']] = item['value']

        r = self.c.post(
            config.uis_url,
            params={'service': service_url},
            headers={
                'Host': 'uis.fudan.edu.cn',
                'Origin': 'https://uis.fudan.edu.cn',
            },
            data=data,
            allow_redirects=False
        )

        assert service_url + '?ticket' in r.headers['location'], '登录失败'

    def close(self, logout_url):
        r = self.c.get(logout_url)
        self.c.close()
        # response_url = str(r.url)
        # assert config.uis_url in response_url, '{} is not in {}'.format(config.uis_url, response_url)

    # def close(self):
    #     self.c.close()

    def get_grade(self, semester_id):
        r = self.c.get('https://jwfw.fudan.edu.cn/eams/teach/grade/course/person!search.action',
                       params={'semesterId': semester_id})
        if '当前用户存在重复登录的情况' in r.text:
            soup = BeautifulSoup(r.text, features='lxml')
            r = self.c.get(soup.a['href'], params={'semesterId': semester_id})

        soup = BeautifulSoup(r.text, features='lxml')
        result = []
        for item in soup.tbody.children:
            strings = list(item.stripped_strings)
            result.append(strings[3] + ' ' + strings[6])
        return result

    def get_gpa(self):
        r = self.c.get('https://jwfw.fudan.edu.cn/eams/myActualGpa!search.action')
        if '当前用户存在重复登录的情况' in r.text:
            soup = BeautifulSoup(r.text, features='lxml')
            r = self.c.get(soup.a['href'])

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
