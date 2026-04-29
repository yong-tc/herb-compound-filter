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

# 尝试导入可视化库
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# 尝试导入openpyxl，如果没有则使用备用方法
try:
    from openpyxl import load_workbook
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

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
    加载鉴定报告 - 使用多个引擎尝试
    """
    try:
        # 方法1: 尝试直接读取（pandas会自动选择引擎）
        try:
            df = pd.read_excel(file_path_or_buffer, sheet_name=None)
            all_dfs = []
            for sheet_name, sheet_df in df.items():
                sheet_df['_来源Sheet'] = sheet_name
                all_dfs.append(sheet_df)
            combined_df = pd.concat(all_dfs, ignore_index=True)
        except Exception as e1:
            # 方法2: 尝试使用calamine引擎（如果可用）
            try:
                df = pd.read_excel(file_path_or_buffer, sheet_name=None, engine='calamine')
                all_dfs = []
                for sheet_name, sheet_df in df.items():
                    sheet_df['_来源Sheet'] = sheet_name
                    all_dfs.append(sheet_df)
                combined_df = pd.concat(all_dfs, ignore_index=True)
            except Exception as e2:
                # 方法3: 尝试只读第一个sheet
                try:
                    combined_df = pd.read_excel(file_path_or_buffer, sheet_name=0)
                    combined_df['_来源Sheet'] = 'Sheet1'
                except Exception as e3:
                    st.error(f"无法读取文件。请确保已安装依赖: pip install openpyxl pandas")
                    st.error(f"错误详情: {str(e3)}")
                    return None
        
        if combined_df is None or combined_df.empty:
            return None
        
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
    if df is None or df.empty:
        return df
    
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


def show_visualizations(df):
    """显示可视化图表"""
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
        # 如果没有标准列，显示所有列（排除内部列）
        available_cols = [c for c in df.columns if not c.startswith('_')]
    
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
    """导出到Excel - 使用csv备用方法"""
    try:
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
    except Exception as e:
        # 如果Excel导出失败，尝试CSV
        st.warning("Excel导出失败，使用CSV格式")
        csv_data = df.to_csv(index=False).encode('utf-8-sig')
        return csv_data


def download_button(df, filename):
    """导出下载按钮"""
    excel_data = export_to_excel(df)
    
    # 检测文件类型
    if filename.endswith('.xlsx'):
        mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        mime_type = "text/csv"
        filename = filename.replace('.xlsx', '.csv')
    
    b64 = base64.b64encode(excel_data).decode()
    href = f'<a href="data:{mime_type};base64,{b64}" download="{filename}">📥 下载文件</a>'
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
                "仅黄酮类": ['黄酮', '黄酮醇', '黄烷酮', 'flavonoid'],
                "仅生物碱": ['生物碱', '碱', 'alkaloid'],
                "仅萜类": ['萜', '萜类', 'terpene', 'terpenoid']
            }[preset]
            
            name_cols = []
            if '化合物中文名' in df.columns:
                name_cols.append('化合物中文名')
            if '化合物类型' in df.columns:
                name_cols.append('化合物类型')
            if '化合物英文名' in df.columns:
                name_cols.append('化合物英文名')
            
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
        min_val = 0.0
        max_val = min(float(df['ppm'].max()), 200.0)
        ppm_range = st.sidebar.slider(
            "ppm误差范围",
            min_value=0.0,
            max_value=max_val,
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
    
    # 显示依赖状态
    if not OPENPYXL_AVAILABLE:
        st.warning("⚠️ openpyxl未安装，将使用备用方法读取文件。如需完整功能，请运行: pip install openpyxl")
    
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
                    
                    # 显示列名预览
                    with st.expander("查看数据列"):
                        st.write("数据列:", df.columns.tolist())
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
        
        # 数据概览
        show_data_overview(st.session_state.filtered_data)
        
        # 筛选
        filtered_df = show_filter_sidebar(st.session_state.original_data)
        st.session_state.filtered_data = filtered_df
        
        if filtered_df is not None and not filtered_df.empty:
            # 显示筛选结果统计
            st.info(f"🔍 筛选完成: 找到 {len(filtered_df)} 个符合条件的化合物")
            
            # 可视化图表
            show_visualizations(filtered_df)
            
            # 结果显示
            result_df = show_results_table(filtered_df)
            
            # 导出
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"筛选结果_{timestamp}.xlsx"
            download_button(result_df, filename)
        else:
            st.warning("⚠️ 没有找到符合条件的化合物，请调整筛选条件")
    
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
            
            ### 如何安装依赖
            在本地运行时，请确保安装以下包：
            ```bash
            pip install streamlit pandas openpyxl numpy
