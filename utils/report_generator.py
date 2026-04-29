# -*- coding: utf-8 -*-
"""报告生成模块"""

import pandas as pd
from io import BytesIO


def export_filtered_data(df, format_type='excel'):
    """导出筛选后的数据
    
    Args:
        df: 筛选后的数据框
        format_type: 导出格式 ('excel' 或 'csv')
    
    Returns:
        bytes: 文件内容
    """
    if format_type == 'excel':
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            if '匹配碎片数' in df.columns:
                with_frag = df[df['匹配碎片数'] > 0]
                no_frag = df[df['匹配碎片数'] == 0]
                
                if not with_frag.empty:
                    with_frag.to_excel(writer, sheet_name='有碎片匹配', index=False)
                if not no_frag.empty:
                    no_frag.to_excel(writer, sheet_name='无碎片匹配', index=False)
            else:
                df.to_excel(writer, sheet_name='筛选结果', index=False)
        
        return output.getvalue()
    
    elif format_type == 'csv':
        return df.to_csv(index=False).encode('utf-8-sig')
    
    return None


def export_summary_report(df):
    """导出摘要报告"""
    summary_cols = ['序号', '化合物中文名', '化合物英文名', '分子式', 
                    '匹配质量数', 'ppm', '综合得分', '评级名称', '匹配碎片数']
    
    available_cols = [c for c in summary_cols if c in df.columns]
    
    if '综合得分' in df.columns:
        summary_df = df[available_cols].sort_values('综合得分', ascending=False)
    else:
        summary_df = df[available_cols]
    
    return export_filtered_data(summary_df, 'excel')


def generate_html_report(df, title="化合物鉴定报告"):
    """生成HTML格式报告"""
    
    # 统计信息
    stats = {
        'total': len(df),
        'high_conf': len(df[df['评级名称'].isin(['确证级', '高置信级'])]) if '评级名称' in df.columns else 0,
        'with_frag': len(df[df['匹配碎片数'] > 0]) if '匹配碎片数' in df.columns else 0,
        'avg_ppm': df['ppm'].mean() if 'ppm' in df.columns else 0,
        'avg_score': df['综合得分'].mean() if '综合得分' in df.columns else 0
    }
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{title}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ background: #2c5f2d; color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
            .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px; }}
            .stat-card {{ background: #f0f2f6; padding: 15px; border-radius: 10px; text-align: center; }}
            .stat-number {{ font-size: 28px; font-weight: bold; color: #2c5f2d; }}
            .stat-label {{ color: #666; margin-top: 5px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #2c5f2d; color: white; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .high-confidence {{ color: #2c5f2d; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🌿 {title}</h1>
            <p>生成时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{stats['total']}</div>
                <div class="stat-label">总化合物数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{stats['high_conf']}</div>
                <div class="stat-label">高置信化合物</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{stats['with_frag']}</div>
                <div class="stat-label">有碎片证据</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{stats['avg_ppm']:.1f}</div>
                <div class="stat-label">平均ppm误差</div>
            </div>
        </div>
    """
    
    # 添加表格
    display_cols = ['化合物中文名', '分子式', 'ppm', '综合得分', '评级
