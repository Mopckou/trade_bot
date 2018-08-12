class ErrorMy(Exception):
    pass

class Enather(Exception):
    pass

try:
    raise Enather(u'Error')
except ErrorMy or Enather:
    print('da')