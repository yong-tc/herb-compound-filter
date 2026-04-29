# -*- coding: utf-8 -*-
"""
中药化合物鉴定报告筛选系统
支持所有药材的通用筛选平台
"""

import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import base64
from datetime import datetime
import re

# 尝试导入plotly，如果没有安装则使用备用方案
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    # 备用：使用matplotlib
    try:
        import matplotlib.pyplot as plt
        MATPLOTLIB_AVAILABLE = True
    except ImportError:
        MATPLOTLIB_AVAILABLE = False

# 页面配置
st.set_page_config(
    page_title="中药化合物鉴定报告筛选系统",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #2c5f2d 0%, #97bc62 100%);
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
    }
    .main-header h1 {
        color: white;
        margin: 0;
    }
    .main-header p {
        color: #e8f5e9;
        margin: 0.5rem 0 0 0;
    }
    .stat-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stat-number {
        font-size: 2rem;
        font-weight: bold;
        color: #2c5f2d;
    }
    .stat-label {
        font-size: 0.9rem;
        color: #666;
    }
    .filter-section {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .success-badge {
        background-color: #d4edda;
        color: #155724;
        padding: 0.2rem 0.5rem;
        border-radius: 5px;
        font-size: 0.8rem;
    }
    .warning-badge {
        background-color: #fff3cd;
        color: #856404;
        padding: 0.2rem 0.5rem;
        border-radius: 5px;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """初始化session state"""
    if 'data' not in st.session_state:
        st.session_state.data = None
    if 'filtered_data' not in st.session_state:
        st.session_state.filtered_data = None
    if 'original_data' not in st.session_state:
        st.session_state.original_data = None
    if 'herb_names' not in st.session_state:
        st.session_state.herb_names = []


def load_report(file_path_or_buffer):
    """
    加载鉴定报告
    
    Args:
        file_path_or_buffer: 文件路径或上传的文件对象
    
    Returns:
        DataFrame: 合并后的数据
    """
    try:
        if hasattr(file_path_or_buffer, 'name'):
            # 处理上传的文件
            xlsx = pd.ExcelFile(file_path_or_buffer)
        else:
            xlsx = pd.ExcelFile(file_path_or_buffer)
        
        all_dfs = []
        for sheet in xlsx.sheet_names:
            df = pd.read_excel(xlsx, sheet_name=sheet)
            df['_来源Sheet'] = sheet
            all_dfs.append(df)
        
        if not all_dfs:
            return None
        
        combined_df = pd.concat(all_dfs, ignore_index=True)
        
        # 清理数据
        combined_df = combined_df.replace([np.inf, -np.inf], np.nan)
        
        # 转换数字列
        numeric_cols = ['ppm', '综合得分', '匹配碎片数', '匹配质量数', '序号']
        for col in numeric_cols:
            if col in combined_df.columns:
                combined_df[col] = pd.to_numeric(combined_df[col], errors='coerce')
        
        # 填充NaN
        combined_df = combined_df.fillna('')
        
        return combined_df
    
    except Exception as e:
        st.error(f"加载失败: {str(e)}")
        return None


def extract_herb_names(df):
    """提取药材名称列表"""
    herbs = []
    
    if '药材名称' in df.columns:
        herbs = df['药材名称'].dropna().unique().tolist()
    
    if not herbs and '_来源Sheet' in df.columns:
        herbs = df['_来源Sheet'].dropna().unique().tolist()
    
    return sorted([str(h) for h in herbs if str(h) != 'nan' and str(h) != ''])


def show_data_overview(df):
    """显示数据概览"""
    cols = st.columns(4)
    
    with cols[0]:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{len(df):,}</div>
            <div class="stat-label">总化合物数</div>
        </div>
        """, unsafe_allow_html=True)
    
    with cols[1]:
        if '评级名称' in df.columns:
            high_confidence = len(df[df['评级名称'].isin(['确证级', '高置信级'])])
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{high_confidence}</div>
                <div class="stat-label">高置信化合物</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">-</div>
                <div class="stat-label">高置信化合物</div>
            </div>
            """, unsafe_allow_html=True)
    
    with cols[2]:
        if '匹配碎片数' in df.columns:
            with_frag = len(df[df['匹配碎片数'] > 0])
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{with_frag}</div>
                <div class="stat-label">有碎片证据</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">-</div>
                <div class="stat-label">有碎片证据</div>
            </div>
            """, unsafe_allow_html=True)
    
    with cols[3]:
        if '药材名称' in df.columns:
            herb_count = df['药材名称'].nunique()
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{herb_count}</div>
                <div class="stat-label">药材种类</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">-</div>
                <div class="stat-label">药材种类</div>
            </div>
            """, unsafe_allow_html=True)


