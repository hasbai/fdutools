import re
from io import BytesIO

import easyocr
import httpx
from PIL import Image

reader = easyocr.Reader(['en'])


def recognize(byte):
    li = reader.readtext(byte, detail=0, paragraph=True)
    text = li[0]
    text = re.sub(r'\s', '', text)
    return text


if __name__ == '__main__':
    captcha_url = 'https://zlapp.fudan.edu.cn/backend/default/code'
    r = httpx.get(captcha_url)
    print(recognize(r.content))
    buffer = BytesIO(r.content)
    Image.open(buffer).show()
