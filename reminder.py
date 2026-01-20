import akshare as ak
import pandas as pd
import warnings
import matplotlib.pyplot as plt
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.header import Header
import PIL.Image
import requests
from bs4 import BeautifulSoup
import re

# ===================== 【核心自定义参数】=====================
# 策略参数
CUSTOM_DAYS_RETURN = 40  # 自定义收益差计算天数（原40天）
CUSTOM_DAYS_MA = 240     # 自定义均线计算天数（原252天）
INIT_CAPITAL = 10000     # 方法A初始本金1万元

# 方案C梯度买入规则（收益差越小/越负，买入金额越高）
# 格式：(阈值下限, 阈值上限, 买入金额) → 收益差 ∈ (上限, 下限] 时触发对应金额
BUY_RULES = [
    # 新增：-0.30 到 -0.19 区间（每降0.01，金额+10）
    (-0.30, -float('inf'), 340),  # 收益差 < -0.30 → 买340元
    (-0.29, -0.30, 330),          # 收益差 ∈ (-0.30, -0.29] → 买330元
    (-0.28, -0.29, 320),          # 收益差 ∈ (-0.29, -0.28] → 买320元
    (-0.27, -0.28, 310),          # 收益差 ∈ (-0.28, -0.27] → 买310元
    (-0.26, -0.27, 300),          # 收益差 ∈ (-0.27, -0.26] → 买300元
    (-0.25, -0.26, 290),          # 收益差 ∈ (-0.26, -0.25] → 买290元
    (-0.24, -0.25, 280),          # 收益差 ∈ (-0.25, -0.24] → 买280元
    (-0.23, -0.24, 270),          # 收益差 ∈ (-0.24, -0.23] → 买270元
    (-0.22, -0.23, 260),          # 收益差 ∈ (-0.23, -0.22] → 买260元
    (-0.21, -0.22, 250),          # 收益差 ∈ (-0.22, -0.21] → 买250元
    (-0.20, -0.21, 240),          # 收益差 ∈ (-0.21, -0.20] → 买240元
    (-0.19, -0.20, 230),          # 收益差 ∈ (-0.20, -0.19] → 买230元
    # 原有：-0.18 到 -0.01 区间（保持不变）
    (-0.18, -0.19, 220),          # 收益差 ∈ (-0.19, -0.18] → 买220元
    (-0.17, -0.18, 210),          # 收益差 ∈ (-0.18, -0.17] → 买210元
    (-0.16, -0.17, 200),          # 收益差 ∈ (-0.17, -0.16] → 买200元
    (-0.15, -0.16, 190),          # 收益差 ∈ (-0.16, -0.15] → 买190元
    (-0.14, -0.15, 180),          # 收益差 ∈ (-0.15, -0.14] → 买180元
    (-0.13, -0.14, 170),          # 收益差 ∈ (-0.14, -0.13] → 买170元
    (-0.12, -0.13, 160),          # 收益差 ∈ (-0.13, -0.12] → 买160元
    (-0.11, -0.12, 150),          # 收益差 ∈ (-0.12, -0.11] → 买150元
    (-0.10, -0.11, 140),          # 收益差 ∈ (-0.11, -0.10] → 买140元
    (-0.09, -0.10, 130),          # 收益差 ∈ (-0.10, -0.09] → 买130元
    (-0.08, -0.09, 120),          # 收益差 ∈ (-0.09, -0.08] → 买120元
    (-0.07, -0.08, 110),          # 收益差 ∈ (-0.08, -0.07] → 买110元
    (-0.06, -0.07, 100),          # 收益差 ∈ (-0.07, -0.06] → 买100元
    (-0.05, -0.06, 90),           # 收益差 ∈ (-0.06, -0.05] → 买90元
    (-0.04, -0.05, 80),           # 收益差 ∈ (-0.05, -0.04] → 买80元
    (-0.03, -0.04, 70),           # 收益差 ∈ (-0.04, -0.03] → 买70元
    (-0.02, -0.03, 60),           # 收益差 ∈ (-0.03, -0.02] → 买60元
    (-0.01, -0.02, 50)            # 收益差 ∈ (-0.02, -0.01] → 买50元
]
# 方案C梯度卖出规则（收益差越大，卖出多买份额比例越高，按最高阈值匹配）
SELL_GRADIENT = {
    0.07: 0.10,  # 收益差 > 0.07 → 卖出多买份额的10%
    0.08: 0.20,  # 收益差 > 0.08 → 卖出多买份额的20%
    0.09: 0.30,  # 收益差 > 0.09 → 卖出多买份额的30%
    0.10: 0.40   # 收益差 > 0.10 → 卖出多买份额的40%
}

DAILY_BASE_INVEST = 50   # 方法B/C基础每日定投金额（必投，不卖出）

# 标的参数（重点：红利ETF 515180，中证全指000985）
HONG_LI_ETF_CODE = "515180"       # 红利ETF代码（ak.fund_etf_hist_em用纯数字）
ZHONG_ZHENG_QUAN_ZHI_SYMBOL = "sh000985"  # 中证全指000985
ETF_START_DATE = "20000101"       # ETF数据起始日期

# 自动获取当前日期作为结束日期
ETF_END_DATE = datetime.now().strftime("%Y%m%d")  # ETF数据结束日期（当前日期）

# 【邮件配置】(功能已禁用，仅保留配置结构)
EMAIL_CONFIG = {
    "sender": "your_email@qq.com",       # 比如：123456@qq.com
    "receiver": "your_email@qq.com",       # 可以和发件邮箱相同
    "smtp_server": "smtp.qq.com",         # QQ邮箱用smtp.qq.com，163邮箱用smtp.163.com
    "smtp_port": 465,                     # SSL端口，QQ/163邮箱均为465
    "auth_code": "your_auth_code",         # 不是登录密码！需在邮箱设置中开启SMTP获取
    "subject": f"红利ETF策略建议_{datetime.now().strftime('%Y%m%d')}"  # 邮件标题
}

# ===================== 基础配置 =====================
# 过滤无关警告
warnings.filterwarnings("ignore", category=UserWarning, module="py_mini_racer")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pkg_resources")
# 关闭PIL图片像素上限警告
PIL.Image.MAX_IMAGE_PIXELS = None

# 配置matplotlib在无图形界面环境下运行
import matplotlib
matplotlib.use('Agg')  # 非交互式后端，适合服务器环境

# 设置matplotlib中文显示（解决乱码）
import platform
import matplotlib.font_manager as fm

# 根据操作系统选择合适的字体解决方案
if platform.system() == 'Windows':
    # Windows系统：使用系统自带的中文字体
    windows_fonts = ['SimHei', 'Microsoft YaHei', 'SimSun', 'FangSong']
    available_fonts = []
    for font in fm.fontManager.ttflist:
        if font.name in windows_fonts:
            available_fonts.append(font.name)
    
    if available_fonts:
        plt.rcParams["font.sans-serif"] = [available_fonts[0]]
        plt.rcParams["font.family"] = "sans-serif"
    else:
        # 如果没有找到指定的中文字体，尝试使用默认的中文字体
        plt.rcParams["font.sans-serif"] = ["SimHei"]
        # 禁用中文显示警告
        warnings.filterwarnings("ignore", category=UserWarning, message="Glyph.*missing from font")
