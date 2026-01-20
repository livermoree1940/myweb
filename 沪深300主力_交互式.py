import requests
import pandas as pd
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# 配置代理（根据你的环境 7897 端口）
proxies = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}
headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://gushitong.baidu.com/"}

def get_baidu_kline(code, is_futures=True):
    """从百度接口获取K线数据"""
    f_type = "true" if is_futures else "false"
    url = f"https://finance.pae.baidu.com/selfselect/getstockquotation?all=1&code={code}&isIndex={not is_futures}&isBk=false&isBlock=false&isFutures={f_type}&isStock=false&newFormat=1&ktype=1&market_type=ab&group=quotation_futures_kline&finClientType=pc"
    
    response = requests.get(url, headers=headers, proxies=proxies)
    res_json = response.json()
    raw_str = res_json['Result']['newMarketData']['marketData']
    keys = res_json['Result']['newMarketData']['keys']
    
    rows = [line.split(',') for line in raw_str.split(';') if line]
    df = pd.DataFrame(rows, columns=keys)
    df['time'] = pd.to_datetime(df['time'])
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    
    return df[['time', 'close']]

# --- 第一步：抓取数据 ---
print("正在抓取沪深300现货数据...")
df_spot = get_baidu_kline("000300", is_futures=False) # 现货
print("正在抓取沪深300期货(IF888)数据...")
df_future = get_baidu_kline("IF888", is_futures=True) # 期货

# --- 第二步：合并数据并计算基差 ---
# 使用 merge 确保日期完全对齐
df_basis = pd.merge(df_future, df_spot, on='time', suffixes=('_fut', '_spot'))
# 计算基差：期货 - 现货 (Basis)
df_basis['basis'] = df_basis['close_fut'] - df_basis['close_spot']

# --- 第三步：计算技术指标 ---
# 60日均线
df_basis['ma60'] = df_basis['basis'].rolling(window=60).mean()
# 布林带 (20日周期)
df_basis['mid'] = df_basis['basis'].rolling(window=20).mean()
df_basis['std'] = df_basis['basis'].rolling(window=20).std()
df_basis['upper'] = df_basis['mid'] + 2 * df_basis['std']
df_basis['lower'] = df_basis['mid'] - 2 * df_basis['std']

# --- 第四步：创建交互式图表 ---# 创建图表
fig = go.Figure()

# 设置图表标题和布局
fig.update_layout(
    title='沪深300股指期货基差分析 (含MA60及布林带) - 交互式图表',
    xaxis_title='时间',
    yaxis_title='基差',
    width=1200,
    height=800,
    template='plotly_white',
    hovermode='x unified'
)

# 绘制基差曲线（主曲线）
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

# 绘制布林带中轨
fig.add_trace(go.Scatter(
    x=df_basis['time'],
    y=df_basis['mid'],
    name='布林带中轨',
    line=dict(color='#7FB069', width=1, dash='dash'),
    opacity=0.6
))

# 绘制布林带上轨
fig.add_trace(go.Scatter(
    x=df_basis['time'],
    y=df_basis['upper'],
    name='布林带上轨',
    line=dict(color='#7FB069', width=1, dash='dash'),
    opacity=0.6,
    fill=None
))

# 绘制布林带下轨，并填充上轨和下轨之间的区域
fig.add_trace(go.Scatter(
    x=df_basis['time'],
    y=df_basis['lower'],
    name='布林带下轨',
    line=dict(color='#d0001f', width=1, dash='dash'),
    opacity=0.6,
    fill='tonexty',  # 填充到上一个轨迹（上轨）下方
    fillcolor='rgba(127, 176, 105, 0.1)'
))

# --- 标记突破布林带上轨的线段 ---
# 找出基差 > 上轨的所有点
breakout_up_points = df_basis['basis'] > df_basis['upper']

# 将突破上轨的点分割成连续的线段
breakout_up_segments = []
current_segment = []

