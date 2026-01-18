import akshare as ak, json, datetime, jinja2

# 1. 用 akshare 拉当日行情
df = ak.stock_zh_a_hist(symbol="600900", period="daily", adjust="")
row = df.iloc[-1]               # 最新一行
price = round(row['收盘'], 2)
date  = row['日期'].strftime('%Y-%m-%d')

# 2. 写 json 供前端（可选）
with open('price.json','w',encoding='utf-8') as f:
    json.dump({'date':date, 'price':price}, f, ensure_ascii=False)

# 3. 生成极简 html
html = jinja2.Template('''
<!doctype html><meta charset="utf-8">
<title>长江电力每日行情</title>
<h1>长江电力（600900）</h1>
<p>日期：{{date}}  收盘价：¥{{price}}</p>
''').render(date=date, price=price)
with open('index.html','w',encoding='utf-8') as f: f.write(html)