else:
    # Linux系统（如GitHub Actions）：使用中文字体
    # 尝试使用多种中文字体，确保兼容
    linux_fonts = ['WenQuanYi Micro Hei', 'WenQuanYi Zen Hei', 'SimHei', 'Microsoft YaHei']
    available_fonts = []
    for font in fm.fontManager.ttflist:
        if font.name in linux_fonts:
            available_fonts.append(font.name)
    
    if available_fonts:
        plt.rcParams["font.sans-serif"] = [available_fonts[0]]
        plt.rcParams["font.family"] = "sans-serif"
    else:
        # 如果没有找到指定的中文字体，尝试使用默认的中文字体
        plt.rcParams["font.sans-serif"] = ["WenQuanYi Micro Hei"]
        # 禁用中文显示警告
    warnings.filterwarnings("ignore", category=UserWarning, message="Glyph.*missing from font")

plt.rcParams["axes.unicode_minus"] = False  # 解决负号显示问题

# 定义保存图片的文件夹
SAVE_DIR = os.environ.get('SAVE_DIR', os.path.dirname(os.path.abspath(__file__)))
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

# ===================== 实时价格获取函数 =====================
def get_hongli_etf_realtime_price():
    """获取红利ETF（515180）实时最新价"""
    try:
        fund_etf_category_sina_df = ak.fund_etf_category_sina(symbol="ETF基金")
        # 筛选代码为sh515180的行
        hongli_row = fund_etf_category_sina_df[fund_etf_category_sina_df['代码']=='sh515180']
        if not hongli_row.empty:
            # 提取最新价，转成浮点数
            price = float(hongli_row['最新价'].iloc[0])
            return price
        else:
            print("❌ 未找到红利ETF（sh515180）的实时数据")
            return None
    except Exception as e:
        print(f"❌ 获取红利ETF实时价格失败：{e}")
        return None

def get_zzqz_price():
    """获取中证全指（000985）实时最新价"""
    # 1. 先获取页面，找到股票代码参数
    url = "https://quote.eastmoney.com/zs000985.html"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        # 2. 获取页面HTML
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # 抛出HTTP错误
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 3. 从页面脚本中提取secid参数
        # 东方财富使用 secid: "1.000985" 的格式（1=上海, 0=深圳）
        secid_match = re.search(r'var secid = "(\d+\.\d+)"', response.text)
        if secid_match:
            secid = secid_match.group(1)
        else:
            secid = "1.000985"  # 默认值
        
        # 4. 调用API获取实时价格
        api_url = "https://push2.eastmoney.com/api/qt/stock/get"
        params = {
            "secid": secid,
            "fields": "f43",  # f43是最新价字段
            "ut": "fa5fd1943c7b386f172d6893dbfba10b"
        }
        
        api_response = requests.get(api_url, headers=headers, params=params, timeout=5)
        api_response.raise_for_status()
        data = api_response.json()
        
        # 5. 解析价格（需要除以100）
        if data.get("data") and "f43" in data["data"]:
            price = data["data"]["f43"] / 100
            return price
        else:
            print("❌ 未获取到中证全指实时价格数据")
            return None
    except Exception as e:
        print(f"❌ 获取中证全指实时价格失败：{e}")
        return None

# ===================== 工具函数：匹配梯度买入金额 =====================
def get_extra_invest_amount(diff_value):
    """根据收益差匹配梯度买入金额"""
    if pd.isna(diff_value):
        return 0, None
    
    for lower, upper, amount in BUY_RULES:
        if upper < diff_value <= lower:
            return amount, lower  # 返回买入金额 + 触发的阈值下限
    return 0, None



# ===================== 三大指数 K线图绘制 =====================
def plot_index_kline(symbol, name, save_dir):
    """获取指数历史数据并绘制带均线的K线图"""
    try:
        # 获取最近120天数据以计算60日均线
        df = ak.stock_zh_index_daily_em(symbol=symbol)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # 计算均线
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma60'] = df['close'].rolling(60).mean()
        
        # 只取最近60个交易日展示
        plot_df = df.tail(60).copy()
        plot_df = plot_df.reset_index(drop=True)
        
        fig, ax = plt.subplots(figsize=(10, 5))
        
        # 绘制K线 (简单实现)
        for i, row in plot_df.iterrows():
            color = 'red' if row['close'] >= row['open'] else 'green'
            # 影线
            ax.vlines(i, row['low'], row['high'], color=color, linewidth=1)
            # 实体
            height = abs(row['close'] - row['open'])
            bottom = min(row['open'], row['close'])
            ax.add_patch(plt.Rectangle((i - 0.3, bottom), 0.6, height, color=color))
            
        # 绘制均线
        ax.plot(plot_df.index, plot_df['ma5'], label='MA5', linewidth=1, alpha=0.8)
        ax.plot(plot_df.index, plot_df['ma10'], label='MA10', linewidth=1, alpha=0.8)
        ax.plot(plot_df.index, plot_df['ma20'], label='MA20', linewidth=1, alpha=0.8)
        ax.plot(plot_df.index, plot_df['ma60'], label='MA60', linewidth=1, alpha=0.8)
        
        ax.set_title(f"{name} ({symbol}) 最近60日K线", fontsize=14)
        ax.legend(loc='upper left', fontsize=8)
        ax.grid(True, alpha=0.2)
        
        # 设置X轴标签 (日期)
        xticks = range(0, len(plot_df), 10)
        ax.set_xticks(xticks)
        ax.set_xticklabels([plot_df['date'].iloc[i].strftime('%m-%d') for i in xticks])
        
        save_path = os.path.join(save_dir, f"kline_{symbol}.png")
        plt.savefig(save_path, bbox_inches='tight', dpi=100)
        plt.close()
        return save_path, plot_df.iloc[-1]['close'], plot_df.iloc[-1]['close']/plot_df.iloc[-2]['close'] - 1
    except Exception as e:
        print(f"❌ 绘制指数 {name} K线失败: {e}")
        return None, None, None