def apply_filters(df, conditions):
    """应用筛选条件"""
    filtered = df.copy()
    
    # 药材筛选
    if conditions.get('herb'):
        if '药材名称' in filtered.columns:
            filtered = filtered[filtered['药材名称'].isin(conditions['herb'])]
        elif '_来源Sheet' in filtered.columns:
            filtered = filtered[filtered['_来源Sheet'].isin(conditions['herb'])]
    
    # 评级筛选
    if conditions.get('rating'):
        if '评级名称' in filtered.columns:
            filtered = filtered[filtered['评级名称'].isin(conditions['rating'])]
    
    # ppm范围
    if 'ppm_range' in conditions:
        min_ppm, max_ppm = conditions['ppm_range']
        if 'ppm' in filtered.columns:
            filtered = filtered[(filtered['ppm'] >= min_ppm) & (filtered['ppm'] <= max_ppm)]
    
    # 最低得分
    if conditions.get('min_score', 0) > 0:
        if '综合得分' in filtered.columns:
            filtered = filtered[filtered['综合得分'] >= conditions['min_score']]
    
    # 碎片匹配
    if 'has_fragment' in conditions:
        if '匹配碎片数' in filtered.columns:
            if conditions['has_fragment']:
                filtered = filtered[filtered['匹配碎片数'] > 0]
            else:
                filtered = filtered[filtered['匹配碎片数'] == 0]
    
    # 包含关键词
    if conditions.get('keywords'):
        name_cols = []
        if '化合物中文名' in filtered.columns:
            name_cols.append('化合物中文名')
        if '化合物英文名' in filtered.columns:
            name_cols.append('化合物英文名')
        
        if name_cols:
            mask = pd.Series([False] * len(filtered))
            for kw in conditions['keywords']:
                for col in name_cols:
                    mask = mask | filtered[col].str.contains(kw, na=False, case=False)
            filtered = filtered[mask]
    
    # 排除关键词
    if conditions.get('exclude_keywords'):
        name_cols = []
        if '化合物中文名' in filtered.columns:
            name_cols.append('化合物中文名')
        if '化合物英文名' in filtered.columns:
            name_cols.append('化合物英文名')
        
        if name_cols:
            mask = pd.Series([True] * len(filtered))
            for kw in conditions['exclude_keywords']:
                for col in name_cols:
                    mask = mask & ~filtered[col].str.contains(kw, na=False, case=False)
            filtered = filtered[mask]
    
    # 化合物类型
    if conditions.get('compound_type'):
        if '化合物类型' in filtered.columns:
            filtered = filtered[filtered['化合物类型'].str.contains(conditions['compound_type'], na=False)]
    
    # 分子量范围
    if 'mw_range' in conditions:
        min_mw, max_mw = conditions['mw_range']
        if '匹配质量数' in filtered.columns:
            filtered = filtered[(filtered['匹配质量数'] >= min_mw) & (filtered['匹配质量数'] <= max_mw)]
    
    return filtered


