import akshare as ak, json, datetime, jinja2, requests, pandas as pd, numpy as np, os, glob
from plotly.graph_objects import Scatter
from plotly.subplots import make_subplots
import plotly.graph_objects as go

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

# 定义获取股票/指数数据的函数
def get_stock_data(symbol, name):
    try:
        df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="")
        latest = df.iloc[-1]       # 最新数据
        previous = df.iloc[-2]     # 昨日数据
        
        price = round(latest['收盘'], 2)
        prev_price = round(previous['收盘'], 2)
        change = round(price - prev_price, 2)
        change_pct = round((change / prev_price) * 100, 2)
        
        return {
            'name': name,
            'symbol': symbol,
            'price': price,
            'prev_price': prev_price,
            'change': change,
            'change_pct': change_pct
        }
    except Exception as e:
        print(f"❌ 获取{name}({symbol})数据失败：{e}，使用默认数据")
        return {
            'name': name,
            'symbol': symbol,
            'price': 0,
            'prev_price': 0,
            'change': 0,
            'change_pct': 0
        }

# 定义获取指数数据的函数
def get_index_data(symbol, name):
    try:
        # 尝试使用东方财富网接口获取指数数据
        print(f"📈 尝试使用东方财富网接口获取{name}({symbol})数据...")
        # 根据指数类型选择合适的symbol参数
        if symbol.startswith('000'):
            df_em = ak.stock_zh_index_spot_em(symbol="上证系列指数")
        elif symbol.startswith('399'):
            df_em = ak.stock_zh_index_spot_em(symbol="深证系列指数")
        else:
            df_em = ak.stock_zh_index_spot_em(symbol="中证系列指数")
        
        # 查找指定指数的数据
        index_data = df_em[df_em['代码'] == symbol]
        if not index_data.empty:
            row = index_data.iloc[0]
            price = round(float(row['最新价']), 2)
            prev_price = round(float(row['昨收']), 2)
            change = round(float(row['涨跌额']), 2)
            change_pct = round(float(row['涨跌幅']), 2)
            
            print(f"✅ 成功从东方财富网获取{name}({symbol})数据")
            return {
                'name': name,
                'symbol': symbol,
                'price': price,
                'prev_price': prev_price,
                'change': change,
                'change_pct': change_pct
            }
        else:
            print(f"⚠️ 东方财富网接口未找到{name}({symbol})数据，尝试使用新浪财经接口...")
            # 东方财富网接口未找到数据，尝试使用新浪财经接口
            df_sina = ak.stock_zh_index_spot_sina()
            # 为新浪财经接口准备代码格式（添加sh或sz前缀）
            sina_symbol = f"sh{symbol}" if symbol.startswith('000') else f"sz{symbol}"
            index_data_sina = df_sina[df_sina['代码'] == sina_symbol]
            
            if not index_data_sina.empty:
                row_sina = index_data_sina.iloc[0]
                price = round(float(row_sina['最新价']), 2)
                prev_price = round(float(row_sina['昨收']), 2)
                change = round(float(row_sina['涨跌额']), 2)
                change_pct = round(float(row_sina['涨跌幅']), 2)
                
                print(f"✅ 成功从新浪财经获取{name}({symbol})数据")
                return {
                    'name': name,
                    'symbol': symbol,
                    'price': price,
                    'prev_price': prev_price,
                    'change': change,
                    'change_pct': change_pct
                }
            else:
                print(f"⚠️ 新浪财经接口也未找到{name}({symbol})数据，尝试使用历史数据接口...")
                # 新浪财经接口也未找到数据，尝试使用历史数据接口
                df_daily = ak.stock_zh_index_daily(symbol=symbol)
                # 检查数据列名是否存在
                if 'date' in df_daily.columns:
                    latest = df_daily.iloc[-1]       # 最新数据
                    previous = df_daily.iloc[-2]     # 昨日数据
                    
                    price = round(latest['close'], 2)
                    prev_price = round(previous['close'], 2)
                else:
                    # 处理接口返回数据格式变化的情况
                    latest = df_daily.iloc[-1]       # 最新数据
                    previous = df_daily.iloc[-2]     # 昨日数据
                    
                    price = round(latest[df_daily.columns[3]], 2)  # 假设close是第4列
                    prev_price = round(previous[df_daily.columns[3]], 2)
                
                change = round(price - prev_price, 2)
                change_pct = round((change / prev_price) * 100, 2)
                
                print(f"✅ 成功从历史数据接口获取{name}({symbol})数据")
                return {
                    'name': name,
                    'symbol': symbol,
                    'price': price,
                    'prev_price': prev_price,
                    'change': change,
                    'change_pct': change_pct
                }
    except Exception as e:
        print(f"❌ 获取{name}({symbol})数据失败：{e}，使用默认数据")
        # 使用模拟数据
        mock_data = {
            '000001': {'price': 3050.25, 'prev_price': 3020.8, 'change': 29.45, 'change_pct': 0.97},
            '399006': {'price': 1850.75, 'prev_price': 1880.3, 'change': -29.55, 'change_pct': -1.57},
            '000688': {'price': 950.3, 'prev_price': 945.2, 'change': 5.1, 'change_pct': 0.54},
            '000985': {'price': 4750.8, 'prev_price': 4720.5, 'change': 30.3, 'change_pct': 0.64}
        }
        
        if symbol in mock_data:
            data = mock_data[symbol]
            return {
                'name': name,
                'symbol': symbol,
                'price': data['price'],
                'prev_price': data['prev_price'],
                'change': data['change'],
                'change_pct': data['change_pct']
            }
        else:
            return {
                'name': name,
                'symbol': symbol,
                'price': 0,
                'prev_price': 0,
                'change': 0,
                'change_pct': 0
            }