# ===================== 保存策略HTML片段函数 =====================
def save_strategy_html_fragment(latest_data, chart_path, df, index_data_list=None):
    """
    生成并保存策略HTML片段（含核心数据+普通内嵌图表+最新20条数据+三大指数），供网页展示
    """
    # 1. 提取并格式化最新20条数据
    latest_20_data = df.tail(20)[['date', 'close_hongli', 'close_quanzhi', 'diff_custom_days']].copy()
    latest_20_data['date'] = latest_20_data['date'].dt.strftime('%Y-%m-%d')
    latest_20_data['close_hongli'] = latest_20_data['close_hongli'].round(3)
    latest_20_data['close_quanzhi'] = latest_20_data['close_quanzhi'].round(3)
    
    # 计算涨跌幅
    latest_20_data['hongli_change(%)'] = latest_20_data['close_hongli'].pct_change() * 100
    latest_20_data['quanzhi_change(%)'] = latest_20_data['close_quanzhi'].pct_change() * 100
    latest_20_data['diff_custom_days(%)'] = latest_20_data['diff_custom_days'] * 100
    
    # 填充第一行的涨跌幅为 '-'
    latest_20_data = latest_20_data.round({'hongli_change(%)': 2, 'quanzhi_change(%)': 2, 'diff_custom_days(%)': 2})
    latest_20_data = latest_20_data.fillna('-')
    
    # 构建历史数据表格
    recent_table_html = """
    <div class="table-container">
        <table class="data-table">
            <thead>
                <tr>
                    <th>日期</th>
                    <th>红利ETF收盘价</th>
                    <th>涨跌幅(%)</th>
                    <th>中证全指收盘价</th>
                    <th>涨跌幅(%)</th>
                    <th>收益差(%)</th>
                </tr>
            </thead>
            <tbody>
    """
    for _, row in latest_20_data.iterrows():
        h_color = "text-red" if row['hongli_change(%)'] != '-' and row['hongli_change(%)'] > 0 else "text-green" if row['hongli_change(%)'] != '-' and row['hongli_change(%)'] < 0 else ""
        q_color = "text-red" if row['quanzhi_change(%)'] != '-' and row['quanzhi_change(%)'] > 0 else "text-green" if row['quanzhi_change(%)'] != '-' and row['quanzhi_change(%)'] < 0 else ""
        d_color = "text-red" if row['diff_custom_days(%)'] != '-' and row['diff_custom_days(%)'] > 0 else "text-green" if row['diff_custom_days(%)'] != '-' and row['diff_custom_days(%)'] < 0 else ""
        
        recent_table_html += f"""
                <tr>
                    <td>{row['date']}</td>
                    <td>{row['close_hongli']}</td>
                    <td class="{h_color}">{row['hongli_change(%)']}{'%' if row['hongli_change(%)'] != '-' else ''}</td>
                    <td>{row['close_quanzhi']}</td>
                    <td class="{q_color}">{row['quanzhi_change(%)']}{'%' if row['quanzhi_change(%)'] != '-' else ''}</td>
                    <td class="{d_color}">{row['diff_custom_days(%)']}%</td>
                </tr>
        """
    recent_table_html += "</tbody></table></div>"
    
    # 构建三大指数HTML
    indices_html = ""
    if index_data_list:
        indices_html = """
        <div class="sub-card">
            <div class="sub-header">🌍 今日三大指数行情</div>
            <div class="summary-grid">
        """
        for item in index_data_list:
            change_color = "text-red" if item['change'] > 0 else "text-green"
            indices_html += f"""
                <div class="summary-item">
                    <div class="label">{item['name']}</div>
                    <div class="value">{item['price']:.2f}</div>
                    <div class="label {change_color}">{item['change']*100:+.2f}%</div>
                </div>
            """
        indices_html += "</div><div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px;'>"
        for item in index_data_list:
            if item['chart']:
                indices_html += f"""
                    <div style='text-align: center;'>
                        <img src="{os.path.basename(item['chart'])}" style="width: 100%; border-radius: 8px;">
                    </div>
                """
        indices_html += "</div></div>"

    # 2. 构建HTML片段
    img_filename = os.path.basename(chart_path)
    
    # 信号灯颜色逻辑
    status_class = "status-green" if "绿" in latest_data['status'] else "status-red" if "红" in latest_data['status'] else "status-yellow"
    
    html_content = f"""
    <div class="strategy-card">
        <div class="card-header">
            <span class="icon">📊</span> 红利ETF 每日策略建议 ({latest_data['date']})
        </div>
        
        {indices_html}

        <div class="table-container" style="margin-top: 25px;">
            <table class="data-table" style="margin-bottom: 25px;">
                <thead>
                    <tr style="background: #f8f9fa;">
                        <th style="width: 50%;">策略指标</th>
                        <th>数值</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>40日收益差（红利-中证全指）</td>
                        <td class="{'text-red' if latest_data['diff']>0 else 'text-green'}" style="font-weight: bold;">{latest_data['diff']*100:.2f}%</td>
                    </tr>
                    <tr>
                        <td>红利ETF最新收盘价</td>
                        <td>{latest_data['hongli_close']:.3f}</td>
                    </tr>
                    <tr>
                        <td>中证全指最新收盘价</td>
                        <td>{latest_data['quanzhi_close']:.3f}</td>
                    </tr>
                    <tr>
                        <td>信号灯状态</td>
                        <td><span class="badge {status_class}">{latest_data['status']}</span></td>
                    </tr>
                    <tr>
                        <td>操作建议</td>
                        <td><span class="badge status-blue" style="white-space: normal;">{latest_data['operation']}</span></td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="sub-card">
            <div class="sub-header">📈 40日收益差趋势图</div>
            <img src="{img_filename}" class="strategy-img" />
        </div>

        <div class="sub-card">
            <div class="sub-header">📋 最新核心数据波动 (最近20个交易日)</div>
            {recent_table_html}
        </div>
        
        <div class="footer-tip" style="margin-top: 30px; border-top: 1px solid #eee; padding-top: 15px;">
            ⚠️ 本建议仅为数据分析参考，不构成投资建议
        </div>
    </div>
    """
    
    output_path = os.path.join(os.path.dirname(chart_path), 'strategy_fragment.html')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"✅ 策略HTML片段已保存至：{output_path}")

