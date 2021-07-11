import json

import config
import utils
from fudan import Fudan


def grade_report(user):
    username = user['username']
    password = user['password']
    email = user['email']

    try:
        c = Fudan(username, password)
        c.login()
        grades = c.get_grade(config.semester_id)
        gpa_report = c.get_gpa()
    except Exception as e:
        print(e)
    finally:
        c.close()

    [print(grade) for grade in grades]
    print(gpa_report)

    try:
        with open('result.json', 'r') as file:
            grade_nums = json.load(file)
    except Exception:
        pass
        grade_nums = {}

    if not grade_nums.get(username):
        grade_nums[username] = 0

    if grade_nums[username] != len(grades):
        grade_nums[username] = len(grades)
        content = '\r\n'.join(grades) + gpa_report
        utils.send_email('考试成绩快报', content, [email])

        with open('result.json', 'w') as file:
            json.dump(grade_nums, file)


if __name__ == '__main__':
    for user in config.users:
        grade_report(user)
