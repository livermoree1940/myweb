import akshare as ak
import json
import datetime
import jinja2
import requests
import pandas as pd
import numpy as np
import os
import glob
from typing import Dict, List, Optional, Any
import plotly.graph_objects as go

from config import (
    STOCK_CONFIG,
    INDEX_CONFIG,
    FUTURES_CONFIG,
    FILE_PATHS,
    TECHNICAL_INDICATORS,
    CHART_CONFIG,
    API_CONFIG
)


def calculate_price_change(current_price: float, previous_price: float) -> Dict[str, float]:
    """计算价格变化和涨跌幅"""
    change = round(current_price - previous_price, 2)
    change_pct = round((change / previous_price) * 100, 2) if previous_price != 0 else 0.0
    return {'change': change, 'change_pct': change_pct}


def get_stock_data(symbol: str, name: str) -> Optional[Dict[str, Any]]:
    """获取股票数据
    
    Args:
        symbol: 股票代码
        name: 股票名称
        
    Returns:
        包含股票信息的字典，如果获取失败则返回None
    """
    try:
        df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="")
        latest_row = df.iloc[-1]
        previous_row = df.iloc[-2]
        
        price = round(latest_row['收盘'], 2)
        prev_price = round(previous_row['收盘'], 2)
        change_data = calculate_price_change(price, prev_price)
        
        return {
            'name': name,
            'symbol': symbol,
            'price': price,
            'prev_price': prev_price,
            **change_data
        }
    except (KeyError, IndexError, ValueError) as e:
        print(f"获取{name}({symbol})数据失败：{e}")
        return None
    except Exception as e:
        print(f"获取{name}({symbol})时发生未知错误：{e}")
        return None


def get_index_data_from_eastmoney(symbol: str, name: str) -> Optional[Dict[str, Any]]:
    """从东方财富网获取指数数据"""
    try:
        if symbol.startswith('000'):
            df_em = ak.stock_zh_index_spot_em(symbol="上证系列指数")
        elif symbol.startswith('399'):
            df_em = ak.stock_zh_index_spot_em(symbol="深证系列指数")
        else:
            df_em = ak.stock_zh_index_spot_em(symbol="中证系列指数")
        
        index_data = df_em[df_em['代码'] == symbol]
        if not index_data.empty:
            row = index_data.iloc[0]
            price = round(float(row['最新价']), 2)
            prev_price = round(float(row['昨收']), 2)
            change = round(float(row['涨跌额']), 2)
            change_pct = round(float(row['涨跌幅']), 2)
            
            print(f"成功从东方财富网获取{name}({symbol})数据")
            return {
                'name': name,
                'symbol': symbol,
                'price': price,
                'prev_price': prev_price,
                'change': change,
                'change_pct': change_pct
            }
    except Exception as e:
        print(f"从东方财富网获取{name}({symbol})失败：{e}")
    return None


def get_index_data_from_sina(symbol: str, name: str) -> Optional[Dict[str, Any]]:
    """从新浪财经获取指数数据"""
    try:
        df_sina = ak.stock_zh_index_spot_sina()
        sina_symbol = f"sh{symbol}" if symbol.startswith('000') else f"sz{symbol}"
        index_data_sina = df_sina[df_sina['代码'] == sina_symbol]
        
        if not index_data_sina.empty:
            row = index_data_sina.iloc[0]
            price = round(float(row['最新价']), 2)
            prev_price = round(float(row['昨收']), 2)
            change = round(float(row['涨跌额']), 2)
            change_pct = round(float(row['涨跌幅']), 2)
            
            print(f"成功从新浪财经获取{name}({symbol})数据")
            return {
                'name': name,
                'symbol': symbol,
                'price': price,
                'prev_price': prev_price,
                'change': change,
                'change_pct': change_pct
            }
    except Exception as e:
        print(f"从新浪财经获取{name}({symbol})失败：{e}")
    return None