# ===================== 邮件发送函数（普通图片版）=====================
def send_strategy_email(latest_data, chart_path, df):
    """
    发送策略建议邮件（含核心数据+普通内嵌图表+最新20条数据）
    :param latest_data: 最新数据字典
    :param chart_path: 图表保存路径
    :param df: 完整的合并数据DataFrame（用于提取最新20条）
    """
    # 1. 构建邮件主体
    msg = MIMEMultipart('related')
    
    # ========== From/To/Subject 格式 ==========
    msg['From'] = EMAIL_CONFIG['sender']
    msg['To'] = EMAIL_CONFIG['receiver']
    msg['Subject'] = Header(EMAIL_CONFIG['subject'], 'utf-8')
    
    # 2. 提取并格式化最新20条数据
    latest_10_data = df.tail(20)[['date', 'close_hongli', 'close_quanzhi', 'diff_custom_days']].copy()
    # 格式化日期
    latest_10_data['date'] = latest_10_data['date'].dt.strftime('%Y-%m-%d')
    # 保留小数位数
    latest_10_data['close_hongli'] = latest_10_data['close_hongli'].round(3)
    latest_10_data['close_quanzhi'] = latest_10_data['close_quanzhi'].round(3)
    # 计算涨跌幅
    latest_10_data['hongli_change(%)'] = latest_10_data['close_hongli'].pct_change() * 100
    latest_10_data['quanzhi_change(%)'] = latest_10_data['close_quanzhi'].pct_change() * 100
    # 收益差转百分比
    latest_10_data['diff_custom_days(%)'] = latest_10_data['diff_custom_days'] * 100
    # 保留2位小数，空值替换为'-'
    latest_10_data = latest_10_data.round({
        'hongli_change(%)': 2,
        'quanzhi_change(%)': 2,
        'diff_custom_days(%)': 2
    }).fillna('-')
    
    # 构建最新20条数据的HTML表格
    recent_table_html = "<table border='1' cellpadding='8' cellspacing='0' style='border-collapse: collapse;'>"
    # 表头
    recent_table_html += """
    <tr style="background-color: #f0f0f0;">
        <th>日期</th>
        <th>红利ETF收盘价</th>
        <th>红利ETF涨跌幅(%)</th>
        <th>中证全指收盘价</th>
        <th>中证全指涨跌幅(%)</th>
        <th>40日收益差(%)</th>
    </tr>
    """
    # 数据行
    for _, row in latest_10_data.iterrows():
        recent_table_html += f"""
        <tr>
            <td>{row['date']}</td>
            <td>{row['close_hongli']}</td>
            <td style="color: {'red' if row['hongli_change(%)'] != '-' and row['hongli_change(%)'] > 0 else 'green' if row['hongli_change(%)'] != '-' and row['hongli_change(%)'] < 0 else 'black'};">
                {row['hongli_change(%)']}
            </td>
            <td>{row['close_quanzhi']}</td>
            <td style="color: {'red' if row['quanzhi_change(%)'] != '-' and row['quanzhi_change(%)'] > 0 else 'green' if row['quanzhi_change(%)'] != '-' and row['quanzhi_change(%)'] < 0 else 'black'};">
                {row['quanzhi_change(%)']}
            </td>
            <td style="color: {'red' if row['diff_custom_days(%)'] != '-' and row['diff_custom_days(%)'] > 0 else 'green' if row['diff_custom_days(%)'] != '-' and row['diff_custom_days(%)'] < 0 else 'black'};">
                {row['diff_custom_days(%)']}
            </td>
        </tr>
        """
    recent_table_html += "</table>"
    
    # 3. 构建邮件正文（HTML格式，新增最新20条数据表格）
    html_content = f"""
    <html>
      <body>
        <h2>📊 红利ETF每日策略建议（{latest_data['date']}）</h2>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse;">
          <tr style="background-color: #f0f0f0;">
            <th>指标</th>
            <th>数值</th>
          </tr>
          <tr>
            <td>40日收益差（红利-中证全指）</td>
            <td><b style="color: {'red' if latest_data['diff']>0 else 'green'};">{latest_data['diff']*100:.2f}%</b></td>
          </tr>
          <tr>
            <td>红利ETF最新收盘价</td>
            <td>{latest_data['hongli_close']:.3f}</td>
          </tr>
          <tr>
            <td>中证全指最新收盘价</td>
            <td>{latest_data['quanzhi_close']:.3f}</td>
          </tr>
          <tr>
            <td>信号灯状态</td>
            <td><b>{latest_data['status']}</b></td>
          </tr>
          <tr>
            <td>操作建议</td>
            <td><b style="color: blue;">{latest_data['operation']}</b></td>
          </tr>
        </table>
        <br>
        <h4>📈 40日收益差趋势图：</h4>
        <img src="cid:chart_img" style="border: none; max-width: 100%; display: block;" />
        <br>
        <h4>📋 最新核心数据波动：</h4>
        {recent_table_html}
        <br><br>
        <p>⚠️ 本建议仅为数据分析参考，不构成投资建议</p>
      </body>
    </html>
    """
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))

    # 4. 嵌入图片到邮件正文
    try:
        with open(chart_path, 'rb') as f:
            img_data = f.read()
            img = MIMEImage(img_data, _subtype='png')
            img.add_header('Content-ID', '<chart_img>')
            msg.attach(img)
        
        # 添加图片作为附件
        with open(chart_path, 'rb') as f:
            att_img = MIMEImage(f.read(), _subtype='png')
            att_img.add_header('Content-Disposition', 'attachment', 
                               filename=('utf-8', '', f"红利ETF策略图_{latest_data['date']}.png"))
            msg.attach(att_img)
    except Exception as e:
        print(f"⚠️ 图表嵌入失败：{e}，将仅发送附件")
        with open(chart_path, 'rb') as f:
            att_img = MIMEImage(f.read())
            att_img.add_header('Content-Disposition', 'attachment', filename=('utf-8', '', os.path.basename(chart_path)))
            msg.attach(att_img)

    # 5. 发送邮件
    try:
        server = smtplib.SMTP_SSL(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'], timeout=30)
        server.login(EMAIL_CONFIG['sender'], EMAIL_CONFIG['auth_code'])
        server.sendmail(
            from_addr=EMAIL_CONFIG['sender'],
            to_addrs=EMAIL_CONFIG['receiver'].split(','),
            msg=msg.as_string()
        )
        server.quit()
        print(f"\n✅ 邮件发送成功！已发送至：{EMAIL_CONFIG['receiver']}")
    except smtplib.SMTPAuthenticationError:
        print("❌ 邮件发送失败：授权码错误/邮箱未开启SMTP服务")
        print("  解决：1.检查授权码是否正确 2.登录QQ邮箱→设置→账户→开启POP3/SMTP服务")
    except smtplib.SMTPRecipientsRefused:
        print("❌ 邮件发送失败：收件人邮箱地址错误")
    except Exception as e:
        print(f"❌ 邮件发送失败：{str(e)}")
# ===================== 数据获取函数（无缓存）=====================
def get_zzqz_index_data(symbol: str) -> pd.DataFrame:
    """获取中证全指指数数据（主备模式）"""
    result_df = pd.DataFrame()
    # 主接口：腾讯数据源
    try:
        print(f"  尝试调用主接口获取中证全指 {symbol} 数据...")
        result_df = ak.stock_zh_index_daily_tx(symbol=symbol)
        # 腾讯接口字段是中文，统一为英文
        if not result_df.empty and "收盘" in result_df.columns:
            result_df.rename(columns={"日期": "date", "收盘": "close"}, inplace=True)
            result_df = result_df[["date", "close"]]
    except Exception:
        pass

    # 主接口失败则用备用接口
    if result_df.empty:
        try:
            print(f"  主接口失败，切换备用接口获取中证全指 {symbol} 数据...")
            result_df = ak.stock_zh_index_daily(symbol=symbol)
            result_df = result_df[["date", "close"]]  # 仅保留核心字段
        except Exception as e:
            print(f"❌ 备用接口获取中证全指 {symbol} 失败：{e}")
            return pd.DataFrame()

    # 数据清洗
    result_df["date"] = pd.to_datetime(result_df["date"])
    result_df = result_df.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
    print(f"  ✅ 中证全指 {symbol} 数据获取成功，共{len(result_df)}条")
    return result_df

def get_hongli_etf_data() -> pd.DataFrame:
    """获取红利ETF数据（无缓存，实时获取）"""
    print(f"📥 正在从akshare获取红利ETF {HONG_LI_ETF_CODE} 数据...")
    try:
        # 调用ak.fund_etf_hist_em获取ETF数据（前复权）
        etf_df = ak.fund_etf_hist_em(
            symbol=HONG_LI_ETF_CODE,
            period="daily",
            start_date=ETF_START_DATE,
            end_date=ETF_END_DATE,
            adjust="qfq"  # 前复权
        )
        # 仅保留核心字段：date + close
        etf_df = etf_df[["日期", "收盘"]].copy()
        etf_df.rename(columns={"日期": "date", "收盘": "close"}, inplace=True)
        # 数据清洗
        etf_df["date"] = pd.to_datetime(etf_df["date"])
        etf_df = etf_df.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
        print(f"✅ 红利ETF {HONG_LI_ETF_CODE} 数据获取完成，共{len(etf_df)}条")
        return etf_df
    except Exception as e:
        print(f"❌ 红利ETF {HONG_LI_ETF_CODE} 数据获取失败：{e}")
        return pd.DataFrame()

def get_index_data():
    """
    整合数据：
    - 红利ETF：实时获取
    - 中证全指：调用指定函数获取（无缓存）
    """
    # 1. 实时获取红利ETF数据
    hongli_df = get_hongli_etf_data()
    if hongli_df.empty:
        raise ValueError("❌ 红利ETF数据获取失败")
    
    # 2. 获取中证全指数据（无缓存）
    print("📌 开始获取中证全指数据（无缓存）...")
    quanzhi_df = get_zzqz_index_data(ZHONG_ZHENG_QUAN_ZHI_SYMBOL)
    if quanzhi_df.empty:
        raise ValueError("❌ 中证全指数据获取失败")
    
    # 3. 对齐日期（仅保留交集）
    merge_df = pd.merge(
        hongli_df, quanzhi_df, 
        on="date", 
        suffixes=("_hongli", "_quanzhi"), 
        how="inner"
    )
    merge_df = merge_df.sort_values("date").reset_index(drop=True)
    print(f"✅ 数据合并完成，共{len(merge_df)}条有效日期数据")
    
    # ========== 关键新增：检查并补充今日实时数据 ==========
    today = datetime.now().date()  # 今天的日期（date类型）
    latest_data_date = merge_df['date'].iloc[-1].date()  # 历史数据的最新日期

    print(f"\n📅 历史数据最新日期：{latest_data_date} | 今日日期：{today}")

    if latest_data_date != today:
        print("⚠️ 历史数据未包含今日，开始补充实时数据...")
        
        # 获取实时价格
        hongli_realtime = get_hongli_etf_realtime_price()
        zzqz_realtime = get_zzqz_price()
        
        if hongli_realtime is not None and zzqz_realtime is not None:
            # 构造今日数据行
            today_datetime = datetime.combine(today, datetime.min.time())  # 转datetime类型
            new_row = pd.DataFrame({
                'date': [today_datetime],
                'close_hongli': [hongli_realtime],
                'close_quanzhi': [zzqz_realtime]
            })
            
            # 将新行添加到merge_df末尾
            merge_df = pd.concat([merge_df, new_row], ignore_index=True)
            
            # 重新排序（确保日期正确）
            merge_df = merge_df.sort_values('date').reset_index(drop=True)
            
            print(f"\n✅ 已补充今日({today})实时数据！最新数据波动情况：")
            print("-" * 80)
            # 筛选关键列并格式化输出
            latest_data = merge_df.tail(10)[['date', 'close_hongli', 'close_quanzhi']].copy()
            # 格式化日期为字符串，保留收盘价三位小数
            latest_data['date'] = latest_data['date'].dt.strftime('%Y-%m-%d')
            latest_data['close_hongli'] = latest_data['close_hongli'].round(3)
            latest_data['close_quanzhi'] = latest_data['close_quanzhi'].round(3)
            # 计算收盘价的日涨跌幅（方便看波动）
            latest_data['hongli_change'] = latest_data['close_hongli'].pct_change() * 100
            latest_data['quanzhi_change'] = latest_data['close_quanzhi'].pct_change() * 100
            latest_data['hongli_change'] = latest_data['hongli_change'].round(2)
            latest_data['quanzhi_change'] = latest_data['quanzhi_change'].round(2)
            # 重命名列名，更易读
            latest_data.rename(
                columns={
                    'date': '日期',
                    'close_hongli': '红利ETF收盘价',
                    'close_quanzhi': '中证全指收盘价',
                    'hongli_change': '红利ETF涨跌幅(%)',
                    'quanzhi_change': '中证全指涨跌幅(%)'
                },
                inplace=True
            )
            # 打印格式化后的最新数据
            print(latest_data.to_string(index=False))
            print("-" * 80)
        else:
            print("❌ 实时价格获取失败，无法补充今日数据")
    else:
        print("✅ 历史数据已包含今日，无需补充")
    
    return merge_df

# ===================== 三种策略收益计算 =====================
def calculate_all_strategies(df: pd.DataFrame) -> pd.DataFrame:
    """计算三种策略收益：
    A：原择时买卖策略（全仓操作）
    B：每日固定定投50元（无择时）
    C：基础定投50元 + 梯度多买 + 梯度止盈卖出多买份额
    """
    df = df.copy()
    # ========== 方法A：原择时买卖策略 ==========
    hold_flag = False  # 是否持仓
    cash_a = INIT_CAPITAL  # 初始现金
    shares_a = 0  # 持有份额
    strategy_a_assets = []  # 策略A资产净值

    # ========== 方法B：每日固定定投50元 ==========
    shares_b = 0  # 方法B持有份额
    total_invest_b = 0  # 方法B累计投入本金
    strategy_b_assets = []  # 方法B资产净值

    # ========== 方法C：基础定投+梯度多买+梯度止盈 ==========
    base_shares_c = 0  # 基础定投累计份额（每日50元，永不卖出）
    extra_shares_c = 0  # 当前剩余多买份额（梯度买入累计，梯度卖出扣减）
    total_base_invest_c = 0  # 基础定投累计投入
    total_extra_invest_c = 0  # 多投累计投入（随卖出按比例扣减）
    cash_c = 0  # 卖出多买份额的现金（已实现收益）
    strategy_c_assets = []  # 方法C资产净值
    c_detail_log = []  # 方法C交易明细日志

    # 买入持有策略（参考基准）
    first_close = df["close_hongli"].iloc[0]
    buy_hold_shares = INIT_CAPITAL / first_close
    buy_hold_assets = []

    # 遍历每一行计算收益
    for idx, row in df.iterrows():
        current_close = row["close_hongli"]
        current_diff = row["diff_custom_days"]
        current_date = row["date"].strftime("%Y-%m-%d")
        sell_ratio = 0  # 当日卖出比例
        sell_shares = 0  # 当日卖出份额
        extra_invest = 0  # 当日额外买入金额
        trigger_threshold = None  # 触发的买入阈值

        # ---------------- 方法A：择时买卖 ----------------
        if not hold_flag and not pd.isna(current_diff) and current_diff <= -0.01:
            # 绿灯（低于最低买入阈值）：全仓买入
            shares_a = cash_a / current_close
            cash_a = 0
            hold_flag = True
            print(f"【方法A-买入】{current_date}：收益差={current_diff*100:.2f}%，买入价={current_close:.3f}")
        elif hold_flag and not pd.isna(current_diff) and current_diff > max(SELL_GRADIENT.keys()):
            # 红灯（超过最高卖出阈值）：全仓卖出
            cash_a = shares_a * current_close
            shares_a = 0
            hold_flag = False
            print(f"【方法A-卖出】{current_date}：收益差={current_diff*100:.2f}%，卖出价={current_close:.3f}，累计收益={(cash_a-INIT_CAPITAL)/INIT_CAPITAL*100:.2f}%")
        
        # 方法A当前资产
        current_asset_a = cash_a + shares_a * current_close
        strategy_a_assets.append(current_asset_a)

        # ---------------- 方法B：每日定投50元 ----------------
        invest_b = DAILY_BASE_INVEST
        shares_b += invest_b / current_close
        total_invest_b += invest_b
        current_asset_b = shares_b * current_close
        strategy_b_assets.append(current_asset_b)

        # ---------------- 方法C：基础定投+梯度多买+梯度止盈 ----------------
        # 1. 每日基础定投50元（必投，不卖出）
        base_shares_c += DAILY_BASE_INVEST / current_close
        total_base_invest_c += DAILY_BASE_INVEST

        # 2. 梯度多买：精准匹配收益差区间
        if not pd.isna(current_diff):
            extra_invest, trigger_threshold = get_extra_invest_amount(current_diff)

            # 执行梯度多买（若有额外买入金额）
            if extra_invest > 0:
                extra_shares_add = extra_invest / current_close
                extra_shares_c += extra_shares_add
                total_extra_invest_c += extra_invest

                log_msg = (f"【方法C-梯度多买】{current_date}：收益差={current_diff*100:.2f}%，触发阈值<{trigger_threshold*100:.1f}%"
                           f"\n  当日多买金额={extra_invest:.0f}元 | 新增多买份额={extra_shares_add:.2f} | 累计多买份额={extra_shares_c:.2f}"
                           f"\n  累计多投本金={total_extra_invest_c:.2f}元 | 基础定投累计={total_base_invest_c:.2f}元")
                print(log_msg)
                c_detail_log.append(log_msg)

        # 3. 梯度止盈：按收益差匹配最高卖出比例（仅当有多买份额时执行）
        if not pd.isna(current_diff) and extra_shares_c > 0:
            # 按阈值从高到低遍历（0.10 → 0.07），匹配最高比例
            for threshold in sorted(SELL_GRADIENT.keys(), reverse=True):
                if current_diff > threshold:
                    sell_ratio = SELL_GRADIENT[threshold]
                    sell_shares = extra_shares_c * sell_ratio
                    break

            # 执行卖出（若有卖出比例）
            if sell_ratio > 0:
                # 计算卖出金额和对应收回的投入本金
                sell_amount = sell_shares * current_close
                recover_invest = total_extra_invest_c * sell_ratio  # 按比例收回多投本金
                
                # 更新现金、多买份额、多投累计投入
                cash_c += sell_amount
                extra_shares_c -= sell_shares
                total_extra_invest_c -= recover_invest

                # 计算多买部分已实现收益
                extra_realized_return = (sell_amount - recover_invest) / recover_invest * 100 if recover_invest > 0 else 0

                # 记录日志
                log_msg = (f"【方法C-梯度卖出】{current_date}：收益差={current_diff*100:.2f}%，触发阈值>{threshold*100:.1f}%，卖出比例{sell_ratio*100:.0f}%"
                           f"\n  卖出份额={sell_shares:.2f} | 卖出金额={sell_amount:.2f}元 | 收回多投本金={recover_invest:.2f}元"
                           f"\n  多买部分已实现收益={extra_realized_return:.2f}% | 剩余多买份额={extra_shares_c:.2f} | 剩余多投本金={total_extra_invest_c:.2f}元")
                print(log_msg)
                c_detail_log.append(log_msg)

        # 方法C当前资产 = 现金（卖出收回） + 基础份额市值 + 剩余多买份额市值
        current_asset_c = cash_c + (base_shares_c + extra_shares_c) * current_close
        strategy_c_assets.append(current_asset_c)

        # ---------------- 买入持有基准 ----------------
        buy_hold_asset = buy_hold_shares * current_close
        buy_hold_assets.append(buy_hold_asset)

    # 计算各策略收益率（标准化对比）
    df["strategy_a_asset"] = strategy_a_assets
    df["strategy_a_return"] = (df["strategy_a_asset"] - INIT_CAPITAL) / INIT_CAPITAL * 100  # 基于初始本金

    df["strategy_b_asset"] = strategy_b_assets
    df["total_invest_b"] = total_invest_b  # 累计投入（整列相同）
    df["strategy_b_return"] = (df["strategy_b_asset"] - df["total_invest_b"]) / df["total_invest_b"] * 100  # 基于累计投入

    # 方法C累计总投入 = 基础定投累计 + 剩余多投累计（已卖出部分不计入）
    total_invest_c = total_base_invest_c + total_extra_invest_c
    df["strategy_c_asset"] = strategy_c_assets
    df["total_invest_c"] = total_invest_c  # 最终累计投入（整列相同）
    # 收益率 =（当前资产 - 累计总投入）/ 累计总投入 ×100%（现金+持仓，真实反映策略效果）
    df["strategy_c_return"] = (df["strategy_c_asset"] - df["total_invest_c"]) / df["total_invest_c"] * 100

    df["buy_hold_asset"] = buy_hold_assets
    df["buy_hold_return"] = (df["buy_hold_asset"] - INIT_CAPITAL) / INIT_CAPITAL * 100  # 参考基准

    # 输出最终收益对比
    final_a = df.iloc[-1]
    final_b = df.iloc[-1]
    final_c = df.iloc[-1]
    print("="*80)
    print(f"三种策略最终收益对比（收益差{CUSTOM_DAYS_RETURN}天 | 均线{CUSTOM_DAYS_MA}天 | 梯度买卖）")
    print("="*80)
    print(f"【方法A】择时买卖策略 | 初始本金：{INIT_CAPITAL}元")
    print(f"  最终资产：{final_a['strategy_a_asset']:.2f}元 | 收益率：{final_a['strategy_a_return']:.2f}%")
    print(f"【方法B】每日定投50元 | 累计投入：{final_b['total_invest_b']:.2f}元")
    print(f"  最终资产：{final_b['strategy_b_asset']:.2f}元 | 收益率：{final_b['strategy_b_return']:.2f}%")
    print(f"【方法C】梯度买卖策略 | 累计投入：{final_c['total_invest_c']:.2f}元")
    print(f"  最终资产：{final_c['strategy_c_asset']:.2f}元 | 收益率：{final_c['strategy_c_return']:.2f}%")
    print(f"  方法C明细：基础份额={base_shares_c:.2f} | 剩余多买份额={extra_shares_c:.2f} | 卖出现金={cash_c:.2f}元")
    print(f"【参考】买入持有策略 | 初始本金：{INIT_CAPITAL}元")
    print(f"  最终资产：{final_a['buy_hold_asset']:.2f}元 | 收益率：{final_a['buy_hold_return']:.2f}%")
    print("="*80)

    return df

# ===================== 信号灯判断（适配梯度买卖）=====================
def get_signal_status(diff_value: float) -> tuple:
    """根据自定义天数收益差判断红绿灯状态和操作建议（适配梯度买卖）"""
    if pd.isna(diff_value):
        return "数据不足", f"无法判断（需至少{CUSTOM_DAYS_RETURN}天数据）"
    
    # 匹配梯度买入建议
    extra_invest, trigger_threshold = get_extra_invest_amount(diff_value)
    buy_suggest = f"基础定投50元 + 额外多投{extra_invest}元" if extra_invest > 0 else ""
    
    # 匹配梯度卖出建议
    sell_suggest = ""
    for threshold in sorted(SELL_GRADIENT.keys(), reverse=True):
        if diff_value > threshold:
            sell_suggest = f" + 卖出多买份额的{SELL_GRADIENT[threshold]*100:.0f}%"
            break
    
    # 综合状态和建议
    if extra_invest > 0:
        status = f"绿灯（低估{abs(diff_value)*100:.1f}%）"
        operation = buy_suggest + sell_suggest if sell_suggest else buy_suggest
    elif diff_value >= min(SELL_GRADIENT.keys()):
        status = f"红灯（高估{diff_value*100:.1f}%）"
        operation = f"仅基础定投50元{sell_suggest}"
    else:
        status = "黄灯（适中）"
        operation = "仅基础定投50元，不操作多买份额"
    
    return status, operation

# ===================== 绘制普通组合图表 =====================
def plot_combined_chart(df: pd.DataFrame):
    """
    绘制普通组合图表：
    - 上半部分：红利ETF收盘价 + 三种策略收益曲线（双Y轴）
    - 下半部分：40日收益差 + 240日均线 + 梯度买卖阈值
    """
    # 过滤掉均线数据不足的行
    plot_df = df.dropna(subset=[f"diff_{CUSTOM_DAYS_RETURN}d_{CUSTOM_DAYS_MA}ma"]).copy()
    
    # 创建2行1列子图
    fig, (ax1, ax2) = plt.subplots(
        nrows=2, ncols=1, 
        figsize=(16, 10), 
        gridspec_kw={'height_ratios': [1.5, 1]},
        sharex=True
    )

    # ========== 上半部分：收盘价 + 收益曲线 ==========
    # 左Y轴：红利ETF收盘价
    ax1_left = ax1
    line1 = ax1_left.plot(plot_df["date"], plot_df["close_hongli"], 
                          color="#2ca02c", linewidth=1.5, label="红利ETF（515180）收盘价")
    ax1_left.set_ylabel("收盘价", fontsize=12, labelpad=8)
    ax1_left.tick_params(axis='y', labelcolor="#2ca02c", labelsize=10)
    ax1_left.grid(True, alpha=0.3)

    # 右Y轴：收益率曲线
    ax1_right = ax1_left.twinx()
    line2 = ax1_right.plot(plot_df["date"], plot_df["strategy_a_return"], 
                           color="#ff7f0e", linewidth=2, label="方法A：择时买卖收益（%）")
    line3 = ax1_right.plot(plot_df["date"], plot_df["strategy_b_return"], 
                           color="#1f77b4", linewidth=1.5, label="方法B：每日定投50元收益（%）")
    line4 = ax1_right.plot(plot_df["date"], plot_df["strategy_c_return"], 
                           color="#d62728", linewidth=1.5, linestyle="--", label="方法C：梯度买卖收益（%）")
    line5 = ax1_right.plot(plot_df["date"], plot_df["buy_hold_return"], 
                           color="#9467bd", linewidth=1.5, linestyle=":", label="参考：买入持有收益（%）")
    ax1_right.set_ylabel("累计收益率（%）", fontsize=12, labelpad=8)
    ax1_right.tick_params(axis='y', labelsize=10)

    # 合并图例
    lines = line1 + line2 + line3 + line4 + line5
    labels = [l.get_label() for l in lines]
    ax1_left.legend(lines, labels, loc="upper left", fontsize=9, frameon=True, shadow=True)
    ax1_left.set_title(f"红利ETF收盘价 + 三种定投策略收益对比（{CUSTOM_DAYS_RETURN}日收益差 | {CUSTOM_DAYS_MA}日均线 | 梯度买卖）", 
                       fontsize=16, pad=15, fontweight="bold", fontfamily="sans-serif")

    # ========== 下半部分：收益差 + 均线 + 梯度阈值 ==========
    ax2.plot(plot_df["date"], plot_df["diff_custom_days"] * 100, 
             color="#1f77b4", linewidth=1.5, label=f"{CUSTOM_DAYS_RETURN}日收益差（红利-中证全指）")
    ax2.plot(plot_df["date"], plot_df[f"diff_{CUSTOM_DAYS_RETURN}d_{CUSTOM_DAYS_MA}ma"] * 100, 
             color="#9467bd", linewidth=2, label=f"{CUSTOM_DAYS_RETURN}日收益差{CUSTOM_DAYS_MA}日均线")
    
    # 绘制梯度买入阈值线（蓝色系，越负颜色越深）
    buy_thresholds = [
    -0.30, -0.29, -0.28, -0.27, -0.26, -0.25, -0.24, -0.23, -0.22, -0.21, -0.20, -0.19,
    -0.18, -0.17, -0.16, -0.15, -0.14, -0.13, -0.12, -0.11,
    -0.10, -0.09, -0.08, -0.07, -0.06, -0.05, -0.04, -0.03, -0.02, -0.01
    ]
    buy_colors = [
        # 新增：-0.30~-0.19 深色系（越负越深）
        "black", "darkslategray", "dimgray", "gray", "darkgreen", "olive", "darkorange", "saddlebrown", "darkred", "maroon", "crimson", "firebrick",
        # 原有：-0.18~-0.11 色系
        "darkmagenta", "darkviolet", "indigo", "purple", "slateblue", "mediumblue", "navy", "royalblue",
        # 原有：-0.10~-0.01 色系
        "darkblue", "blue", "lightblue", "skyblue", "cyan", "teal", "green", "lime", "yellow", "orange"
    ]
    for i, threshold in enumerate(buy_thresholds):
        ax2.axhline(y=threshold*100, color=buy_colors[i], linestyle="-.", linewidth=1.0)
    
    # 绘制梯度卖出阈值线（红色系，越高颜色越深）
    sell_colors = {0.07: "orange", 0.08: "darkorange", 0.09: "red", 0.10: "darkred"}
    for threshold, ratio in SELL_GRADIENT.items():
        ax2.axhline(y=threshold*100, color=sell_colors[threshold], linestyle="--", linewidth=1.2)
    
    # 区间填充（增强视觉）
    # 低估区间（梯度多买）
    for i in range(len(buy_thresholds)):
        lower = buy_thresholds[i] * 100
        upper = buy_thresholds[i-1] * 100 if i > 0 else -20
        ax2.fill_between(plot_df["date"], lower, upper,
                         where=(plot_df["diff_custom_days"]*100 < lower) & (plot_df["diff_custom_days"]*100 >= upper),
                         color=buy_colors[i], alpha=0.05)
    
    # 高估区间（梯度止盈）
    sell_thresholds = sorted(SELL_GRADIENT.keys())
    for i, threshold in enumerate(sell_thresholds):
        lower = threshold * 100
        upper = sell_thresholds[i+1] * 100 if i+1 < len(sell_thresholds) else 20
        ax2.fill_between(plot_df["date"], lower, upper,
                         where=(plot_df["diff_custom_days"]*100 > lower) & (plot_df["diff_custom_days"]*100 <= upper),
                         color=sell_colors[threshold], alpha=0.1)
    
    ax2.set_xlabel("日期", fontsize=12, labelpad=8)
    ax2.set_ylabel(f"{CUSTOM_DAYS_RETURN}日收益差（%）", fontsize=12, labelpad=8)
    ax2.tick_params(axis='both', labelsize=10)
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc="upper right", fontsize=8, frameon=True, shadow=True, ncol=2)

    # 格式化X轴日期
    fig.autofmt_xdate()
    plt.subplots_adjust(hspace=0.1)
    plt.tight_layout()

    # 保存普通图片
    latest_date = df.iloc[-1]["date"].strftime("%Y%m%d")
    save_path = os.path.join(SAVE_DIR, f"红利ETF_三种策略_梯度买卖_{CUSTOM_DAYS_RETURN}天_{CUSTOM_DAYS_MA}天_{latest_date}.png")
    plt.savefig(save_path, bbox_inches='tight', pad_inches=0.1)
    plt.close()

    print(f"\n✅ 策略对比图表已保存：{save_path}")
    return save_path

