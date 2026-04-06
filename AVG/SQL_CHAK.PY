import pymysql
import json

conn = pymysql.connect(host='10.32.72.48', port=3306, user='root', password='test', database='amp', charset='utf8mb4')
cursor = conn.cursor(pymysql.cursors.DictCursor)

data = {}
cursor.execute("SELECT * FROM location")
data['location'] = cursor.fetchall()
cursor.execute("SELECT * FROM node")
data['node'] = cursor.fetchall()
cursor.execute("SELECT * FROM hostlocation")
data['hostlocation'] = cursor.fetchall()
cursor.execute("SELECT * FROM bufferlocation")
data['bufferlocation'] = cursor.fetchall()
cursor.close()
conn.close()

f = open('amp_map_data.json', 'w', encoding='utf-8')
json.dump(data, f, ensure_ascii=False, default=str)
f.close()

print('location:', len(data['location']))
print('node:', len(data['node']))
print('hostlocation:', len(data['hostlocation']))
print('bufferlocation:', len(data['bufferlocation']))
print('amp_map_data.json 저장 완료')
