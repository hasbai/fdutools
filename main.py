import config
import utils
from fudan import Fudan


def grade_report():
    try:
        c = Fudan(config.username, config.password)
        c.login(config.jwfw_url)
        grades = c.get_grade(config.semester_id)
        gpa_report = c.get_gpa()
    except Exception as e:
        print(e)
    finally:
        c.close(config.jwfw_logout_url)

    try:
        with open('result.txt', 'r') as file:
            grades_num = int(file.readline())
    except (ValueError, FileNotFoundError):
        with open('result.txt', 'w') as file:
            file.write('0')
        grades_num = 0

    if grades_num != len(grades):
        [print(grade) for grade in grades]
        print(gpa_report)

        content = ''
        for s in grades:
            content = content + s + '\r\n'
        content = content + gpa_report
        utils.send_email('考试成绩快报', content)

        with open('result.txt', 'w') as file:
            file.write(str(len(grades)))


if __name__ == '__main__':
    grade_report()