for i in range(len(breakout_up_points)):
    if breakout_up_points.iloc[i]:  # 如果当前点是突破上轨点
        current_segment.append(i)
    else:  # 如果不是突破点且当前有未完成的线段
        if current_segment:
            breakout_up_segments.append(current_segment)
            current_segment = []

# 处理最后一个线段
if current_segment:
    breakout_up_segments.append(current_segment)

# 为突破上轨线段分配颜色（冷色调）
colors_up = ['#33FF57', '#3357FF', '#4ECDC4', '#45B7D1', '#96CEB4']

# 绘制突破上轨线段（更粗的线条）
for idx, segment in enumerate(breakout_up_segments):
    if len(segment) > 1:  # 只绘制长度大于1的线段
        color = colors_up[idx % len(colors_up)]  # 循环使用颜色
        start_idx = segment[0]
        end_idx = segment[-1] + 1  # +1 确保线段是连续的
        fig.add_trace(go.Scatter(
            x=df_basis['time'].iloc[start_idx:end_idx],
            y=df_basis['basis'].iloc[start_idx:end_idx],
            name=f'突破上轨 #{idx+1}',
            line=dict(color=color, width=3),
            opacity=0.9,
            visible='legendonly' if idx > 0 else True  # 只默认显示第一个突破段
        ))

# --- 标记突破布林带下轨的线段 ---
# 找出基差 < 下轨的所有点
breakout_down_points = df_basis['basis'] < df_basis['lower']

# 将突破下轨的点分割成连续的线段
breakout_down_segments = []
current_segment = []

for i in range(len(breakout_down_points)):
    if breakout_down_points.iloc[i]:  # 如果当前点是突破下轨点
        current_segment.append(i)
    else:  # 如果不是突破点且当前有未完成的线段
        if current_segment:
            breakout_down_segments.append(current_segment)
            current_segment = []

# 处理最后一个线段
if current_segment:
    breakout_down_segments.append(current_segment)

# 为突破下轨线段分配颜色（暖色调）
colors_down = ['#FF5733', '#FFC300', '#FF6B6B', '#FF8E53', '#FFB74D']

# 绘制突破下轨线段（更粗的线条）
for idx, segment in enumerate(breakout_down_segments):
    if len(segment) > 1:  # 只绘制长度大于1的线段
        color = colors_down[idx % len(colors_down)]  # 循环使用颜色
        start_idx = segment[0]
        end_idx = segment[-1] + 1  # +1 确保线段是连续的
        fig.add_trace(go.Scatter(
            x=df_basis['time'].iloc[start_idx:end_idx],
            y=df_basis['basis'].iloc[start_idx:end_idx],
            name=f'突破下轨 #{idx+1}',
            line=dict(color=color, width=3),
            opacity=0.9,
            visible='legendonly' if idx > 0 else True  # 只默认显示第一个突破段
        ))

# 添加水平线：基差 = 0
fig.add_hline(
    y=0, 
    line=dict(color='black', width=1, dash='solid'),
    name='基差=0线'
)

# 配置图表交互功能
fig.update_xaxes(
    rangeslider_visible=True,  # 底部范围选择器
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

# 保存为HTML文件
fig.write_html("hs300_basis_interactive.html", 
               include_plotlyjs='cdn',  # 使用CDN减小文件大小
               full_html=True,
               auto_open=False)

# 保存为可嵌入的HTML片段
fig.write_html("hs300_basis_embed.html", 
               include_plotlyjs='cdn',
               full_html=False)

# 保存数据到本地
df_basis.to_csv("hs300_basis_data.csv", index=False, encoding='utf-8-sig')

print("\n分析完成！")
print("生成的文件：")
print("- hs300_basis_interactive.html: 完整的交互式HTML图表")
print("- hs300_basis_embed.html: 可嵌入的HTML片段")
print("- hs300_basis_data.csv: 基差数据CSV文件")
print("\n可以直接在浏览器中打开 hs300_basis_interactive.html 查看交互式图表")
print("如需嵌入到现有网页，可以将 hs300_basis_embed.html 的内容复制到您的HTML文件中")
