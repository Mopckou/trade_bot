import os
from src.telegram_bot import TBot
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from selenium import webdriver
from src.config import token
from selenium.common.exceptions import TimeoutException

NAME = 'TRADE_DATA_BASE.db'
DATABASE = os.path.abspath(
    os.path.join(
        os.path.split(__file__)[0], 'src', 'db', NAME
    )
)
binary_loc = r"C:\Users\a.ermakov\AppData\Local\Programs\Opera\60.0.3255.70\opera.exe"
chrome_driver_loc = r"C:\OTbot\src\operadriver_win64\operadriver.exe"
opera_settings = r'C:\Users\a.ermakov\AppData\Roaming\Opera Software\Opera Stable Work'

options = webdriver.ChromeOptions()
options.add_argument(r'--user-data-dir=%s' % opera_settings)
options.binary_location = binary_loc


def main():
    while 1:
        driver = webdriver.Chrome(executable_path=chrome_driver_loc, chrome_options=options)

        engine = create_engine('sqlite:///%s' % DATABASE, echo=False)
        sm = sessionmaker(bind=engine)
        session = sm()

        try:
            bot = TBot(driver, token, session)
            bot.run()
        except TimeoutException:
            print('Перезапуск драйвера!')
            driver.quit()
        except Exception:
            raise


if __name__ == '__main__':
    main()