def is_trading_day():
    """
    判断今天是否是交易日
    返回: True(交易日) / False(非交易日)
    """
    try:
        # 获取当前日期
        today = datetime.now().strftime('%Y%m%d')
        
        # 使用akshare获取交易日历
        print("正在获取交易日历...")
        trade_date_df = ak.tool_trade_date_hist_sina()
        
        # 检查今天是否在交易日历中
        today_str = datetime.now().strftime('%Y-%m-%d')
        # 统一日期格式为字符串进行比较
        trade_dates = pd.to_datetime(trade_date_df['trade_date']).dt.strftime('%Y-%m-%d').values
        is_trade_day = today_str in trade_dates
        
        if is_trade_day:
            print(f"✅ {today_str} 是交易日，继续执行数据收集")
        else:
            print(f"⏸️ {today_str} 是非交易日，跳过数据收集")
            
        return is_trade_day
        
    except Exception as e:
        print(f"⚠️ 交易日历获取失败: {e}，使用备用判断方法")
        
        # 备用方法: 基于星期判断（周六日是非交易日）
        weekday = datetime.now().weekday()
        is_trade_day = weekday < 5  # 0-4 是周一到周五
        
        if is_trade_day:
            print(f"✅ 基于星期判断：今天是工作日，假设为交易日")
        else:
            print(f"⏸️ 基于星期判断：今天是周末，假设为非交易日")
            
        return is_trade_day

