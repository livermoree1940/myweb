import akshare as ak, json, datetime, jinja2, requests, pandas as pd, numpy as np
from plotly.graph_objects import Scatter
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# 创建模拟的沪深300基差数据
def create_mock_hs300_data():
    # 创建模拟时间序列
    dates = pd.date_range(start='2024-01-01', end=datetime.datetime.now(), freq='D')
    
    # 创建模拟数据
    np.random.seed(42)
    spot_prices = 3000 + np.cumsum(np.random.normal(0, 10, len(dates)))
    future_prices = spot_prices + np.random.normal(5, 15, len(dates))
    
    # 创建DataFrame
    df_future = pd.DataFrame({'time': dates, 'close_fut': future_prices})
    df_spot = pd.DataFrame({'time': dates, 'close_spot': spot_prices})
    
    # 合并数据并计算基差
    df_basis = pd.merge(df_future, df_spot, on='time')
    df_basis['basis'] = df_basis['close_fut'] - df_basis['close_spot']
    
    # 计算技术指标
    df_basis['ma60'] = df_basis['basis'].rolling(window=60, min_periods=1).mean()
    df_basis['mid'] = df_basis['basis'].rolling(window=20, min_periods=1).mean()
    df_basis['std'] = df_basis['basis'].rolling(window=20, min_periods=1).std().fillna(1)
    df_basis['upper'] = df_basis['mid'] + 2 * df_basis['std']
    df_basis['lower'] = df_basis['mid'] - 2 * df_basis['std']
    
    return df_basis

# 创建沪深300基差图表
def create_hs300_chart(df_basis):
    try:
        if df_basis is None or len(df_basis) < 20:
            return False
        
        # 创建图表
        fig = go.Figure()
        
        # 设置图表标题和布局
        fig.update_layout(
            title='沪深300股指期货基差分析 (含MA60及布林带)',
            xaxis_title='时间',
            yaxis_title='基差',
            width=1000,
            height=600,
            template='plotly_white',
            hovermode='x unified'
        )
        
        # 绘制基差曲线
        fig.add_trace(go.Scatter(
            x=df_basis['time'],
            y=df_basis['basis'],
            name='沪深300基差 (IF-现货)',
            line=dict(color='#5386E4', width=1.5),
            opacity=0.9
        ))
        
        # 绘制60日均线
        fig.add_trace(go.Scatter(
            x=df_basis['time'],
            y=df_basis['ma60'],
            name='基差 60日均线',
            line=dict(color='#F49E4C', width=2, dash='solid'),
            opacity=0.8
        ))
        
        # 绘制布林带
        fig.add_trace(go.Scatter(
            x=df_basis['time'],
            y=df_basis['mid'],
            name='布林带中轨',
            line=dict(color='#7FB069', width=1, dash='dash'),
            opacity=0.6
        ))
        
        fig.add_trace(go.Scatter(
            x=df_basis['time'],
            y=df_basis['upper'],
            name='布林带上轨',
            line=dict(color='#7FB069', width=1, dash='dash'),
            opacity=0.6,
            fill=None
        ))
        
        fig.add_trace(go.Scatter(
            x=df_basis['time'],
            y=df_basis['lower'],
            name='布林带下轨',
            line=dict(color='#d0001f', width=1, dash='dash'),
            opacity=0.6,
            fill='tonexty',
            fillcolor='rgba(127, 176, 105, 0.1)'
        ))
        
        # 添加水平线：基差 = 0
        fig.add_hline(
            y=0, 
            line=dict(color='black', width=1, dash='solid'),
            name='基差=0线'
        )
        
        # 配置图表交互功能
        fig.update_xaxes(
            rangeslider_visible=True,
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1月", step="month", stepmode="backward"),
                    dict(count=3, label="3月", step="month", stepmode="backward"),
                    dict(count=6, label="6月", step="month", stepmode="backward"),
                    dict(count=1, label="1年", step="year", stepmode="backward"),
                    dict(step="all")
                ])
            )
        )
        
        # 保存为可嵌入的HTML片段
        fig.write_html("hs300_basis_embed.html", 
                       include_plotlyjs='cdn',
                       full_html=False)
        
        return True
    except Exception as e:
        print(f"创建沪深300图表时出错: {e}")
        return False