def get_index_data_from_history(symbol: str, name: str) -> Optional[Dict[str, Any]]:
    """从历史数据接口获取指数数据"""
    try:
        df_daily = ak.stock_zh_index_daily(symbol=symbol)
        
        if 'date' in df_daily.columns:
            latest_row = df_daily.iloc[-1]
            previous_row = df_daily.iloc[-2]
            price = round(latest_row['close'], 2)
            prev_price = round(previous_row['close'], 2)
        else:
            latest_row = df_daily.iloc[-1]
            previous_row = df_daily.iloc[-2]
            price = round(latest_row[df_daily.columns[3]], 2)
            prev_price = round(previous_row[df_daily.columns[3]], 2)
        
        change_data = calculate_price_change(price, prev_price)
        
        print(f"成功从历史数据接口获取{name}({symbol})数据")
        return {
            'name': name,
            'symbol': symbol,
            'price': price,
            'prev_price': prev_price,
            **change_data
        }
    except Exception as e:
        print(f"从历史数据接口获取{name}({symbol})失败：{e}")
    return None





def get_index_data(symbol: str, name: str) -> Optional[Dict[str, Any]]:
    """获取指数数据，尝试多个数据源
    
    Args:
        symbol: 指数代码
        name: 指数名称
        
    Returns:
        包含指数信息的字典，如果获取失败则返回None
    """
    print(f"尝试获取{name}({symbol})数据...")
    
    data = get_index_data_from_eastmoney(symbol, name)
    if data:
        return data
    
    data = get_index_data_from_sina(symbol, name)
    if data:
        return data
    
    data = get_index_data_from_history(symbol, name)
    if data:
        return data
    
    print(f"所有数据源均失败，返回None")
    return None


def get_baidu_kline_data(code: str, is_futures: bool) -> Optional[pd.DataFrame]:
    """从百度接口获取K线数据
    
    Args:
        code: 代码
        is_futures: 是否为期货
        
    Returns:
        包含时间和收盘价的DataFrame
    """
    try:
        f_type = "true" if is_futures else "false"
        url = f"https://finance.pae.baidu.com/selfselect/getstockquotation?all=1&code={code}&isIndex={not is_futures}&isBk=false&isBlock=false&isFutures={f_type}&isStock=false&newFormat=1&ktype=1&market_type=ab&group=quotation_futures_kline&finClientType=pc"
        
        response = requests.get(url, headers=API_CONFIG['headers'], timeout=API_CONFIG['timeout'])
        response.raise_for_status()
        res_json = response.json()
        
        raw_str = res_json['Result']['newMarketData']['marketData']
        keys = res_json['Result']['newMarketData']['keys']
        
        rows = [line.split(',') for line in raw_str.split(';') if line]
        df = pd.DataFrame(rows, columns=keys)
        df['time'] = pd.to_datetime(df['time'])
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        
        return df[['time', 'close']]
    except Exception as e:
        print(f"从百度接口获取{code}数据失败：{e}")
        return None


def get_index_futures_data(spot_code: str, future_code: str, index_name: str) -> Optional[pd.DataFrame]:
    """获取指数现货和期货数据并计算基差
    
    Args:
        spot_code: 现货代码
        future_code: 期货代码
        index_name: 指数名称
        
    Returns:
        包含基差和技术指标的DataFrame
    """
    try:
        df_spot = get_baidu_kline_data(spot_code, is_futures=False)
        df_future = get_baidu_kline_data(future_code, is_futures=True)
        
        if df_spot is None or df_future is None:
            return None
        
        df_basis = pd.merge(df_future, df_spot, on='time', suffixes=('_fut', '_spot'))
        df_basis['basis'] = df_basis['close_fut'] - df_basis['close_spot']
        
        ma60_window = TECHNICAL_INDICATORS['MA60_WINDOW']
        bollinger_window = TECHNICAL_INDICATORS['BOLLINGER_WINDOW']
        std_multiplier = TECHNICAL_INDICATORS['STD_MULTIPLIER']
        
        df_basis['ma60'] = df_basis['basis'].rolling(window=ma60_window).mean()
        df_basis['mid'] = df_basis['basis'].rolling(window=bollinger_window).mean()
        df_basis['std'] = df_basis['basis'].rolling(window=bollinger_window).std()
        df_basis['upper'] = df_basis['mid'] + std_multiplier * df_basis['std']
        df_basis['lower'] = df_basis['mid'] - std_multiplier * df_basis['std']
        
        return df_basis
    except Exception as e:
        print(f"获取{index_name}数据时出错: {e}")
        return None


