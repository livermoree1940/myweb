import json, datetime, jinja2

# 使用模拟数据进行测试
stock_data = {
    'name': '长江电力',
    'symbol': '600900',
    'price': 23.56,
    'prev_price': 23.20,
    'change': 0.36,
    'change_pct': 1.55
}

indices = [
    {
        'name': '上证指数',
        'symbol': '000001',
        'price': 3050.25,
        'prev_price': 3020.80,
        'change': 29.45,
        'change_pct': 0.97
    },
    {
        'name': '创业板指',
        'symbol': '399006',
        'price': 1850.75,
        'prev_price': 1880.30,
        'change': -29.55,
        'change_pct': -1.57
    },
    {
        'name': '科创50',
        'symbol': '000688',
        'price': 950.30,
        'prev_price': 945.20,
        'change': 5.10,
        'change_pct': 0.54
    },
    {
        'name': '中证全指',
        'symbol': '000985',
        'price': 4750.80,
        'prev_price': 4720.50,
        'change': 30.30,
        'change_pct': 0.64
    }
]

# 获取日期
date = datetime.datetime.now().strftime('%Y-%m-%d')

# 写 json 供前端（可选）
data = {
    'date': date,
    'stock': stock_data,
    'indices': indices
}
with open('price.json','w',encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False)

# 生成 html
html = jinja2.Template('''
<!doctype html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>股票行情看板</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: #2c3e50;
            color: white;
            padding: 20px;
            text-align: center;
        }
        .header h1 {
            font-size: 24px;
            margin-bottom: 5px;
        }
        .header .date {
            font-size: 14px;
            opacity: 0.8;
        }
        .stock-card {
            padding: 25px;
            border-bottom: 1px solid #eee;
        }
        .stock-card h2 {
            font-size: 20px;
            margin-bottom: 15px;
            color: #2c3e50;
        }
        .stock-info {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
        }
        .stock-price {
            font-size: 36px;
            font-weight: bold;
            color: #2c3e50;
        }
        .stock-change {
            font-size: 18px;
            font-weight: bold;
        }
        .change-positive {
            color: #27ae60;
        }
        .change-negative {
            color: #e74c3c;
        }
        .indices-section {
            padding: 25px;
        }
        .indices-section h2 {
            font-size: 20px;
            margin-bottom: 20px;
            color: #2c3e50;
        }
        .indices-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }
        .index-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #3498db;
        }
        .index-name {
            font-size: 14px;
            margin-bottom: 8px;
            color: #666;
        }
        .index-price {
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 5px;
            color: #2c3e50;
        }
        .index-change {
            font-size: 14px;
            font-weight: bold;
        }
        .footer {
            padding: 15px 25px;
            background: #f8f9fa;
            text-align: center;
            font-size: 12px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>股票行情看板</h1>
            <div class="date">更新日期：{{date}}</div>
        </div>
        
        <div class="stock-card">
            <h2>{{stock.name}}（{{stock.symbol}}）</h2>
            <div class="stock-info">
                <div class="stock-price">¥{{stock.price}}</div>
                <div class="stock-change {% if stock.change >= 0 %}change-positive{% else %}change-negative{% endif %}">
                    {% if stock.change >= 0 %}+{% endif %}{{stock.change}} ({% if stock.change >= 0 %}+{% endif %}{{stock.change_pct}}%)
                </div>
            </div>
        </div>
        
        <div class="indices-section">
            <h2>市场指数</h2>
            <div class="indices-grid">
                {% for index in indices %}
                <div class="index-card">
                    <div class="index-name">{{index.name}}（{{index.symbol}}）</div>
                    <div class="index-price">{{index.price}}</div>
                    <div class="index-change {% if index.change >= 0 %}change-positive{% else %}change-negative{% endif %}">
                        {% if index.change >= 0 %}+{% endif %}{{index.change}} ({% if index.change >= 0 %}+{% endif %}{{index.change_pct}}%)
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        
        <div class="footer">
            数据来源：akshare | 更新时间：{{date}}
        </div>
    </div>
</body>
</html>
''').render(date=date, stock=stock_data, indices=indices)

with open('index.html','w',encoding='utf-8') as f:
    f.write(html)

print("测试完成！已使用模拟数据生成index.html文件")