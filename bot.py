import os
from src.data_base import TBot
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from selenium import webdriver
from src.config import token

NAME = 'TRADE_DATA_BASE.db'
DATABASE = os.path.abspath(
    os.path.join(
        os.path.split(__file__)[0], 'src', 'db', NAME
    )
)
binary_loc = r"C:\Users\a.ermakov\AppData\Local\Programs\Opera\55.0.2994.61\opera.exe"
chrome_driver_loc = r"C:\Users\a.ermakov\Documents\GitHub\trade_bot\src\operadriver_win64\operadriver.exe"
opera_settings = r'C:\Users\a.ermakov\AppData\Roaming\Opera Software\Opera Stable'

options = webdriver.ChromeOptions()
options.add_argument(r'--user-data-dir=%s' % opera_settings)
options.binary_location = binary_loc

driver = webdriver.Chrome(executable_path=chrome_driver_loc, chrome_options=options)

engine = create_engine('sqlite:///%s' % DATABASE, echo=False)
Session = sessionmaker(bind=engine)
session = Session()

bot = TBot(driver, token, session)
bot.run()