def create_basis_chart(df_basis: pd.DataFrame, index_name: str, output_file: str) -> bool:
    """创建基差交互式图表
    
    Args:
        df_basis: 基差数据DataFrame
        index_name: 指数名称
        output_file: 输出文件路径
        
    Returns:
        是否成功创建图表
    """
    try:
        if df_basis is None or len(df_basis) < 20:
            return False
        
        fig = go.Figure()
        
        fig.update_layout(
            title=f'{index_name}股指期货基差分析 (含MA60及布林带)',
            xaxis_title='时间',
            yaxis_title='基差',
            width=CHART_CONFIG['width'],
            height=CHART_CONFIG['height'],
            template=CHART_CONFIG['template'],
            hovermode='x unified'
        )
        
        fig.add_trace(go.Scatter(
            x=df_basis['time'],
            y=df_basis['basis'],
            name=f'{index_name}基差',
            line=dict(color='#5386E4', width=1.5),
            opacity=0.9
        ))
        
        fig.add_trace(go.Scatter(
            x=df_basis['time'],
            y=df_basis['ma60'],
            name='基差 60日均线',
            line=dict(color='#F49E4C', width=2, dash='solid'),
            opacity=0.8
        ))
        
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
        
        fig.add_hline(
            y=0,
            line=dict(color='black', width=1, dash='solid'),
            name='基差=0线'
        )
        
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
        
        fig.write_html(
            output_file,
            include_plotlyjs=CHART_CONFIG['include_plotlyjs'],
            full_html=CHART_CONFIG['full_html']
        )
        
        return True
    except Exception as e:
        print(f"创建{index_name}图表时出错: {e}")
        return False


