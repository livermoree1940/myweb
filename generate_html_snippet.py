import json

def generate_html():
    # 1. Generate Hot Concepts HTML
    try:
        with open('hot_concepts_analysis.json', 'r', encoding='utf-8') as f:
            concept_data = json.load(f)
        
        concepts_html = ""
        for item in concept_data['hot_concepts'][:10]:
            concepts_html += f"""
                                <tr>
                                    <td>{item['rank']}</td>
                                    <td>{item['concept']}</td>
                                    <td>{item['count']}</td>
                                    <td>{item['percentage']}%</td>
                                </tr>"""
    except Exception as e:
        concepts_html = f"<!-- Error loading concepts: {e} -->"

    # 2. Generate Hot Stocks HTML
    try:
        with open('all_hot_stocks.json', 'r', encoding='utf-8') as f:
            stock_data = json.load(f)
        
        stocks_html = """
        <div class="card">
            <h2>同花顺热榜 Top 50 (实时)</h2>
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>排名</th>
                            <th>股票名称</th>
                            <th>代码</th>
                            <th>涨跌幅</th>
                            <th>热度</th>
                            <th>核心概念</th>
                            <th>热点解析</th>
                        </tr>
                    </thead>
                    <tbody>"""
        
        for stock in stock_data['hourly_normal'][:50]:
            # Determine color for change
            try:
                change_val = float(stock['change'])
                if change_val > 0:
                    change_class = "text-red"
                    change_str = f"+{change_val}%"
                elif change_val < 0:
                    change_class = "text-green"
                    change_str = f"{change_val}%"
                else:
                    change_class = ""
                    change_str = "0.00%"
            except:
                change_class = ""
                change_str = str(stock['change'])

            # Format Hot value (e.g. 8472839 -> 847.28万)
            try:
                hot_val = float(stock['hot'])
                hot_str = f"{hot_val/10000:.2f}万"
            except:
                hot_str = str(stock['hot'])
            
            # Concepts (limit length)
            concepts = stock['concept']
            if len(concepts) > 20:
                concepts = concepts[:20] + "..."

            # Analysis/Topic
            reason = stock.get('analyse_title', '') or stock.get('topic', '')
            if not reason and stock.get('analyse'):
                reason = stock['analyse'][:20] + "..."

            stocks_html += f"""
                        <tr>
                            <td>{stock['rank']}</td>
                            <td>{stock['name']}</td>
                            <td>{stock['code']}</td>
                            <td class="{change_class}">{change_str}</td>
                            <td>{hot_str}</td>
                            <td>{concepts}</td>
                            <td style="font-size: 12px; color: #666;">{reason}</td>
                        </tr>"""
        
        stocks_html += """
                    </tbody>
                </table>
            </div>
        </div>"""
        
    except Exception as e:
        stocks_html = f"<!-- Error loading stocks: {e} -->"

    # Save to files
    with open('concepts_snippet.html', 'w', encoding='utf-8') as f:
        f.write(concepts_html)
    
    with open('stocks_snippet.html', 'w', encoding='utf-8') as f:
        f.write(stocks_html)

if __name__ == "__main__":
    generate_html()
