# -*- coding: utf-8 -*-
"""
中药化合物鉴定报告筛选系统
支持所有药材的通用筛选平台
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import base64
from datetime import datetime

# 导入自定义模块
from utils.data_loader import load_report, get_available_columns, extract_herb_names
from utils.filter_engine import FilterEngine
from utils.report_generator import export_filtered_data, create_summary_stats

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


def show_filter_sidebar(df):
    """显示筛选侧边栏"""
    st.sidebar.markdown("# 🔍 筛选条件")
    
    engine = FilterEngine(df)
    conditions = {}
    
    # 快速预设
    st.sidebar.markdown("## 快速预设")
    preset = st.sidebar.selectbox(
        "选择预设模式",
        ["无", "高置信模式", "中等置信模式", "宽松模式", "确证级", "仅黄酮类", "仅生物碱", "仅萜类"]
    )
    
    preset_map = {
        "高置信模式": {'评级': ['确证级', '高置信级'], 'max_ppm': 20, 'has_fragment': True},
        "中等置信模式": {'评级': ['确证级', '高置信级', '推定级'], 'max_ppm': 50},
        "宽松模式": {'max_ppm': 100, 'has_fragment': True},
        "确证级": {'评级': ['确证级']},
        "仅黄酮类": {'max_ppm': 30, 'keywords': ['黄酮', '黄酮醇', '黄烷酮']},
        "仅生物碱": {'max_ppm': 30, 'keywords': ['生物碱', '碱']},
        "仅萜类": {'max_ppm': 30, 'keywords': ['萜', '萜类', 'terpene']}
    }
    
    if preset != "无":
        return engine.apply_preset(preset)
    
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
        min_ppm, max_ppm = st.sidebar.slider(
            "ppm误差范围",
            min_value=float(df['ppm'].min()),
            max_value=float(df['ppm'].max()),
            value=(0.0, 100.0)
        )
        conditions['ppm_range'] = (min_ppm, max_ppm)
    
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
        return engine.apply_conditions(conditions)
    
    return df


def show_visualizations(df):
    """显示可视化图表"""
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
            fig = px.histogram(
                df, x='ppm',
                nbins=30,
                title="ppm误差分布",
                labels={'ppm': 'ppm误差', 'count': '化合物数量'},
                color_discrete_sequence=['#2c5f2d']
            )
            fig.add_vline(x=20, line_dash="dash", line_color="red", annotation_text="20ppm")
            fig.add_vline(x=50, line_dash="dash", line_color="orange", annotation_text="50ppm")
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
    
    # 选择排序方式
    sort_by = st.selectbox(
        "排序方式",
        ["综合得分 (高→低)", "ppm (低→高)", "匹配碎片数 (多→少)", "分子量 (小→大)"]
    )
    
    if sort_by == "综合得分 (高→低)" and '综合得分' in df.columns:
        df = df.sort_values('综合得分', ascending=False)
    elif sort_by == "ppm (低→高)" and 'ppm' in df.columns:
        df = df.sort_values('ppm', ascending=True)
    elif sort_by == "匹配碎片数 (多→少)" and '匹配碎片数' in df.columns:
        df = df.sort_values('匹配碎片数', ascending=False)
    elif sort_by == "分子量 (小→大)" and '匹配质量数' in df.columns:
        df = df.sort_values('匹配质量数', ascending=True)
    
    # 选择显示列
    display_cols = []
    default_cols = ['序号', '化合物中文名', '化合物英文名', '分子式', 'ppm', 
                    '综合得分', '评级名称', '匹配碎片数', '化合物类型']
    
    available_cols = [c for c in default_cols if c in df.columns]
    
    # 添加药材名称列
    if '药材名称' in df.columns and '药材名称' not in available_cols:
        available_cols.insert(1, '药材名称')
    
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


def download_button(df, filename):
    """导出下载按钮"""
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
    b64 = base64.b64encode(output.read()).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">📥 下载Excel文件</a>'
    st.markdown(href, unsafe_allow_html=True)


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
            try:
                df = load_report(uploaded_file)
                if df is not None:
                    st.session_state.data = df
                    st.session_state.original_data = df.copy()
                    st.session_state.filtered_data = df.copy()
                    st.session_state.herb_names = extract_herb_names(df)
                    st.success(f"✅ 成功加载 {len(df)} 条记录，包含 {len(st.session_state.herb_names)} 种药材")
                else:
                    st.error("文件加载失败，请检查文件格式")
            except Exception as e:
                st.error(f"加载错误: {str(e)}")
    
    # 主内容区域
    if st.session_state.data is not None:
        df = st.session_state.data
        
        # 工具栏
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.markdown(f"**当前数据:** {len(st.session_state.filtered_data)} / {len(df)} 条记录")
        with col2:
            if st.button("🔄 重置所有筛选", use_container_width=True):
                st.session_state.filtered_data = df.copy()
                st.rerun()
        with col3:
            # 导出功能
            export_format = st.selectbox("导出格式", ["Excel完整报告", "Excel摘要"], label_visibility="collapsed")
        
        # 数据概览
        show_data_overview(st.session_state.filtered_data)
        
        # 筛选侧边栏
        filtered_df = show_filter_sidebar(st.session_state.data)
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
            if export_format == "Excel完整报告":
                filename = f"筛选结果_{timestamp}.xlsx"
                download_button(result_df, filename)
            else:
                # 摘要报告
                summary_cols = ['序号', '化合物中文名', 'ppm', '综合得分', '评级名称', '匹配碎片数']
                available_summary = [c for c in summary_cols if c in result_df.columns]
                if available_summary:
                    summary_df = result_df[available_summary].copy()
                    filename = f"摘要报告_{timestamp}.xlsx"
                    download_button(summary_df, filename)
        else:
            st.warning("⚠️ 没有找到符合条件的化合物，请调整筛选条件")
        
        # 详情查看
        with st.expander("📖 查看化合物详情"):
            if filtered_df is not None and not filtered_df.empty:
                selected_compound = st.selectbox(
                    "选择化合物查看详情",
                    filtered_df['化合物中文名'].tolist() if '化合物中文名' in filtered_df.columns else []
                )
                if selected_compound:
                    details = filtered_df[filtered_df['化合物中文名'] == selected_compound].iloc[0]
                    st.json(details.to_dict())
    
    else:
        # 空状态提示
        st.info("👈 请先上传鉴定报告文件开始分析")
        
        # 示例数据说明
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
            
            ### 筛选功能
            - **快速预设**: 一键应用常用筛选组合
            - **多条件筛选**: 支持药材、等级、ppm、得分等多维度筛选
            - **关键词搜索**: 按化合物名称或类型筛选
            - **可视化分析**: 自动生成数据分布图表
            - **结果导出**: 支持Excel格式导出
            
            ### 常见问题
            如有问题，请检查报告文件格式是否正确。
            """)


if __name__ == "__main__":
    main()
