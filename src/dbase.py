import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey, Boolean
from sqlalchemy.orm import relationship

def create_bd(engine):
    metadata = MetaData()

    trade = Table('Trade', metadata,
        Column('id', Integer, primary_key=True),
        Column('burse', String),
        Column('pair', String),
        Column('token_name', String),
        Column('tokens', String),
        Column('params', String),
        Column('data', String)
    )

    task = Table('Task', metadata,
        Column('id', Integer, primary_key=True),
        Column('is_done', Boolean),
        Column('user_id', Integer),
        Column('create_time', String),
        Column('task_name', String),
        Column('data', String)
    )

    report = Table('Report', metadata,
        Column('id', Integer, primary_key=True),
        Column('user_id', Integer),
        Column('data', String)
    )

    archive = Table('Archive', metadata,
        Column('id', Integer, primary_key=True),
        Column('burse', String),
        Column('pair', String),
        Column('token_name', String),
        Column('tokens', String),
        Column('params', String),
        Column('error', String)
    )

    dispatch = Table('Dispatch', metadata,
        Column('id', Integer, primary_key=True),
        Column('user_id', Integer),
    )

    # token = Table('Token', metadata,
    #               Column('id', Integer, primary_key=True),
    #               Column('burse', String),
    #               Column('name_token', String),
    #               Column('data', String)
    #               )
    return metadata.create_all(engine)

# Функция declarative_base создаёт базовый класс для декларативной работы
Base = declarative_base()


# На основании базового класса можно создавать необходимые классы
class TRADE(Base):
    __tablename__ = 'TRADE'
    id = Column(Integer, primary_key=True)
    burse = Column(String)
    pair = Column(String)
    token_name = Column(String)
    tokens = Column(String)
    params = Column(String)
    data = Column(String)

    def __init__(self, burse, pair, token_name, tokens, params):
        self.burse = burse
        self.pair = pair
        self.token_name = token_name
        self.tokens = tokens
        self.params = params
        self.data = None

    def __repr__(self):
        return "<TRADE(burse - '%s', pair -'%s', token_name - '%s', tokens - '%s', params - '%s', data - '%s')>" % \
                     (self.burse, self.pair, self.token_name, self.tokens, self.params, self.data)


class ARCHIVE(Base):
    __tablename__ = 'ARCHIVE'
    id = Column(Integer, primary_key=True)
    burse = Column(String)
    pair = Column(String)
    token_name = Column(String)
    tokens = Column(String)
    params = Column(String)
    error = Column(String)

    def __init__(self, burse, pair, token_name, tokens, params, error):
        self.burse = burse
        self.pair = pair
        self.token_name = token_name
        self.tokens = tokens
        self.params = params
        self.error = error

    def __repr__(self):
        return "<ARCHIVE(burse - '%s', pair -'%s', token_name - '%s', tokens - '%s', params - '%s', error - '%s')>" % \
                     (self.burse, self.pair, self.token_name, self.tokens, self.params, self.error)


class TASK(Base):
    __tablename__ = 'Task'
    id = Column(Integer, primary_key=True)
    is_done = Column(Boolean)
    user_id = Column(Integer)
    create_time = Column(String)
    task_name = Column(String)
    data = Column(String)

    def __init__(self, user_id, task_name, data):
        self.user_id = user_id
        self.task_name = task_name
        self.data = data
        self.create_time = time.ctime()
        self.is_done = False

    def __repr__(self):
        return "<Task(id - '%s', is_done - %s, user_id - '%s', task_name - '%s', create_time - '%s', data - '%s')>" % \
               (self.id, self.is_done, self.user_id, self.task_name, self.create_time, self.data)


class REPORT(Base):
    __tablename__ = 'Report'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    data = Column(String)

    def __init__(self, user_id, data):
        self.user_id = user_id
        self.data = data

    def __repr__(self):
        return "<Report('%s','%s')>" % \
               (self.user_id, self.data)

class DISPATCH(Base):
    __tablename__ = 'Dispatch'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)

    def __init__(self, user_id,):
        self.user_id = user_id

    def __repr__(self):
        return "<Dispatch('%s')>" % \
               (self.user_id)


class TOKEN(Base):
    __tablename__ = 'Token'
    id = Column(Integer, primary_key=True)
    burse = Column(String)
    name_token = Column(String)
    data = Column(String)

    def __init__(self, burse, name_token, data):
        self.burse = burse
        self.name_token = name_token
        self.data = data

    def __repr__(self):
        return "<TOKEN(burse - %s, name_token - %s, data - %s)>" % \
               (self.burse, self.name_token, self.data)

# # Метеданные доступны через класс Base
# metadata = Base.metadata
# print('Declarative. Metadata:', metadata)
#
# print(' ----------------- Работа с сессией ---------------------------------')

#                   Добавление новых объектов                      #
####################################################################

# Для сохранения объекта User, нужно добавить его к имеющейся сессии
# admin_user = User("vasia", "Vasiliy Pypkin", "vasia2000")
# log1 = Log("vasia", 'adada')
# log2 = Log("vasia", '3333')
# log3 = Log("vasia", '4444444')
# session.add(admin_user)
# session.add_all([log1, log2, log3])
#eventer = Event('ev1', 'new_event1')
#session.add(eventer)

# # Простой запрос
# q_user = session.query(User).filter_by(name="vasia").first()
# print('Simple query:', q_user)
# print(q_user.fullname)
# # Добавить сразу несколько записей
# session.add_all([User("kolia", "Cool Kolian[S.A.]","kolia$$$"),
#                  User("zina", "Zina Korzina", "zk18")])

# Сессия "знает" об изменениях пользователя
#session.commit()
#
#print('User ID after commit:', admin_user.user_id)
#q_user = session.query(Log).filter_by(name="vasia").all()
#print(q_user)

# ev = session.query(Event).all()
# print(ev)
# session.delete(ev[-1])
# session.commit()
# ev = session.query(Event).all()
# print(ev)

if __name__ == '__main__':
    data_base_path = "TRADE_DATA_BASE.db"
    engine = create_engine('sqlite:///%s' % data_base_path, echo=False)
    create_bd(engine)
    Session = sessionmaker(bind=engine)

    # Класс Session будет создавать Session-объекты, которые привязаны к базе данных
    session = Session()



    # t = session.query(Task).filter_by(is_done=False).all()
    # print(t)
    print('___')
    # arch = ARCHIVE('2', '2', '2', '2', '2', '2')
    # session.add(arch)
    # session.commit()
    arc1 = session.query(ARCHIVE).all()
    for arch in arc1:
        print(arch.id)
        session.delete(arch)
    session.commit()


    # admin_user = TOKEN("EXMO44", "bot", "data-[1][2]")
    # admin_user2 = TOKEN("EXMO555", "bot", "data-[1][2]")
    #
    # session.add(admin_user)
    # session.add(admin_user2)
    # session.commit()
    #
    # query = session.query(TOKEN).all()
    # for i in query:
    #     print(i.id, i.burse)
    #
    # q = session.query(Task).all()
    # for i in q:
    #     print(i.id, i.user_id)