# 定义获取指数现货和期货数据的通用函数
def get_index_futures_data(spot_code, future_code, index_name):
    try:
        # 移除代理设置，直接连接
        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://gushitong.baidu.com/"}
        
        def get_baidu_kline(code, is_futures=True):
            """从百度接口获取K线数据"""
            f_type = "true" if is_futures else "false"
            url = f"https://finance.pae.baidu.com/selfselect/getstockquotation?all=1&code={code}&isIndex={not is_futures}&isBk=false&isBlock=false&isFutures={f_type}&isStock=false&newFormat=1&ktype=1&market_type=ab&group=quotation_futures_kline&finClientType=pc"
            
            # 移除proxies参数，直接连接
            response = requests.get(url, headers=headers, timeout=10)
            res_json = response.json()
            raw_str = res_json['Result']['newMarketData']['marketData']
            keys = res_json['Result']['newMarketData']['keys']
            
            rows = [line.split(',') for line in raw_str.split(';') if line]
            df = pd.DataFrame(rows, columns=keys)
            df['time'] = pd.to_datetime(df['time'])
            df['close'] = pd.to_numeric(df['close'], errors='coerce')
            
            return df[['time', 'close']]
        
        # 获取现货和期货数据
        df_spot = get_baidu_kline(spot_code, is_futures=False)
        df_future = get_baidu_kline(future_code, is_futures=True)
        
        # 合并数据并计算基差
        df_basis = pd.merge(df_future, df_spot, on='time', suffixes=('_fut', '_spot'))
        df_basis['basis'] = df_basis['close_fut'] - df_basis['close_spot']
        
        # 计算技术指标
        df_basis['ma60'] = df_basis['basis'].rolling(window=60).mean()
        df_basis['mid'] = df_basis['basis'].rolling(window=20).mean()
        df_basis['std'] = df_basis['basis'].rolling(window=20).std()
        df_basis['upper'] = df_basis['mid'] + 2 * df_basis['std']
        df_basis['lower'] = df_basis['mid'] - 2 * df_basis['std']
        
        return df_basis
    except Exception as e:
        print(f"获取{index_name}数据时出错: {e}")
        return None

# 定义获取沪深300现货和期货数据的函数
def get_hs300_data():
    return get_index_futures_data("000300", "IF888", "沪深300")

# 定义获取中证1000现货和期货数据的函数
def get_zz1000_data():
    return get_index_futures_data("000852", "IC888", "中证1000")

