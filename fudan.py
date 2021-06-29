from lxml import etree
from bs4 import BeautifulSoup


def login(c, uis_url, service_url, username, password):
    r = c.get(uis_url, params={'service': service_url})
    assert r.status_code == 200, '网络错误'

    html = etree.HTML(r.text, etree.HTMLParser())
    data = {
        'username': username,
        'password': password,
    }
    data.update(zip(
        html.xpath("/html/body/form/input/@name"),
        html.xpath("/html/body/form/input/@value")
    ))

    r = c.post(
        uis_url,
        params={'service': service_url},
        headers={
            'Host':     'uis.fudan.edu.cn',
            'Origin':   'https://uis.fudan.edu.cn',
        },
        data=data,
        allow_redirects=False
    )

    assert service_url + '?ticket' in r.headers['location'], '登录失败'


def logout(c, logout_url, login_url):
    r = c.get(logout_url)
    response_url = str(r.url)
    assert login_url in response_url, '{} is not in {}'.format(login_url, response_url)


def get_grade(c, semester_id):
    r = c.get('https://jwfw.fudan.edu.cn/eams/teach/grade/course/person!search.action',
              params={'semesterId': semester_id})
    if '当前用户存在重复登录的情况' in r.text:
        soup = BeautifulSoup(r.text, features='lxml')
        r = c.get(soup.a['href'], params={'semesterId': semester_id})

    soup = BeautifulSoup(r.text, features='lxml')
    result = []
    for item in soup.tbody.children:
        strings = list(item.stripped_strings)
        result.append(strings[3] + ' ' + strings[6])
    return result


def get_gpa(c):
    r = c.get('https://jwfw.fudan.edu.cn/eams/myActualGpa!search.action')
    if '当前用户存在重复登录的情况' in r.text:
        soup = BeautifulSoup(r.text, features='lxml')
        r = c.get(soup.a['href'])

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