def read_chart_html(chart_file: str) -> str:
    """读取图表HTML文件
    
    Args:
        chart_file: 图表文件路径
        
    Returns:
        HTML内容字符串
    """
    try:
        if os.path.exists(chart_file):
            with open(chart_file, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception as e:
        print(f"读取{chart_file}时出错: {e}")
    return ""


def process_index_futures(futures_key: str) -> tuple[bool, str]:
    """处理指数期货数据并创建图表
    
    Args:
        futures_key: 期货配置键名
        
    Returns:
        (是否成功, 图表HTML内容)
    """
    config = FUTURES_CONFIG[futures_key]
    has_chart = False
    chart_html = ""
    
    try:
        print(f"正在获取{config['name']}基差数据...")
        df_basis = get_index_futures_data(config['spot_code'], config['future_code'], config['name'])
        
        if df_basis is not None:
            print(f"正在创建{config['name']}基差图表...")
            has_chart = create_basis_chart(df_basis, config['name'], config['chart_file'])
            
            if has_chart:
                print(f"{config['name']}基差图表创建成功！")
                chart_html = read_chart_html(config['chart_file'])
            else:
                print(f"{config['name']}基差图表创建失败！")
        else:
            print(f"未能获取{config['name']}数据！")
    except Exception as e:
        print(f"处理{config['name']}数据时出错: {e}")
        has_chart = False
    
    # 如果没有获取到新数据，但是之前已经生成了图表文件，那么使用之前的图表文件
    if not has_chart and not chart_html:
        chart_html = read_chart_html(config['chart_file'])
        if chart_html:
            print(f"使用之前生成的{config['name']}基差图表文件！")
            has_chart = True
    
    return has_chart, chart_html


def get_latest_strategy_png() -> Optional[str]:
    """获取最新的红利ETF策略PNG图片
    
    Returns:
        最新的PNG文件路径
    """
    try:
        png_files = glob.glob(FILE_PATHS['strategy_png_pattern'])
        png_files.sort(key=os.path.getmtime, reverse=True)
        return png_files[0] if png_files else None
    except Exception as e:
        print(f"查找策略图片时出错: {e}")
        return None


def read_strategy_fragment() -> str:
    """读取策略HTML片段
    
    Returns:
        HTML片段内容
    """
    try:
        if os.path.exists(FILE_PATHS['strategy_fragment']):
            with open(FILE_PATHS['strategy_fragment'], 'r', encoding='utf-8') as f:
                return f.read()
    except Exception as e:
        print(f"读取策略片段时出错: {e}")
    return ""


def generate_html(date: str, stock_data: Dict, indices: List[Dict], 
                  has_hs300_chart: bool, hs300_chart_html: str,
                  has_zz1000_chart: bool, zz1000_chart_html: str,
                  latest_png: Optional[str], strategy_html: str,
                  hot_concepts: Optional[Dict[str, Any]],
                  stocks_by_concept: Optional[Dict[str, Any]],
                  recent_trading_data: Optional[List[Dict[str, Any]]],
                  stock_kline_html: str) -> str:
    """生成HTML页面
    
    Args:
        date: 日期
        stock_data: 股票数据
        indices: 指数数据列表
        has_hs300_chart: 是否有沪深300图表
        hs300_chart_html: 沪深300图表HTML
        has_zz1000_chart: 是否有中证1000图表
        zz1000_chart_html: 中证1000图表HTML
        latest_png: 最新策略图片路径
        strategy_html: 策略HTML片段
        hot_concepts: 热点概念数据
        stocks_by_concept: 按概念分组的个股数据
        recent_trading_data: 最近交易日数据
        stock_kline_html: 股票日K线图HTML
        
    Returns:
        生成的HTML字符串
    """
    try:
        template_loader = jinja2.FileSystemLoader(searchpath=FILE_PATHS['template_dir'])
        template_env = jinja2.Environment(loader=template_loader)
        template = template_env.get_template('index.html')
        
        return template.render(
            date=date,
            stock=stock_data,
            indices=indices,
            has_hs300_chart=has_hs300_chart,
            hs300_chart_html=hs300_chart_html,
            has_zz1000_chart=has_zz1000_chart,
            zz1000_chart_html=zz1000_chart_html,
            latest_png=latest_png,
            strategy_html=strategy_html,
            hot_concepts=hot_concepts,
            stocks_by_concept=stocks_by_concept,
            recent_trading_data=recent_trading_data,
            stock_kline_html=stock_kline_html
        )
    except Exception as e:
        print(f"生成HTML时出错: {e}")
        return ""


def save_json(data: Dict, filepath: str) -> bool:
    """保存JSON数据
    
    Args:
        data: 要保存的数据
        filepath: 文件路径
        
    Returns:
        是否成功保存
    """
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"保存JSON文件{filepath}时出错: {e}")
        return False


def save_html(html_content: str, filepath: str) -> bool:
    """保存HTML文件
    
    Args:
        html_content: HTML内容
        filepath: 文件路径
        
    Returns:
        是否成功保存
    """
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        return True
    except Exception as e:
        print(f"保存HTML文件{filepath}时出错: {e}")
        return False


