import time
import json
import random
from src.ban_list import gaijins
from urllib.parse import quote_plus
from src.dbase import DISPATCH, REPORT
from src.commands import NEW, EDIT, RETURN, SUBSCRIPTION, INFO
from selenium.common.exceptions import NoSuchElementException, TimeoutException


def filter_banned(func):

    def _func(*args, **kwargs):
        obj, user = [*args][0], [*args][1]
        if user in gaijins and gaijins[user]:
            msg = random.choice(gaijins[user])
            print('Забаненный пользователь постучался. %s. Пользовательно получил сообщение - %s' % (user, msg))
            try:
                func(obj, user, msg)
            except Exception as e:
                if 'Error - 403' in e.__str__():
                    pass
        elif user in gaijins and not gaijins[user]:
            print('Забаненный пользователь постучался. %s' % user)
            return
        else:
            return func(*args, **kwargs)

    return _func


class TBot:
    HTTP_ADDR = r'https://api.telegram.org'
    offset = 0
    active_of_session = {}
    special_commands = {'/new': NEW,
                        '/edit': EDIT,
                        '/return': RETURN,
                        '/sub': SUBSCRIPTION,
                        '/info': INFO,
                        '/photo': None}

    ans = "Поддерживаемые команды:\n\n\n" \
          "/info - информация по парам\n\n" \
          "/new - создание новой пары\n\n" \
          "/edit - редактирование настроек пары\n\n" \
          "/return - восставноление пары из архива\n\n" \
          "/sub - подписка на рассылку уведовлений"

    def __init__(self, opera_driver, token, db):
        self.browser = opera_driver
        self.token = token
        self.db = db
        self.count_error = 0
        self.answer_with_error = None

    def get_updates(self, offset):
        self.browser.get('https://api.telegram.org/bot%s/getUpdates?offset=%s&timeout=120' % (self.token, offset))
        js = self.__get_json_obj()
        if not js['ok']:
            print(js['error_code'], js['description'])
            raise Exception('Error - %s' % js['error_code'])
        return js

    @filter_banned
    def send_msg(self, chat_id, txt, data=None, parse_mode=None):
        txt = quote_plus(txt)
        req = 'https://api.telegram.org/bot%s/sendMessage?chat_id=%s&text=%s' % (self.token, chat_id, txt)

        if parse_mode is not None:
            req += '&parse_mode=%s' % parse_mode

        if data is not None:
            req += '&%s' % data

        self.browser.get(req)
        js = self.__get_json_obj()
        if not js['ok']:
            print(js['error_code'], js['description'])
            self.answer_with_error = js
            raise Exception('Error - %s' % js['error_code'])
        return js

    # def send_image(self, chat_id, image_path):
    #     files = {'photo': open(image_path, 'rb')}
    #     # from requests_toolbelt import MultipartEncoder
    #     # multipart_data = MultipartEncoder(
    #     #     fields={
    #     #         # a file upload field
    #     #         'file': ('file.py', open(image_path, 'rb'), 'text/plain')
    #     #     }
    #     # )
    #
    #     # print(multipart_data.boundary)
    #     from urllib import parse
    #     data = parse.urlencode(files)
    #     self.browser.get('https://api.telegram.org/bot%s/sendPhoto?chat_id=%s&%s' % (self.token, chat_id, data))
    #     js = self.__get_json_obj()
    #     if not js['ok']:
    #         print(js['error_code'], js['description'])
    #         raise Exception('Error - %s' % js['error_code'])
    #     return js

    def __get_json_obj(self):
        txt = self.browser.find_element_by_tag_name('pre').text
        return json.loads(txt)

    def clear_session_of_done(self):
        while 1:
            for chat_id in self.active_of_session:
                if self.active_of_session[chat_id].session_is_done():
                    self.active_of_session.pop(chat_id)
                    break
                if self.active_of_session[chat_id].is_timeouted():
                    self.active_of_session.pop(chat_id)
                    #self.send_msg(chat_id, 'Сессия завершена.')
                    break
            else:
                return

    def send_message_to_all(self):
        try:
            reports = self.db.query(REPORT).all()
            for report in reports:
                if report.user_id == 0:
                    self.send_all(report.data)
                else:
                    self.send_msg(report.user_id, report.data)
                self.db.delete(report)
            self.db.commit()
        except Exception as e:
            print(e)

    def send_all(self, data):
        dispatch_all = self.db.query(DISPATCH).all()
        for d in dispatch_all:
            self.send_msg(d.user_id, data)

    def run(self):
        while 1:
            try:
                upd = self.get_updates(self.offset)
                print(len(upd['result']))

                for update in upd['result']:
                    self.offset = int(update['update_id']) + 1
                    if 'message' not in update or 'text' not in update['message']:
                        continue

                    txt = update['message']['text']
                    chat_id = update['message']['chat']['id']

                    if txt in self.special_commands:

                        if txt == '/photo':
                            continue

                        if chat_id in self.active_of_session:
                            self.active_of_session.pop(chat_id)
                            self.send_msg(chat_id, 'Предыдущая сессия завершена.')

                        new_session = self.special_commands[txt]
                        self.active_of_session.update(
                            {chat_id: new_session(chat_id, self.send_msg, self.db)}
                        )

                    if chat_id in self.active_of_session:
                        session = self.active_of_session[chat_id]
                        if session.session_is_done():
                            self.send_msg(chat_id, self.ans)
                        else:
                            session.run(txt)
                    else:
                        self.send_msg(chat_id, self.ans)

                self.clear_session_of_done()
                self.send_message_to_all()
                time.sleep(1)
            except NoSuchElementException:
                print('Ошибка получения элемента страницы.')
            except TimeoutException:
                print('TIMEOUT!')
                self.count_error += 1
                if self.count_error > 10:
                    raise
            except Exception as ex:
                if 'Error - 500' in ex.__str__():
                    print(u'Ошибка 500.')
                    time.sleep(5)
                elif 'Error - 502' in ex.__str__():
                    print(u'Ошибка 502.')
                elif 'Error - 429' in ex.__str__():
                    timer = self.answer_with_error['parameters']['retry_after']

                    print(u'Слишком много запросов. Ждем %s секунд.' % timer)
                    time.sleep(timer)
                elif 'Error - 400' in ex.__str__():
                    pass
                else:
                    raise