# 定义创建基差交互式图表的通用函数
def create_basis_chart(df_basis, index_name, output_file):
    try:
        if df_basis is None or len(df_basis) < 20:
            return None
        
        # 创建图表
        fig = go.Figure()
        
        # 设置图表标题和布局
        fig.update_layout(
            title=f'{index_name}股指期货基差分析 (含MA60及布林带)',
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
            name=f'{index_name}基差',
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
        fig.write_html(output_file, 
                       include_plotlyjs='cdn',
                       full_html=False)
        
        return True
    except Exception as e:
        print(f"创建{index_name}图表时出错: {e}")
        return False

# 定义创建沪深300基差交互式图表的函数
def create_hs300_chart(df_basis):
    return create_basis_chart(df_basis, "沪深300", "hs300_basis_embed.html")

# 定义创建中证1000基差交互式图表的函数
def create_zz1000_chart(df_basis):
    return create_basis_chart(df_basis, "中证1000", "zz1000_basis_embed.html")

# 1. 获取长江电力数据
stock_data = get_stock_data("600900", "长江电力")

# 2. 获取指数数据
indices = [
    get_index_data("000001", "上证指数"),
    get_index_data("399006", "创业板指"),
    get_index_data("000688", "科创50"),
    get_index_data("000985", "中证全指")
]

# 3. 获取日期
date = datetime.datetime.now().strftime('%Y-%m-%d')

# 4. 获取沪深300基差数据并创建图表
has_hs300_chart = False
try:
    print("正在获取沪深300基差数据...")
    df_hs300 = get_hs300_data()
    if df_hs300 is not None:
        print("正在创建沪深300基差图表...")
        has_hs300_chart = create_hs300_chart(df_hs300)
        if has_hs300_chart:
            print("沪深300基差图表创建成功！")
        else:
            print("沪深300基差图表创建失败！")
    else:
        print("未能获取沪深300数据！")
except Exception as e:
    print(f"处理沪深300数据时出错: {e}")
    has_hs300_chart = False

# 5. 获取中证1000基差数据并创建图表
has_zz1000_chart = False
try:
    print("正在获取中证1000基差数据...")
    df_zz1000 = get_zz1000_data()
    if df_zz1000 is not None:
        print("正在创建中证1000基差图表...")
        has_zz1000_chart = create_zz1000_chart(df_zz1000)
        if has_zz1000_chart:
            print("中证1000基差图表创建成功！")
        else:
            print("中证1000基差图表创建失败！")
    else:
        print("未能获取中证1000数据！")
except Exception as e:
    print(f"处理中证1000数据时出错: {e}")
    has_zz1000_chart = False

# 6. 写 json 供前端（可选）
data = {
    'date': date,
    'stock': stock_data,
    'indices': indices,
    'has_hs300_chart': has_hs300_chart,
    'has_zz1000_chart': has_zz1000_chart
}
with open('price.json','w',encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False)

# 6. 获取红利ETF策略相关数据
# 查找最新的红利ETF PNG图片
png_files = glob.glob('红利ETF_三种策略_梯度买卖_*_*.png')
# 按修改时间排序，最新的在前面
png_files.sort(key=os.path.getmtime, reverse=True)
latest_png = png_files[0] if png_files else None

# 尝试读取策略HTML片段
strategy_html = ""
if os.path.exists('strategy_fragment.html'):
    with open('strategy_fragment.html', 'r', encoding='utf-8') as f:
        strategy_html = f.read()

# 7. 生成 html
# 读取沪深300基差图表的HTML片段
if has_hs300_chart:
    try:
        with open('hs300_basis_embed.html', 'r', encoding='utf-8') as f:
            hs300_chart_html = f.read()
    except Exception as e:
        print(f"读取沪深300图表HTML时出错: {e}")
        hs300_chart_html = ""
        has_hs300_chart = False
else:
    hs300_chart_html = ""

# 读取中证1000基差图表的HTML片段
if has_zz1000_chart:
    try:
        with open('zz1000_basis_embed.html', 'r', encoding='utf-8') as f:
            zz1000_chart_html = f.read()
    except Exception as e:
        print(f"读取中证1000图表HTML时出错: {e}")
        zz1000_chart_html = ""
        has_zz1000_chart = False
else:
    zz1000_chart_html = ""

html = jinja2.Template('''
<!doctype html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>股票行情与量化策略仪表盘</title>
    <style>
        :root {
            --primary-color: #2c3e50;
            --bg-color: #f4f7f9;
            --card-bg: #ffffff;
            --text-main: #333;
            --text-muted: #666;
            --red: #e74c3c;
            --green: #27ae60;
            --blue: #3498db;
            --shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            margin: 0;
            padding: 20px;
            line-height: 1.6;
        }

        .container { max-width: 1000px; margin: 0 auto; }
        
        header { 
            text-align: center; 
            margin-bottom: 30px; 
            padding: 20px 0;
            border-bottom: 2px solid #ddd;
        }
        
        h1 { margin: 0; color: var(--primary-color); font-size: 24px; }
        .last-update { color: var(--text-muted); font-size: 14px; margin-top: 5px; }

        /* 核心卡片样式 */
        .card {
            background: var(--card-bg);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: var(--shadow);
        }

        .stock-card {
            padding: 25px;
            border-bottom: 1px solid #eee;
        }

        .stock-card h2 {
            font-size: 20px;
            margin-bottom: 15px;
            color: var(--primary-color);
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
            color: var(--primary-color);
        }

        .stock-change {
            font-size: 18px;
            font-weight: bold;
        }

        .change-positive {
            color: var(--green);
        }

        .change-negative {
            color: var(--red);
        }

        .indices-section {
            padding: 25px;
            border-bottom: 1px solid #eee;
        }

        .indices-section h2 {
            font-size: 20px;
            margin-bottom: 20px;
            color: var(--primary-color);
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
            border-left: 4px solid var(--blue);
        }

        .index-name {
            font-size: 14px;
            margin-bottom: 8px;
            color: var(--text-muted);
        }

        .index-price {
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 5px;
            color: var(--primary-color);
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
            color: var(--primary-color);
        }

        .chart-container {
            width: 100%;
            overflow-x: auto;
            background: #f8f9fa;
            padding: 10px;
            border-radius: 8px;
        }

        /* 策略卡片样式 */
        .strategy-card { }
        .card-header { font-size: 20px; font-weight: bold; margin-bottom: 20px; color: var(--primary-color); display: flex; align-items: center; }
        .card-header .icon { margin-right: 10px; }

        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }

        .summary-item {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            border: 1px solid #eee;
        }
        
        .summary-item .label { font-size: 13px; color: var(--text-muted); margin-bottom: 5px; }
        .summary-item .value { font-size: 18px; font-weight: bold; }

        .sub-card { margin-top: 25px; border-top: 1px dashed #eee; padding-top: 20px; }
        .sub-header { font-size: 16px; font-weight: bold; margin-bottom: 15px; color: var(--text-muted); }

        .strategy-img { 
            max-width: 100%; 
            height: auto; 
            border-radius: 8px; 
            margin: 20px auto; 
            display: block;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }

        /* 表格样式 */
        .table-container { overflow-x: auto; }
        .data-table { width: 100%; border-collapse: collapse; font-size: 14px; }
        .data-table th { background: #f8f9fa; color: var(--text-muted); text-align: left; padding: 12px 8px; border-bottom: 2px solid #eee; }
        .data-table td { padding: 10px 8px; border-bottom: 1px solid #eee; }
        .data-table tr:hover { background-color: #fafafa; }

        /* 标签样式 */
        .badge {
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 500;
        }
        .status-red { background: #fdeaea; color: var(--red); }
        .status-green { background: #e6f4ea; color: var(--green); }
        .status-yellow { background: #fff8e1; color: #f39c12; }
        .status-blue { background: #e8f4fd; color: var(--blue); }

        .text-red { color: var(--red); }
        .text-green { color: var(--green); }
        
        .footer-tip { font-size: 12px; color: #999; text-align: center; margin-top: 20px; }

        .footer {
            padding: 15px 25px;
            background: #f8f9fa;
            text-align: center;
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 20px;
        }

        @media (max-width: 600px) {
            body { padding: 10px; }
            .price-value { font-size: 24px; }
            .summary-grid { grid-template-columns: 1fr 1fr; }
            .indices-grid { grid-template-columns: 1fr 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>股票行情与量化策略仪表盘</h1>
            <div class="last-update">最后更新时间：{{date}}</div>
        </header>
        
        <div class="card">
            <h2>{{stock.name}}（{{stock.symbol}}）</h2>
            <div class="stock-info">
                <div class="stock-price">¥{{stock.price}}</div>
                <div class="stock-change {% if stock.change >= 0 %}change-positive{% else %}change-negative{% endif %}">
                    {% if stock.change >= 0 %}+{% endif %}{{stock.change}} ({% if stock.change >= 0 %}+{% endif %}{{stock.change_pct}}%)
                </div>
            </div>
        </div>
        
        <div class="card">
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
        <div class="card">
            <h2>沪深300股指期货基差分析</h2>
            <div class="chart-container">
                {{ hs300_chart_html | safe }}
            </div>
        </div>
        {% endif %}
        
        {% if has_zz1000_chart %}
        <div class="card">
            <h2>中证1000股指期货基差分析</h2>
            <div class="chart-container">
                {{ zz1000_chart_html | safe }}
            </div>
        </div>
        {% endif %}
        
        <div class="card">
            {% if strategy_html %}
                {{ strategy_html }}
            {% else %}
                <div class="card-header">红利ETF 策略分析</div>
                {% if latest_png %}
                <img src="{{latest_png}}" alt="策略分析图" class="strategy-img">
                {% else %}
                <p style="text-align: center; color: var(--text-muted);">暂无策略分析图</p>
                {% endif %}
            {% endif %}
        </div>
        
        <div class="footer">
            数据来源：akshare | 更新时间：{{date}}
        </div>
    </div>
</body>
</html>
''').render(date=date, stock=stock_data, indices=indices, has_hs300_chart=has_hs300_chart, hs300_chart_html=hs300_chart_html, has_zz1000_chart=has_zz1000_chart, zz1000_chart_html=zz1000_chart_html, latest_png=latest_png, strategy_html=strategy_html)

with open('index.html','w',encoding='utf-8') as f:
    f.write(html)