def get_hot_concepts() -> Optional[Dict[str, Any]]:
    """获取热点概念数据
    
    Returns:
        热点概念分析数据，如果文件不存在则返回None
    """
    try:
        if os.path.exists('hot_concepts_analysis.json'):
            with open('hot_concepts_analysis.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    except Exception as e:
        print(f"读取热点概念数据失败: {e}")
        return None


def get_stocks_by_concept() -> Optional[Dict[str, Any]]:
    """获取按概念分组的个股数据
    
    Returns:
        按概念分组的个股数据，如果文件不存在则返回None
    """
    try:
        if os.path.exists('all_hot_stocks.json'):
            with open('all_hot_stocks.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 收集所有股票
            all_stocks = []
            for key, stocks_list in data.items():
                if isinstance(stocks_list, list):
                    all_stocks.extend(stocks_list)
            
            # 提取所有概念并统计
            concept_stocks = {}
            for stock in all_stocks:
                if 'concept' in stock and stock['concept']:
                    concepts = [c.strip() for c in stock['concept'].split() if c.strip()]
                    for concept in concepts:
                        if concept not in concept_stocks:
                            concept_stocks[concept] = []
                        # 只添加唯一的股票（根据代码）
                        if not any(s['code'] == stock['code'] for s in concept_stocks[concept]):
                            concept_stocks[concept].append(stock)
            
            # 按股票数量排序概念
            sorted_concepts = sorted(concept_stocks.items(), key=lambda x: len(x[1]), reverse=True)
            
            return {
                'total_stocks': len(all_stocks),
                'total_concepts': len(concept_stocks),
                'sorted_concepts': [{'concept': c, 'stocks': s} for c, s in sorted_concepts]
            }
        return None
    except Exception as e:
        print(f"读取个股数据失败: {e}")
        return None


def get_recent_trading_days_data(symbol: str, name: str, days: int = 20) -> Optional[List[Dict[str, Any]]]:
    """获取最近N个交易日的数据
    
    Args:
        symbol: 股票代码
        name: 股票名称
        days: 交易日天数
        
    Returns:
        包含最近交易日数据的列表
    """
    try:
        df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="")
        # 获取最近N个交易日的数据
        recent_data = []
        
        # 确保有足够的数据
        start_idx = max(0, len(df) - days)
        
        for i in range(start_idx, len(df)):
            row = df.iloc[i]
            
            # 尝试获取日期
            if '日期' in df.columns:
                date = row['日期']
            elif 'date' in df.columns:
                date = row['date']
            else:
                # 如果没有日期列，使用索引
                date = str(row.name)
            
            # 计算涨跌幅
            close = round(row['收盘'], 2)
            open_price = round(row['开盘'], 2)
            high = round(row['最高'], 2)
            low = round(row['最低'], 2)
            volume = int(row['成交量'])
            amount = round(row['成交额'], 2)
            
            # 计算涨跌幅
            change = round(close - open_price, 2)
            change_pct = round((change / open_price) * 100, 2) if open_price != 0 else 0.0
            
            recent_data.append({
                'date': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'change': change,
                'change_pct': change_pct,
                'volume': volume,
                'amount': amount
            })
        
        return recent_data
    except Exception as e:
        print(f"获取{name}最近{days}个交易日数据失败: {e}")
        return None


def create_stock_kline_chart(symbol: str, name: str, days: int = 180) -> str:
    """创建股票日k图
    
    Args:
        symbol: 股票代码
        name: 股票名称
        days: 显示的交易日天数
        
    Returns:
        生成的HTML图表字符串
    """
    try:
        df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="")
        
        # 获取最近N个交易日的数据
        start_idx = max(0, len(df) - days)
        df_recent = df.iloc[start_idx:]
        
        # 准备数据
        dates = []
        opens = []
        highs = []
        lows = []
        closes = []
        
        for i in range(len(df_recent)):
            row = df_recent.iloc[i]
            date = row.name.strftime('%Y-%m-%d') if hasattr(row.name, 'strftime') else str(row.name)
            dates.append(date)
            opens.append(round(row['开盘'], 2))
            highs.append(round(row['最高'], 2))
            lows.append(round(row['最低'], 2))
            closes.append(round(row['收盘'], 2))
        
        # 创建K线图
        fig = go.Figure(data=[go.Candlestick(
            x=dates,
            open=opens,
            high=highs,
            low=lows,
            close=closes,
            increasing_line_color='#27ae60',
            decreasing_line_color='#e74c3c'
        )])
        
        # 更新布局
        fig.update_layout(
            title=f'{name}({symbol}) 日K线图',
            xaxis_title='日期',
            yaxis_title='价格',
            width=1000,
            height=600,
            template='plotly_white',
            hovermode='x unified'
        )
        
        # 添加成交量
        volumes = [int(row['成交量']) for _, row in df_recent.iterrows()]
        fig.add_trace(go.Bar(
            x=dates,
            y=volumes,
            name='成交量',
            yaxis='y2',
            marker_color=['#27ae60' if closes[i] >= opens[i] else '#e74c3c' for i in range(len(closes))],
            opacity=0.6
        ))
        
        # 更新Y轴
        fig.update_layout(
            yaxis2=dict(
                title='成交量',
                overlaying='y',
                side='right',
                showgrid=False
            )
        )
        
        # 更新X轴
        fig.update_xaxes(
            rangeslider_visible=False,
            rangeselector=dict(
                buttons=list([
                    dict(count=30, label="30天", step="day", stepmode="backward"),
                    dict(count=60, label="60天", step="day", stepmode="backward"),
                    dict(count=90, label="90天", step="day", stepmode="backward"),
                    dict(count=180, label="180天", step="day", stepmode="backward"),
                    dict(step="all")
                ])
            )
        )
        
        # 转换为HTML
        return fig.to_html(
            include_plotlyjs='cdn',
            full_html=False
        )
    except Exception as e:
        print(f"创建{name}日K线图失败: {e}")
        return ""


