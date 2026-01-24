"""配置文件 - 管理股票/指数代码和文件路径"""

# 股票配置
STOCK_CONFIG = {
    'main_stock': {
        'symbol': '600900',
        'name': '长江电力',
        'default_price': 26.80
    }
}

# 指数配置
INDEX_CONFIG = [
    {'symbol': '000001', 'name': '上证指数'},
    {'symbol': '399006', 'name': '创业板指'},
    {'symbol': '000688', 'name': '科创50'},
    {'symbol': '000985', 'name': '中证全指'}
]

# 股指期货配置
FUTURES_CONFIG = {
    'hs300': {
        'spot_code': '000300',
        'future_code': 'IF888',
        'name': '沪深300',
        'chart_file': 'hs300_basis_embed.html'
    },
    'zz1000': {
        'spot_code': '000852',
        'future_code': 'IC888',
        'name': '中证1000',
        'chart_file': 'zz1000_basis_embed.html'
    }
}



# 文件路径配置
FILE_PATHS = {
    'price_json': 'price.json',
    'index_html': 'index.html',
    'strategy_fragment': 'strategy_fragment.html',
    'strategy_png_pattern': '红利ETF_三种策略_梯度买卖_*_*.png',
    'template_dir': 'templates',
    'template_file': 'templates/index.html'
}

# 技术指标常量
TECHNICAL_INDICATORS = {
    'MA60_WINDOW': 60,
    'BOLLINGER_WINDOW': 20,
    'STD_MULTIPLIER': 2
}

# 图表配置
CHART_CONFIG = {
    'width': 1000,
    'height': 600,
    'template': 'plotly_white',
    'include_plotlyjs': 'cdn',
    'full_html': False
}

# API 配置
API_CONFIG = {
    'timeout': 10,
    'headers': {
        'User-Agent': 'Mozilla/5.0',
        'Referer': 'https://gushitong.baidu.com/'
    }
}
