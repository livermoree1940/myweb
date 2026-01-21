# -*- coding: utf-8 -*-
"""
同花顺热榜爬虫与热点概念分析
功能：
1. 获取同花顺热榜数据（小时级和日级）
2. 分析热点概念
3. 生成详细分析报告
"""

import requests
import json
import os
from collections import Counter

class THSHotSpider:
    """同花顺热榜爬虫"""
    
    def __init__(self):
        self.api_endpoints = {
            "hourly_normal": "https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/stock?stock_type=a&type=hour&list_type=normal",
            "hourly_skyrocket": "https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/stock?stock_type=a&type=hour&list_type=skyrocket",
            "daily_tech": "https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/stock?stock_type=a&type=day&list_type=tech",
            "daily_value": "https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/stock?stock_type=a&type=day&list_type=value",
            "daily_trend": "https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/stock?stock_type=a&type=day&list_type=trend",
            "new_stock": "https://eq.10jqka.com.cn/open/api/hot_list/rank/v1/new_stock.txt"
        }
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive"
        }
        
        self.proxies = {
            'http': None,
            'https': None
        }
    
    def fetch_api_data(self, url, name):
        """获取API数据"""
        try:
            print(f"\n=== 获取 {name} 数据 ===")
            response = requests.get(url, headers=self.headers, verify=False, proxies=self.proxies, timeout=10)
            
            if response.status_code == 200:
                if url.endswith('.txt'):
                    # 处理文本格式的响应
                    content = response.text
                    print(f"响应长度: {len(content)}")
                    # 保存文本响应
                    with open(f'{name}_response.txt', 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"已保存: {name}_response.txt")
                    return content
                else:
                    # 处理JSON格式的响应
                    data = response.json()
                    print(f"JSON keys: {list(data.keys()) if isinstance(data, dict) else 'Array'}")
                    # 保存JSON响应
                    with open(f'{name}_response.json', 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    print(f"已保存: {name}_response.json")
                    return data
            else:
                print(f"错误: {response.status_code}")
                return None
        except Exception as e:
            print(f"异常: {e}")
            return None
    
    def parse_stock_data(self, data, name):
        """解析股票数据"""
        if not data or 'data' not in data:
            print(f"{name} 数据格式不正确")
            return []
        
        # 从data['stock_list']中获取股票列表
        stock_list = data['data'].get('stock_list', [])
        print(f"找到 {len(stock_list)} 个 {name} 热股")
        
        parsed_stocks = []
        for stock in stock_list:
            # 使用stock中的order字段作为排名
            rank = stock.get('order', len(parsed_stocks) + 1)
            
            # 提取概念标签
            concept_tags = []
            if 'tag' in stock and 'concept_tag' in stock['tag']:
                concept_tags = stock['tag']['concept_tag']
            concept_str = ' '.join(concept_tags)
            
            # 处理topic字段
            topic_title = ''
            if 'topic' in stock and stock['topic'] is not None:
                topic_title = stock['topic'].get('title', '')
            
            parsed_stock = {
                "rank": rank,
                "name": stock.get('name', ''),
                "code": stock.get('code', ''),
                "change": stock.get('rise_and_fall', ''),
                "hot": stock.get('rate', ''),
                "concept": concept_str,
                "analyse": stock.get('analyse', ''),
                "analyse_title": stock.get('analyse_title', ''),
                "topic": topic_title
            }
            parsed_stocks.append(parsed_stock)
            # 打印前几个股票
            if rank <= 5:
                print(f"排名: {rank}")
                print(f"  名称: {parsed_stock['name']}")
                print(f"  代码: {parsed_stock['code']}")
                print(f"  涨跌幅: {parsed_stock['change']}")
                print(f"  热度: {parsed_stock['hot']}")
                print(f"  概念: {parsed_stock['concept']}")
                if parsed_stock['topic']:
                    print(f"  热点: {parsed_stock['topic']}")
                print("---")
        
        # 保存解析后的数据
        with open(f'{name}_parsed.json', 'w', encoding='utf-8') as f:
            json.dump(parsed_stocks, f, ensure_ascii=False, indent=2)
        print(f"解析后的数据已保存: {name}_parsed.json")
        
        return parsed_stocks
    
    def parse_new_stock_data(self, content):
        """解析新股数据"""
        lines = content.strip().split('\n')
        stocks = []
        
        for i, line in enumerate(lines, 1):
            if line:
                parts = line.split('|')
                if len(parts) >= 5:
                    stock = {
                        "rank": i,
                        "name": parts[0],
                        "code": parts[1],
                        "pe": parts[2],
                        "hot": parts[3],
                        "market": parts[4]
                    }
                    stocks.append(stock)
                    # 打印前几个股票
                    if i <= 5:
                        print(f"排名: {i}")
                        print(f"  名称: {stock['name']}")
                        print(f"  代码: {stock['code']}")
                        print(f"  市盈率: {stock['pe']}")
                        print(f"  热度: {stock['hot']}")
                        print(f"  市场: {stock['market']}")
                        print("---")
        
        print(f"找到 {len(stocks)} 个新股")
        
        # 保存解析后的数据
        with open('new_stock_parsed.json', 'w', encoding='utf-8') as f:
            json.dump(stocks, f, ensure_ascii=False, indent=2)
        print("解析后的数据已保存: new_stock_parsed.json")
        
        return stocks
    
    def run(self):
        """运行爬虫"""
        print("开始获取同花顺热榜数据...")
        
        # 获取并解析各个API的数据
        results = {}
        
        # 获取小时级普通热股
        hourly_normal_data = self.fetch_api_data(self.api_endpoints["hourly_normal"], "hourly_normal")
        if hourly_normal_data and not isinstance(hourly_normal_data, str):
            results["hourly_normal"] = self.parse_stock_data(hourly_normal_data, "hourly_normal")
        
        # 获取小时级飙升热股
        hourly_skyrocket_data = self.fetch_api_data(self.api_endpoints["hourly_skyrocket"], "hourly_skyrocket")
        if hourly_skyrocket_data and not isinstance(hourly_skyrocket_data, str):
            results["hourly_skyrocket"] = self.parse_stock_data(hourly_skyrocket_data, "hourly_skyrocket")
        
        # 获取日级技术热股
        daily_tech_data = self.fetch_api_data(self.api_endpoints["daily_tech"], "daily_tech")
        if daily_tech_data and not isinstance(daily_tech_data, str):
            results["daily_tech"] = self.parse_stock_data(daily_tech_data, "daily_tech")
        
        # 获取日级价值热股
        daily_value_data = self.fetch_api_data(self.api_endpoints["daily_value"], "daily_value")
        if daily_value_data and not isinstance(daily_value_data, str):
            results["daily_value"] = self.parse_stock_data(daily_value_data, "daily_value")
        
        # 获取日级趋势热股
        daily_trend_data = self.fetch_api_data(self.api_endpoints["daily_trend"], "daily_trend")
        if daily_trend_data and not isinstance(daily_trend_data, str):
            results["daily_trend"] = self.parse_stock_data(daily_trend_data, "daily_trend")
        
        # 获取新股数据
        new_stock_data = self.fetch_api_data(self.api_endpoints["new_stock"], "new_stock")
        if new_stock_data and isinstance(new_stock_data, str):
            results["new_stock"] = self.parse_new_stock_data(new_stock_data)
        
        # 保存所有结果
        with open('all_hot_stocks.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print("\n所有热榜数据已保存: all_hot_stocks.json")
        
        print("\n热榜数据获取完成!")
        return results

class HotConceptAnalyzer:
    """热点概念分析器"""
    
    def __init__(self):
        self.parsed_files = [
            'hourly_normal_parsed.json',
            'hourly_skyrocket_parsed.json',
            'daily_value_parsed.json',
            'daily_trend_parsed.json'
        ]
    
    def load_stocks_from_file(self, file_path):
        """从文件中加载股票数据"""
        if not os.path.exists(file_path):
            print(f"文件不存在: {file_path}")
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except Exception as e:
            print(f"加载文件失败 {file_path}: {e}")
            return []
    
    def extract_concepts(self, stocks):
        """从股票数据中提取概念"""
        concepts = []
        for stock in stocks:
            if 'concept' in stock and stock['concept']:
                # 分割概念字符串，去除空字符串
                stock_concepts = [concept.strip() for concept in stock['concept'].split() if concept.strip()]
                concepts.extend(stock_concepts)
        return concepts
    
    def generate_markdown_report(self, report, sorted_concepts):
        """生成Markdown格式的分析报告"""
        markdown_content = f"""
# 同花顺热榜热点概念分析报告

## 分析时间
2026年1月21日

## 数据概况
- **总股票数量**: {report['total_stocks']}
- **总概念数量**: {report['total_concepts']}
- **不同概念数量**: {report['unique_concepts']}

## 概念分布
- **1-5次**: {report['concept_distribution']['1-5次']}个概念
- **6-10次**: {report['concept_distribution']['6-10次']}个概念
- **11-20次**: {report['concept_distribution']['11-20次']}个概念
- **20次以上**: {report['concept_distribution']['20次以上']}个概念

## 热点概念Top 30

| 排名 | 概念 | 出现次数 | 占比 |
|------|------|---------|------|
"""
        
        for i, (concept, count) in enumerate(sorted_concepts[:30], 1):
            percentage = round(count / report['total_stocks'] * 100, 2)
            markdown_content += f"| {i} | {concept} | {count} | {percentage}% |\n"
        
        markdown_content += "\n## 热门概念分析\n\n"    
        # 分析前5个热点概念
        if sorted_concepts:
            top_concepts = sorted_concepts[:5]
            markdown_content += "### 最热门的5个概念\n\n"
            for i, (concept, count) in enumerate(top_concepts, 1):
                percentage = round(count / report['total_stocks'] * 100, 2)
                markdown_content += f"{i}. **{concept}**: {count}次出现，占比{percentage}%\n"
        
        markdown_content += "\n### 趋势分析\n\n"
        markdown_content += "- 商业航天、人工智能相关概念持续活跃\n"
        markdown_content += "- 新能源、特高压等传统热点仍有较高关注度\n"
        markdown_content += "- Sora概念(文生视频)等新兴概念开始崛起\n"
        markdown_content += "\n### 投资建议\n\n"
        markdown_content += "- 关注热点概念的持续性和基本面支撑\n"
        markdown_content += "- 避免盲目追高，注意风险控制\n"
        markdown_content += "- 关注概念叠加效应，寻找多概念共振的标的\n"
        
        with open('hot_concepts_analysis.md', 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        print("分析报告已保存: hot_concepts_analysis.md")
    
    def analyze(self):
        """分析热点概念"""
        print("\n开始分析热点概念...")
        
        # 加载所有股票数据
        all_stocks = []
        for file_path in self.parsed_files:
            stocks = self.load_stocks_from_file(file_path)
            all_stocks.extend(stocks)
        
        print(f"总股票数量: {len(all_stocks)}")
        
        # 提取所有概念
        all_concepts = self.extract_concepts(all_stocks)
        print(f"总概念数量: {len(all_concepts)}")
        
        # 统计概念出现次数
        concept_counter = Counter(all_concepts)
        print(f"不同概念数量: {len(concept_counter)}")
        
        # 排序概念（按出现次数降序）
        sorted_concepts = concept_counter.most_common()
        
        # 打印前20个热点概念
        print("\n=== 热点概念排名 ===")
        print("排名\t概念\t\t\t出现次数")
        print("-" * 50)
        
        for i, (concept, count) in enumerate(sorted_concepts[:20], 1):
            # 格式化输出，确保对齐
            print(f"{i}\t{concept:<20}\t{count}")
        
        # 生成详细分析报告
        report = {
            "total_stocks": len(all_stocks),
            "total_concepts": len(all_concepts),
            "unique_concepts": len(concept_counter),
            "hot_concepts": [
                {
                    "rank": i + 1,
                    "concept": concept,
                    "count": count,
                    "percentage": round(count / len(all_stocks) * 100, 2)
                }
                for i, (concept, count) in enumerate(sorted_concepts[:30])
            ],
            "concept_distribution": {
                "1-5次": len([c for c, cnt in concept_counter.items() if 1 <= cnt <= 5]),
                "6-10次": len([c for c, cnt in concept_counter.items() if 6 <= cnt <= 10]),
                "11-20次": len([c for c, cnt in concept_counter.items() if 11 <= cnt <= 20]),
                "20次以上": len([c for c, cnt in concept_counter.items() if cnt > 20])
            }
        }
        
        # 保存分析报告
        with open('hot_concepts_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print("\n分析报告已保存: hot_concepts_analysis.json")
        
        # 生成Markdown分析报告
        self.generate_markdown_report(report, sorted_concepts)
        
        return report

def main():
    """主函数"""
    print("=" * 60)
    print("同花顺热榜爬虫与热点概念分析")
    print("=" * 60)
    
    # 运行爬虫
    spider = THSHotSpider()
    spider.run()
    
    # 运行分析
    analyzer = HotConceptAnalyzer()
    analyzer.analyze()
    
    print("\n" + "=" * 60)
    print("任务完成！")
    print("\n生成的文件：")
    print("1. 热榜数据文件：*.json, *.txt")
    print("2. 热点概念分析：hot_concepts_analysis.json")
    print("3. 分析报告：hot_concepts_analysis.md")
    print("=" * 60)

if __name__ == "__main__":
    main()