# 定义获取股票/指数数据的函数（使用模拟数据）
def get_stock_data(symbol, name):
    return {
        'name': name,
        'symbol': symbol,
        'price': 23.56,
        'prev_price': 23.20,
        'change': 0.36,
        'change_pct': 1.55
    }

# 定义获取指数数据的函数（使用模拟数据）
def get_index_data(symbol, name):
    mock_data = {
        "000001": (3050.25, 3020.80),
        "399006": (1850.75, 1880.30),
        "000688": (950.30, 945.20),
        "000985": (4750.80, 4720.50)
    }
    
    price, prev_price = mock_data[symbol]
    change = price - prev_price
    change_pct = round((change / prev_price) * 100, 2)
    
    return {
        'name': name,
        'symbol': symbol,
        'price': price,
        'prev_price': prev_price,
        'change': change,
        'change_pct': change_pct
    }

# 测试整个集成过程
def test_integration():
    print("=== 测试沪深300基差图表集成 ===")
    
    # 1. 获取股票数据（模拟）
    stock_data = get_stock_data("600900", "长江电力")
    print(f"✓ 获取长江电力数据成功: {stock_data['price']}")
    
    # 2. 获取指数数据（模拟）
    indices = [
        get_index_data("000001", "上证指数"),
        get_index_data("399006", "创业板指"),
        get_index_data("000688", "科创50"),
        get_index_data("000985", "中证全指")
    ]
    print("✓ 获取市场指数数据成功")
    
    # 3. 获取日期
    date = datetime.datetime.now().strftime('%Y-%m-%d')
    
    # 4. 获取沪深300基差数据并创建图表（使用模拟数据）
    print("正在创建模拟的沪深300基差数据...")
    df_hs300 = create_mock_hs300_data()
    print(f"✓ 创建沪深300基差数据成功: {len(df_hs300)} 条记录")
    
    print("正在创建沪深300基差图表...")
    has_hs300_chart = create_hs300_chart(df_hs300)
    if has_hs300_chart:
        print("✓ 沪深300基差图表创建成功！")
    else:
        print("✗ 沪深300基差图表创建失败！")
        return False
    
    # 5. 读取沪深300基差图表的HTML片段
    if has_hs300_chart:
        try:
            with open('hs300_basis_embed.html', 'r', encoding='utf-8') as f:
                hs300_chart_html = f.read()
            print("✓ 读取沪深300图表HTML片段成功")
        except Exception as e:
            print(f"✗ 读取沪深300图表HTML时出错: {e}")
            return False
    else:
        hs300_chart_html = ""
    
    # 6. 生成完整的HTML页面
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
            max-width: 1000px;
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
            border-bottom: 1px solid #eee;
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
        .chart-section {
            padding: 25px;
            border-bottom: 1px solid #eee;
        }
        .chart-section h2 {
            font-size: 20px;
            margin-bottom: 20px;
            color: #2c3e50;
        }
        .chart-container {
            width: 100%;
            overflow-x: auto;
            background: #f8f9fa;
            padding: 10px;
            border-radius: 8px;
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
        
        {% if has_hs300_chart %}
        <div class="chart-section">
            <h2>沪深300股指期货基差分析</h2>
            <div class="chart-container">
                {{ hs300_chart_html | safe }}
            </div>
        </div>
        {% endif %}
        
        <div class="footer">
            数据来源：akshare | 更新时间：{{date}}
        </div>
    </div>
</body>
</html>
''').render(date=date, stock=stock_data, indices=indices, has_hs300_chart=has_hs300_chart, hs300_chart_html=hs300_chart_html)
    
    # 7. 保存HTML页面
    with open('test_index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("✓ 生成集成后的HTML页面成功")
    
    print("\n=== 测试完成 ===")
    print("生成的文件：")
    print("- test_index.html: 集成了沪深300基差图表的股票行情看板")
    print("- hs300_basis_embed.html: 沪深300基差图表的HTML片段")
    print("\n可以在浏览器中打开 test_index.html 查看集成效果")
    
    return True

if __name__ == "__main__":
    test_integration()