def show_visualizations_simple(df):
    """简单可视化（无plotly）"""
    st.markdown("## 📊 数据统计")
    
    col1, col2 = st.columns(2)
    
    # 评级分布
    with col1:
        if '评级名称' in df.columns:
            rating_counts = df['评级名称'].value_counts()
            st.markdown("**置信等级分布**")
            for level, count in rating_counts.items():
                pct = count / len(df) * 100
                st.markdown(f"- {level}: {count} ({pct:.1f}%)")
                st.progress(pct / 100)
    
    # ppm统计
    with col2:
        if 'ppm' in df.columns:
            st.markdown("**ppm误差统计**")
            st.markdown(f"- 最小值: {df['ppm'].min():.2f}")
            st.markdown(f"- 最大值: {df['ppm'].max():.2f}")
            st.markdown(f"- 平均值: {df['ppm'].mean():.2f}")
            st.markdown(f"- 中位数: {df['ppm'].median():.2f}")
            
            # ppm区间分布
            bins = [0, 5, 10, 20, 30, 50, 100, float('inf')]
            labels = ['0-5', '5-10', '10-20', '20-30', '30-50', '50-100', '>100']
            df['_ppm_bin'] = pd.cut(df['ppm'], bins=bins, labels=labels)
            st.markdown("**ppm区间分布**")
            for label in labels:
                count = (df['_ppm_bin'] == label).sum()
                if count > 0:
                    pct = count / len(df) * 100
                    st.markdown(f"- {label}: {count} ({pct:.1f}%)")
            df.drop('_ppm_bin', axis=1, inplace=True)
    
    # 碎片匹配
    if '匹配碎片数' in df.columns:
        col3, col4 = st.columns(2)
        with col3:
            has_frag = (df['匹配碎片数'] > 0).sum()
            no_frag = (df['匹配碎片数'] == 0).sum()
            st.markdown("**碎片匹配**")
            st.markdown(f"- 有碎片证据: {has_frag} ({has_frag/len(df)*100:.1f}%)")
            st.markdown(f"- 无碎片证据: {no_frag} ({no_frag/len(df)*100:.1f}%)")
        
        with col4:
            if '综合得分' in df.columns:
                st.markdown("**综合得分统计**")
                st.markdown(f"- 最高: {df['综合得分'].max():.1f}")
                st.markdown(f"- 最低: {df['综合得分'].min():.1f}")
                st.markdown(f"- 平均: {df['综合得分'].mean():.1f}")
    
    # 化合物类型
    if '化合物类型' in df.columns:
        type_counts = df['化合物类型'].value_counts().head(10)
        if not type_counts.empty:
            st.markdown("**Top 10 化合物类型**")
            for t, count in type_counts.items():
                st.markdown(f"- {t}: {count}")


