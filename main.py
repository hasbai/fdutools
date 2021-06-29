import httpx

import config
import utils
from fudan import *

if __name__ == '__main__':

    with httpx.Client(headers={'User-Agent': config.ua}) as c:
        login(c, config.uis_url, config.jwfw_url, config.username, config.password)
        grades = get_grade(c, config.semester_id)
        gpa = get_gpa(c)
        logout(c, config.jwfw_logout_url, config.uis_url)

    with open('result.txt', 'r') as file:
        grades_num = int(file.readline())

    if grades_num != len(grades):
        print(grades)
        print(gpa)

        content = ''
        for s in grades:
            content = content + s + '\r\n'
        content = content + gpa
        utils.send_email('考试成绩快报', content)

        with open('result.txt', 'w') as file:
            file.write(str(len(grades)))