# ===================== 主流程执行 =====================
if __name__ == "__main__":
    if not is_trading_day():
        print("🛑 非交易日，跳过")
    else:
        try:
            # 1. 获取数据（无缓存）
            today = datetime.now().strftime('%Y%m%d')
            ETF_END_DATE=today
            print(today)
            merge_df = get_index_data()

            # 2. 计算核心指标
            merge_df[f"return_{CUSTOM_DAYS_RETURN}d_hongli"] = merge_df["close_hongli"] / merge_df["close_hongli"].shift(CUSTOM_DAYS_RETURN) - 1
            merge_df[f"return_{CUSTOM_DAYS_RETURN}d_quanzhi"] = merge_df["close_quanzhi"] / merge_df["close_quanzhi"].shift(CUSTOM_DAYS_RETURN) - 1
            merge_df["diff_custom_days"] = merge_df[f"return_{CUSTOM_DAYS_RETURN}d_hongli"] - merge_df[f"return_{CUSTOM_DAYS_RETURN}d_quanzhi"]
            merge_df[f"diff_{CUSTOM_DAYS_RETURN}d_{CUSTOM_DAYS_MA}ma"] = merge_df["diff_custom_days"].rolling(window=CUSTOM_DAYS_MA).mean()

            # 3. 计算三种策略收益
            merge_df = calculate_all_strategies(merge_df)

            # 4. 输出信号灯状态
            latest_row = merge_df.iloc[-1]
            latest_date = latest_row["date"].strftime("%Y-%m-%d")
            latest_diff = latest_row["diff_custom_days"]
            latest_ma = latest_row[f"diff_{CUSTOM_DAYS_RETURN}d_{CUSTOM_DAYS_MA}ma"]
            signal_status, operation = get_signal_status(latest_diff)

            print("="*60)
            print(f"红利ETF信号灯（{latest_date} 更新）| 收益差{CUSTOM_DAYS_RETURN}天 | 均线{CUSTOM_DAYS_MA}天")
            print(f"基准：红利ETF(515180) vs 中证全指(000985)")
            print("="*60)
            print(f"1. 红利ETF最新收盘价：{latest_row['close_hongli']:.3f}")
            print(f"2. 中证全指最新收盘价：{latest_row['close_quanzhi']:.3f}")
            print(f"3. 红利ETF{CUSTOM_DAYS_RETURN}日收益率：{latest_row[f'return_{CUSTOM_DAYS_RETURN}d_hongli']*100:.2f}%")
            print(f"4. 中证全指{CUSTOM_DAYS_RETURN}日收益率：{latest_row[f'return_{CUSTOM_DAYS_RETURN}d_quanzhi']*100:.2f}%")
            print(f"5. {CUSTOM_DAYS_RETURN}日收益差（红利-中证）：{latest_diff*100:.2f}%")
            print(f"6. {CUSTOM_DAYS_RETURN}日收益差{CUSTOM_DAYS_MA}日均线：{latest_ma*100:.2f}%" if not pd.isna(latest_ma) else f"6. 均线数据不足（需{CUSTOM_DAYS_MA}天）")
            print(f"7. 信号灯状态：{signal_status}")
            print(f"8. 操作建议：{operation}")
            print("="*60)

            # 5. 绘制普通对比图表
            chart_path = plot_combined_chart(merge_df)

            # 6. 输出最近10天核心数据
            print("\n最近10天核心数据趋势：")
            recent_10d = merge_df.tail(10)[["date", "diff_custom_days", "strategy_a_return", "strategy_b_return", "strategy_c_return"]].copy()
            recent_10d["date"] = recent_10d["date"].dt.strftime("%Y-%m-%d")
            recent_10d["diff_custom_days"] = recent_10d["diff_custom_days"] * 100  # 转百分比
            recent_10d = recent_10d.round(2)  # 保留两位小数
            print(recent_10d.to_string(index=False))

            # 7. 获取三大指数行情并生成K线图
            print("\n📈 正在生成三大指数K线图...")
            major_indices = [
                ("000001", "上证指数"),
                ("399001", "深证成指"),
                ("399006", "创业板指")
            ]
            index_data_list = []
            for symbol, name in major_indices:
                chart_path_idx, price_idx, change_idx = plot_index_kline(symbol, name, SAVE_DIR)
                if chart_path_idx:
                    index_data_list.append({
                        "name": name,
                        "price": price_idx,
                        "change": change_idx,
                        "chart": chart_path_idx
                    })

            # 8. 生成策略内容
            print("\n📧 开始生成网页策略片段...")
            email_data = {
                "date": latest_date,
                "diff": latest_diff,
                "hongli_close": latest_row["close_hongli"],
                "quanzhi_close": latest_row["close_quanzhi"],
                "status": signal_status,
                "operation": operation
            }
            # send_strategy_email(email_data, chart_path, merge_df)  # 新增merge_df参数
            save_strategy_html_fragment(email_data, chart_path, merge_df, index_data_list)  # 保存HTML片段供网页展示


        except Exception as e:
            print(f"\n❌ 程序执行失败：{str(e)}")
            raise