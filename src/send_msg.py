import json
txt = '0'
data = ['K-213', 'S-3231']
dat = json.dumps(data)

print(dat)

d = json.loads(dat)
print(d)