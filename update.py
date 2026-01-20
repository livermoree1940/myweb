import akshare as ak, json, datetime, jinja2, os, glob

# 1. 用 akshare 拉当日行情
try:
    df = ak.stock_zh_a_hist(symbol="600900", period="daily", adjust="")
    row = df.iloc[-1]               # 最新一行
    price = round(row['收盘'], 2)
    date  = row['日期'].strftime('%Y-%m-%d')
except Exception as e:
    print(f"❌ 获取行情失败：{e}，使用默认数据")
    price = 26.80
    date = datetime.datetime.now().strftime('%Y-%m-%d')

# 2. 写 json 供前端（可选）
with open('price.json','w',encoding='utf-8') as f:
    json.dump({'date':date, 'price':price}, f, ensure_ascii=False)

# 3. 查找最新的红利ETF PNG图片
png_files = glob.glob('红利ETF_三种策略_梯度买卖_*_*.png')
# 按修改时间排序，最新的在前面
png_files.sort(key=os.path.getmtime, reverse=True)
latest_png = png_files[0] if png_files else None

# 尝试读取策略HTML片段
strategy_html = ""
if os.path.exists('strategy_fragment.html'):
    with open('strategy_fragment.html', 'r', encoding='utf-8') as f:
        strategy_html = f.read()

# 4. 生成包含图片的HTML
html = jinja2.Template('''
<!doctype html><meta charset="utf-8">
<title>长江电力每日行情</title>
<h1>长江电力（600900）</h1>
<p>日期：{{date}}  收盘价：¥{{price}}</p>
{% if strategy_html %}
    {{ strategy_html }}
{% elif latest_png %}
<h2>红利ETF策略分析</h2>
<img src="{{latest_png}}" alt="红利ETF策略分析图" style="max-width: 100%; height: auto;">
{% endif %}
''').render(date=date, price=price, latest_png=latest_png, strategy_html=strategy_html)
with open('index.html','w',encoding='utf-8') as f: f.write(html)