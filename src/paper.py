import json
import time
from selenium import webdriver
chrome_options = webdriver.ChromeOptions()
options = webdriver.ChromeOptions()
options.add_argument(r'--user-data-dir=C:\Users\Ishimura\AppData\Roaming\Opera Software\Opera Stable')
options.binary_location = r"C:\Program Files\Opera\55.0.2994.44\opera.exe"

driver = webdriver.Chrome(executable_path=r"C:\Users\Ishimura\Downloads\operadriver_win64\operadriver_win64\operadriver.exe", chrome_options=options)

def get_update(driver, offset):
    driver.get('https://api.telegram.org/bot451415684:AAFJ5RJ523tchgbfaahoVL_cTfGvERKTQGg/getUpdates?offset=%s&timeout=100' % offset)
    txt = driver.find_element_by_tag_name('pre').text
    format_json = json.loads(txt)
    return format_json

def send_msg(driver, chat_id, txt):
    driver.get('https://api.telegram.org/bot451415684:AAFJ5RJ523tchgbfaahoVL_cTfGvERKTQGg/sendMessage?chat_id=%s&text=%s' % (chat_id, txt))
    txt = driver.find_element_by_tag_name('pre').text
    format_json = json.loads(txt)
    return format_json

offset = 0

while 1:
    upd = get_update(driver, offset)
    print(len(upd['result']))
    for update in upd['result']:
        offset = int(update['update_id']) + 1
        if 'message' not in update or 'text' not in update['message']:
            continue
        txt = update['message']['text']
        chat_id = update['message']['chat']['id']
        upd = send_msg(driver, chat_id, txt)
    time.sleep(1)