def show_visualizations_plotly(df):
    """使用plotly的可视化"""
    if not PLOTLY_AVAILABLE:
        show_visualizations_simple(df)
        return
    
    st.markdown("## 📊 数据分析图表")
    
    col1, col2 = st.columns(2)
    
    # 评级分布
    with col1:
        if '评级名称' in df.columns:
            rating_counts = df['评级名称'].value_counts()
            fig = px.pie(
                values=rating_counts.values,
                names=rating_counts.index,
                title="化合物置信等级分布",
                color_discrete_sequence=px.colors.sequential.Greens_r
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # ppm分布
    with col2:
        if 'ppm' in df.columns:
            # 过滤异常值
            ppm_data = df[df['ppm'] <= 200]['ppm'] if len(df[df['ppm'] <= 200]) > 0 else df['ppm']
            fig = px.histogram(
                ppm_data, 
                nbins=30,
                title="ppm误差分布",
                labels={'value': 'ppm误差', 'count': '化合物数量'},
                color_discrete_sequence=['#2c5f2d']
            )
            fig.add_vline(x=20, line_dash="dash", line_color="red", 
                         annotation_text="20ppm", annotation_position="top")
            fig.add_vline(x=50, line_dash="dash", line_color="orange", 
                         annotation_text="50ppm", annotation_position="top")
            st.plotly_chart(fig, use_container_width=True)
    
    # 碎片匹配分布
    if '匹配碎片数' in df.columns:
        col3, col4 = st.columns(2)
        with col3:
            has_frag = (df['匹配碎片数'] > 0).sum()
            no_frag = (df['匹配碎片数'] == 0).sum()
            fig = px.pie(
                values=[has_frag, no_frag],
                names=['有碎片证据', '无碎片证据'],
                title="碎片匹配情况",
                color_discrete_sequence=['#97bc62', '#ffa500']
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col4:
            if '综合得分' in df.columns:
                fig = px.box(
                    df, y='综合得分',
                    title="综合得分分布",
                    color_discrete_sequence=['#2c5f2d']
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # 化合物类型分布
    if '化合物类型' in df.columns:
        type_counts = df['化合物类型'].value_counts().head(10)
        if not type_counts.empty:
            fig = px.bar(
                x=type_counts.values,
                y=type_counts.index,
                orientation='h',
                title="Top 10 化合物类型",
                labels={'x': '化合物数量', 'y': '类型'},
                color_discrete_sequence=['#2c5f2d']
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)


def show_results_table(df):
    """显示结果表格"""
    st.markdown("## 📋 筛选结果")
    
    if df.empty:
        st.warning("没有符合条件的化合物")
        return df
    
    # 选择排序方式
    sort_options = []
    if '综合得分' in df.columns:
        sort_options.append("综合得分 (高→低)")
    if 'ppm' in df.columns:
        sort_options.append("ppm (低→高)")
    if '匹配碎片数' in df.columns:
        sort_options.append("匹配碎片数 (多→少)")
    if '匹配质量数' in df.columns:
        sort_options.append("分子量 (小→大)")
    
    if sort_options:
        sort_by = st.selectbox("排序方式", sort_options)
        
        if sort_by == "综合得分 (高→低)" and '综合得分' in df.columns:
            df = df.sort_values('综合得分', ascending=False)
        elif sort_by == "ppm (低→高)" and 'ppm' in df.columns:
            df = df.sort_values('ppm', ascending=True)
        elif sort_by == "匹配碎片数 (多→少)" and '匹配碎片数' in df.columns:
            df = df.sort_values('匹配碎片数', ascending=False)
        elif sort_by == "分子量 (小→大)" and '匹配质量数' in df.columns:
            df = df.sort_values('匹配质量数', ascending=True)
    
    # 选择显示列
    default_cols = ['序号', '化合物中文名', '化合物英文名', '分子式', 'ppm', 
                    '综合得分', '评级名称', '匹配碎片数', '化合物类型', '药材名称']
    
    available_cols = [c for c in default_cols if c in df.columns]
    
    if not available_cols:
        # 如果没有标准列，显示所有列
        available_cols = df.columns.tolist()
    
    # 使用st.dataframe显示
    st.dataframe(
        df[available_cols],
        use_container_width=True,
        height=500,
        column_config={
            "序号": st.column_config.NumberColumn("序号", width="small"),
            "ppm": st.column_config.NumberColumn("ppm", format="%.2f", width="small"),
            "综合得分": st.column_config.NumberColumn("综合得分", format="%.1f", width="small"),
            "匹配碎片数": st.column_config.NumberColumn("碎片数", width="small")
        }
    )
    
    return df


def export_to_excel(df):
    """导出到Excel"""
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
    
    output.seek(0)
    return output.getvalue()


def download_button(df, filename):
    """导出下载按钮"""
    excel_data = export_to_excel(df)
    b64 = base64.b64encode(excel_data).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">📥 下载Excel文件</a>'
    st.markdown(href, unsafe_allow_html=True)


def show_filter_sidebar(df):
    """显示筛选侧边栏"""
    st.sidebar.markdown("# 🔍 筛选条件")
    
    conditions = {}
    
    # 快速预设
    st.sidebar.markdown("## 快速预设")
    preset = st.sidebar.selectbox(
        "选择预设模式",
        ["无", "高置信模式", "中等置信模式", "宽松模式", "确证级", "仅黄酮类", "仅生物碱", "仅萜类"]
    )
    
    if preset != "无":
        if preset == "高置信模式":
            if '评级名称' in df.columns:
                df = df[df['评级名称'].isin(['确证级', '高置信级'])]
            if 'ppm' in df.columns:
                df = df[df['ppm'] <= 20]
            if '匹配碎片数' in df.columns:
                df = df[df['匹配碎片数'] > 0]
        elif preset == "中等置信模式":
            if '评级名称' in df.columns:
                df = df[df['评级名称'].isin(['确证级', '高置信级', '推定级'])]
            if 'ppm' in df.columns:
                df = df[df['ppm'] <= 50]
        elif preset == "宽松模式":
            if 'ppm' in df.columns:
                df = df[df['ppm'] <= 100]
            if '匹配碎片数' in df.columns:
                df = df[df['匹配碎片数'] > 0]
        elif preset == "确证级":
            if '评级名称' in df.columns:
                df = df[df['评级名称'] == '确证级']
        elif preset in ["仅黄酮类", "仅生物碱", "仅萜类"]:
            if 'ppm' in df.columns:
                df = df[df['ppm'] <= 30]
            
            keywords = {
                "仅黄酮类": ['黄酮', '黄酮醇', '黄烷酮'],
                "仅生物碱": ['生物碱', '碱'],
                "仅萜类": ['萜', '萜类', 'terpene']
            }[preset]
            
            name_cols = []
            if '化合物中文名' in df.columns:
                name_cols.append('化合物中文名')
            if '化合物类型' in df.columns:
                name_cols.append('化合物类型')
            
            if name_cols:
                mask = pd.Series([False] * len(df))
                for kw in keywords:
                    for col in name_cols:
                        mask = mask | df[col].str.contains(kw, na=False, case=False)
                df = df[mask]
        
        st.sidebar.success(f"已应用: {preset}")
        return df
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("## 基础筛选")
    
    # 药材筛选
    if st.session_state.herb_names:
        selected_herbs = st.sidebar.multiselect(
            "药材名称",
            options=st.session_state.herb_names,
            default=[]
        )
        if selected_herbs:
            conditions['herb'] = selected_herbs
    
    # 评级筛选
    if '评级名称' in df.columns:
        levels = df['评级名称'].dropna().unique().tolist()
        selected_levels = st.sidebar.multiselect("置信等级", options=levels, default=[])
        if selected_levels:
            conditions['rating'] = selected_levels
    
    # ppm范围
    if 'ppm' in df.columns:
        min_val = float(df['ppm'].min())
        max_val = float(df['ppm'].max())
        ppm_range = st.sidebar.slider(
            "ppm误差范围",
            min_value=0.0,
            max_value=min(max_val, 200.0),
            value=(0.0, min(max_val, 100.0))
        )
        conditions['ppm_range'] = ppm_range
    
    # 综合得分
    if '综合得分' in df.columns:
        min_score = st.sidebar.slider(
            "最低综合得分",
            min_value=0,
            max_value=100,
            value=0
        )
        conditions['min_score'] = min_score
    
    # 碎片数
    if '匹配碎片数' in df.columns:
        frag_choice = st.sidebar.radio(
            "碎片匹配",
            ["全部", "有碎片匹配", "无碎片匹配"]
        )
        if frag_choice == "有碎片匹配":
            conditions['has_fragment'] = True
        elif frag_choice == "无碎片匹配":
            conditions['has_fragment'] = False
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("## 化合物筛选")
    
    # 关键词
    keywords = st.sidebar.text_input("包含关键词 (用逗号分隔)", placeholder="例如: 苷,黄酮,酸")
    if keywords:
        conditions['keywords'] = [k.strip() for k in keywords.split(',')]
    
    # 排除关键词
    exclude_keywords = st.sidebar.text_input("排除关键词 (用逗号分隔)", placeholder="例如: 酯,醛")
    if exclude_keywords:
        conditions['exclude_keywords'] = [k.strip() for k in exclude_keywords.split(',')]
    
    # 类型筛选
    if '化合物类型' in df.columns:
        types = df['化合物类型'].dropna().unique().tolist()
        if types:
            selected_type = st.sidebar.selectbox("化合物类型", ["全部"] + types)
            if selected_type != "全部":
                conditions['compound_type'] = selected_type
    
    # 分子量范围
    if '匹配质量数' in df.columns:
        col1, col2 = st.sidebar.columns(2)
        with col1:
            min_mw = st.number_input("最小分子量", min_value=0, value=0)
        with col2:
            max_mw = st.number_input("最大分子量", min_value=0, value=2000)
        if min_mw > 0 or max_mw < 2000:
            conditions['mw_range'] = (min_mw, max_mw)
    
    # 应用筛选
    if conditions:
        return apply_filters(df, conditions)
    
    return df


def main():
    """主函数"""
    init_session_state()
    
    # 页眉
    st.markdown("""
    <div class="main-header">
        <h1>🌿 中药化合物鉴定报告筛选系统</h1>
        <p>支持所有药材 · 多条件组合筛选 · 智能分析</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 文件上传区域
    with st.expander("📂 加载报告文件", expanded=st.session_state.data is None):
        uploaded_file = st.file_uploader(
            "上传鉴定报告 (Excel格式)",
            type=['xlsx', 'xls'],
            help="支持栀子、丹参、黄芪等所有药材的鉴定报告"
        )
        
        if uploaded_file is not None:
            with st.spinner("正在加载数据..."):
                df = load_report(uploaded_file)
                if df is not None and not df.empty:
                    st.session_state.data = df
                    st.session_state.original_data = df.copy()
                    st.session_state.filtered_data = df.copy()
                    st.session_state.herb_names = extract_herb_names(df)
                    st.success(f"✅ 成功加载 {len(df)} 条记录，包含 {len(st.session_state.herb_names)} 种药材")
                else:
                    st.error("文件加载失败，请检查文件格式")
    
    # 主内容区域
    if st.session_state.data is not None:
        df = st.session_state.data
        
        # 工具栏
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.markdown(f"**当前数据:** {len(st.session_state.filtered_data)} / {len(df)} 条记录")
        with col2:
            if st.button("🔄 重置所有筛选", use_container_width=True):
                st.session_state.filtered_data = st.session_state.original_data.copy()
                st.rerun()
        with col3:
            export_col, _ = st.columns(2)
            with export_col:
                pass
        
        # 数据概览
        show_data_overview(st.session_state.filtered_data)
        
        # 筛选
        filtered_df = show_filter_sidebar(st.session_state.original_data)
        st.session_state.filtered_data = filtered_df
        
        if filtered_df is not None and not filtered_df.empty:
            # 显示筛选结果统计
            st.info(f"🔍 筛选完成: 找到 {len(filtered_df)} 个符合条件的化合物")
            
            # 可视化图表
            if PLOTLY_AVAILABLE:
                show_visualizations_plotly(filtered_df)
            else:
                show_visualizations_simple(filtered_df)
            
            # 结果显示
            result_df = show_results_table(filtered_df)
            
            # 导出
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"筛选结果_{timestamp}.xlsx"
            download_button(result_df, filename)
        else:
            st.warning("⚠️ 没有找到符合条件的化合物，请调整筛选条件")
        
        # 详情查看
        with st.expander("📖 查看化合物详情"):
            if filtered_df is not None and not filtered_df.empty:
                compound_col = '化合物中文名' if '化合物中文名' in filtered_df.columns else filtered_df.columns[0]
                selected_compound = st.selectbox(
                    "选择化合物查看详情",
                    filtered_df[compound_col].tolist()
                )
                if selected_compound:
                    details = filtered_df[filtered_df[compound_col] == selected_compound].iloc[0]
                    # 显示详情
                    for col in filtered_df.columns:
                        val = details[col]
                        if pd.notna(val) and str(val).strip():
                            st.markdown(f"**{col}:** {val}")
    
    else:
        # 空状态提示
        st.info("👈 请先上传鉴定报告文件开始分析")
        
        # 使用说明
        with st.expander("📖 使用说明"):
            st.markdown("""
            ### 支持的报告格式
            - 支持所有中药的化合物鉴定报告
            - 文件应包含以下字段（部分）：
                - 化合物中文名/英文名
                - ppm误差
                - 综合得分
                - 评级名称（确证级/高置信级/推定级/提示级）
                - 匹配碎片数
                - 化合物类型
                - 药材名称（可选）
            
            ### 筛选功能
            - **快速预设**: 一键应用常用筛选组合
            - **多条件筛选**: 支持药材、等级、ppm、得分等多维度筛选
            - **关键词搜索**: 按化合物名称或类型筛选
            - **可视化分析**: 自动生成数据分布图表
            - **结果导出**: 支持Excel格式导出
            
            ### 常见问题
            1. 如果图表不显示，请安装 plotly: `pip install plotly`
            2. 确保Excel文件包含必要的列
            3. 支持多个工作表的文件
            """)


if __name__ == "__main__":
    main()