def main():
    """主函数"""
    print("开始更新股票行情数据...")
    
    date = datetime.datetime.now().strftime('%Y-%m-%d')
    
    stock_config = STOCK_CONFIG['main_stock']
    stock_data = get_stock_data(stock_config['symbol'], stock_config['name'])
    
    # 检查关键数据是否获取成功
    if not stock_data:
        print("❌ 核心股票数据获取失败，程序终止！")
        return False
    
    # 获取最近20个交易日数据
    recent_trading_data = get_recent_trading_days_data(stock_config['symbol'], stock_config['name'])
    
    # 创建长江电力日K线图
    stock_kline_html = create_stock_kline_chart(stock_config['symbol'], stock_config['name'])
    
    # 获取指数数据
    indices = []
    for idx in INDEX_CONFIG:
        idx_data = get_index_data(idx['symbol'], idx['name'])
        if not idx_data:
            print(f"❌ 指数 {idx['name']} 数据获取失败，程序终止！")
            return False
        indices.append(idx_data)
    
    # 获取基差图表
    has_hs300_chart, hs300_chart_html = process_index_futures('hs300')
    has_zz1000_chart, zz1000_chart_html = process_index_futures('zz1000')
    
    # 检查基差图表是否获取成功
    if not has_hs300_chart or not has_zz1000_chart:
        print("❌ 基差图表获取失败，程序终止！")
        return False
    
    data = {
        'date': date,
        'stock': stock_data,
        'indices': indices,
        'has_hs300_chart': has_hs300_chart,
        'has_zz1000_chart': has_zz1000_chart
    }
    save_json(data, FILE_PATHS['price_json'])
    
    latest_png = get_latest_strategy_png()
    strategy_html = read_strategy_fragment()
    
    # 获取热点概念数据
    hot_concepts = get_hot_concepts()
    # 获取按概念分组的个股数据
    stocks_by_concept = get_stocks_by_concept()
    
    html = generate_html(
        date=date,
        stock_data=stock_data,
        indices=indices,
        has_hs300_chart=has_hs300_chart,
        hs300_chart_html=hs300_chart_html,
        has_zz1000_chart=has_zz1000_chart,
        zz1000_chart_html=zz1000_chart_html,
        latest_png=latest_png,
        strategy_html=strategy_html,
        hot_concepts=hot_concepts,
        stocks_by_concept=stocks_by_concept,
        recent_trading_data=recent_trading_data,
        stock_kline_html=stock_kline_html
    )
    
    if html:
        save_html(html, FILE_PATHS['index_html'])
        print(f"✅ 数据更新完成！HTML文件已保存到 {FILE_PATHS['index_html']}")
        return True
    else:
        print("❌ HTML生成失败！")
        return False


if __name__ == '__main__':
    success = main()
    if not success:
        print("❌ 程序执行失败，退出！")
        import sys
        sys.exit(1)