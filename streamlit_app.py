# -*- coding: utf-8 -*-
"""
中药化合物鉴定报告筛选工具 - Streamlit Web版 v1.0
适用于所有药材的鉴定报告筛选
"""

import streamlit as st
import pandas as pd
import os
from datetime import datetime
import glob

st.set_page_config(
    page_title="中药化合物鉴定报告筛选工具",
    page_icon="🔬",
    layout="wide"
)

# 快速预设定义
PRESETS = {
    '1': ('高置信模式', '确证级+高置信级, ppm≤20, 有碎片'),
    '2': ('中等置信', '推定级+, ppm≤50'),
    '3': ('宽松模式', 'ppm≤100, 有碎片'),
    '4': ('仅确证级', '确证级'),
    '5': ('仅黄酮类', 'ppm≤30, 黄酮/黄酮醇/黄烷酮'),
    '6': ('仅生物碱', 'ppm≤30, 生物碱'),
    '7': ('仅萜类', 'ppm≤30, 萜/单萜/倍半萜/二萜/三萜'),
    '8': ('仅酚酸类', 'ppm≤30, 酚酸/苯甲酸'),
    '9': ('仅糖类', 'ppm≤30, 糖/糖苷/多糖'),
    '10': ('确证+高置信无碎片', '高置信级, 无碎片'),
    '11': ('高质量无碎片', 'ppm≤10, 无碎片'),
    '12': ('综合评分高', '得分≥85'),
    '13': ('低ppm精准匹配', 'ppm≤5, 有碎片'),
    '14': ('中等碎片匹配', '碎片数3-10个'),
}


@st.cache_data
def load_report(uploaded_file):
    """加载上传的报告文件"""
    try:
        if uploaded_file is not None:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                xlsx = pd.ExcelFile(uploaded_file)
                all_dfs = []
                for sheet in xlsx.sheet_names:
                    sheet_df = pd.read_excel(xlsx, sheet_name=sheet)
                    sheet_df['_来源Sheet'] = sheet
                    all_dfs.append(sheet_df)
                df = pd.concat(all_dfs, ignore_index=True)
            return df
    except Exception as e:
        st.error(f"加载失败: {e}")
        return None
    return None


def find_local_reports():
    """查找本地报告文件"""
    patterns = ['*鉴定报告*.xlsx', '*筛选结果*.xlsx', '*.xlsx']
    found_files = []
    for pattern in patterns:
        files = glob.glob(pattern)
        for f in files:
            if not f.startswith('~') and f not in found_files:
                found_files.append(f)
    return sorted(found_files)


def apply_preset(df, preset_key):
    """应用快速预设"""
    if df is None or preset_key not in PRESETS:
        return df

    if preset_key == '1':
        return df[(df['评级名称'].isin(['确证级', '高置信级'])) & (df['ppm'] <= 20) & (df['匹配碎片数'] > 0)]
    elif preset_key == '2':
        return df[(df['评级名称'].isin(['确证级', '高置信级', '推定级'])) & (df['ppm'] <= 50)]
    elif preset_key == '3':
        return df[(df['ppm'] <= 100) & (df['匹配碎片数'] > 0)]
    elif preset_key == '4':
        return df[df['评级名称'] == '确证级']
    elif preset_key == '5':
        return df[(df['ppm'] <= 30) & (df['化合物中文名'].str.contains('黄酮|黄酮醇|黄烷酮|flavonoid', na=False, case=False))]
    elif preset_key == '6':
        return df[(df['ppm'] <= 30) & (df['化合物中文名'].str.contains('生物碱|alkaloid', na=False, case=False))]
    elif preset_key == '7':
        return df[(df['ppm'] <= 30) & (df['化合物中文名'].str.contains('萜|单萜|倍半萜|二萜|三萜|terpene', na=False, case=False))]
    elif preset_key == '8':
        return df[(df['ppm'] <= 30) & (df['化合物中文名'].str.contains('酚酸|苯甲酸|phenolic', na=False, case=False))]
    elif preset_key == '9':
        return df[(df['ppm'] <= 30) & (df['化合物中文名'].str.contains('糖|糖苷|多糖|glucoside|sugar', na=False, case=False))]
    elif preset_key == '10':
        return df[(df['评级名称'].isin(['确证级', '高置信级'])) & (df['匹配碎片数'] == 0)]
    elif preset_key == '11':
        return df[(df['ppm'] <= 10) & (df['匹配碎片数'] == 0)]
    elif preset_key == '12':
        return df[df['综合得分'] >= 85]
    elif preset_key == '13':
        return df[(df['ppm'] <= 5) & (df['匹配碎片数'] > 0)]
    elif preset_key == '14':
        return df[(df['匹配碎片数'] >= 3) & (df['匹配碎片数'] <= 10)]
    return df


def apply_custom_filters(df, filters):
    """应用自定义筛选条件"""
    if df is None:
        return df

    filtered = df.copy()

    if filters.get('levels'):
        filtered = filtered[filtered['评级名称'].isin(filters['levels'])]

    if filters.get('ppm_min') is not None:
        filtered = filtered[filtered['ppm'] >= filters['ppm_min']]
    if filters.get('ppm_max') is not None:
        filtered = filtered[filtered['ppm'] <= filters['ppm_max']]

    if filters.get('score_min') is not None:
        filtered = filtered[filtered['综合得分'] >= filters['score_min']]

    if filters.get('frag_min') is not None:
        filtered = filtered[filtered['匹配碎片数'] >= filters['frag_min']]

    if filters.get('has_fragment') == '有碎片':
        filtered = filtered[filtered['匹配碎片数'] > 0]
    elif filters.get('has_fragment') == '无碎片':
        filtered = filtered[filtered['匹配碎片数'] == 0]

    if filters.get('include_kw'):
        for kw in filters['include_kw']:
            filtered = filtered[filtered['化合物中文名'].str.contains(kw, na=False, case=False)]

    if filters.get('exclude_kw'):
        for kw in filters['exclude_kw']:
            filtered = filtered[~filtered['化合物中文名'].str.contains(kw, na=False, case=False)]

    if filters.get('formula'):
        filtered = filtered[filtered['分子式'].str.contains(filters['formula'], na=False, case=False)]

    if filters.get('mw_min') is not None:
        filtered = filtered[filtered['匹配质量数'] >= filters['mw_min']]
    if filters.get('mw_max') is not None:
        filtered = filtered[filtered['匹配质量数'] <= filters['mw_max']]

    return filtered


def main():
    st.title("🔬 中药化合物鉴定报告筛选工具")
    st.markdown("**通用版 - 适用于所有药材的鉴定报告**")

    if 'df_original' not in st.session_state:
        st.session_state.df_original = None
    if 'df_filtered' not in st.session_state:
        st.session_state.df_filtered = None

    # 侧边栏
    with st.sidebar:
        st.header("📁 加载报告")

        uploaded_file = st.file_uploader(
            "上传鉴定报告 (Excel/CSV)",
            type=['xlsx', 'xls', 'csv']
        )

        if uploaded_file:
            df = load_report(uploaded_file)
            if df is not None:
                st.session_state.df_original = df
                st.session_state.df_filtered = df
                st.success(f"已加载 {len(df)} 条记录")

        st.divider()
        st.markdown("**或选择本地文件:**")
        local_files = find_local_reports()
        if local_files:
            selected_file = st.selectbox("本地报告", ["-- 选择 --"] + local_files)
            if selected_file != "-- 选择 --":
                try:
                    xlsx = pd.ExcelFile(selected_file)
                    all_dfs = []
                    for sheet in xlsx.sheet_names:
                        sheet_df = pd.read_excel(xlsx, sheet_name=sheet)
                        sheet_df['_来源Sheet'] = sheet
                        all_dfs.append(sheet_df)
                    df = pd.concat(all_dfs, ignore_index=True)
                    st.session_state.df_original = df
                    st.session_state.df_filtered = df
                    st.success(f"已加载 {len(df)} 条记录")
                except Exception as e:
                    st.error(f"加载失败: {e}")

        if st.session_state.df_original is not None:
            st.divider()
            st.markdown(f"**原始数据:** {len(st.session_state.df_original)} 条")

    # 主界面
    tab1, tab2, tab3 = st.tabs(["⚡ 快速筛选", "🔧 自定义筛选", "📊 统计摘要"])

    with tab1:
        st.subheader("快速预设筛选")
        cols = st.columns(2)
        for i, (key, (name, desc)) in enumerate(PRESETS.items()):
            with cols[i % 2]:
                if st.button(f"{i+1}. {name}", use_container_width=True):
                    if st.session_state.df_original is not None:
                        st.session_state.df_filtered = apply_preset(
                            st.session_state.df_original.copy(), key
                        )
                        st.rerun()

        if st.session_state.df_filtered is not None:
            st.divider()
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("筛选结果", len(st.session_state.df_filtered))
            with col2:
                pct = len(st.session_state.df_filtered) / len(st.session_state.df_original) * 100
                st.metric("保留比例", f"{pct:.1f}%")
            with col3:
                if '匹配碎片数' in st.session_state.df_filtered.columns:
                    has_frag = (st.session_state.df_filtered['匹配碎片数'] > 0).sum()
                    st.metric("有碎片", has_frag)

    with tab2:
        st.subheader("自定义多条件筛选")
        if st.session_state.df_original is not None:
            with st.form("custom_filter"):
                filters = {}
                col1, col2 = st.columns(2)

                with col1:
                    if '评级名称' in st.session_state.df_original.columns:
                        levels = st.session_state.df_original['评级名称'].dropna().unique().tolist()
                        selected_levels = st.multiselect("评级", levels, default=levels)
                        filters['levels'] = selected_levels if selected_levels else None

                    ppm_min, ppm_max = st.slider("ppm范围", 0, 100, (0, 100))
                    filters['ppm_min'] = ppm_min if ppm_min > 0 else None
                    filters['ppm_max'] = ppm_max if ppm_max < 100 else None

                    score_min = st.number_input("最低得分", 0, 100, 0)
                    filters['score_min'] = score_min if score_min > 0 else None

                with col2:
                    frag_min = st.number_input("最少碎片数", 0, 100, 0)
                    filters['frag_min'] = frag_min if frag_min > 0 else None

                    has_frag = st.radio("碎片状态", ["不限", "有碎片", "无碎片"], horizontal=True)
                    filters['has_fragment'] = None if has_frag == "不限" else has_frag

                    include_kw = st.text_input("包含关键词 (逗号分隔)")
                    filters['include_kw'] = [k.strip() for k in include_kw.split(',') if k.strip()] if include_kw else None

                    exclude_kw = st.text_input("排除关键词 (逗号分隔)")
                    filters['exclude_kw'] = [k.strip() for k in exclude_kw.split(',') if k.strip()] if exclude_kw else None

                submitted = st.form_submit_button("应用筛选", type="primary", use_container_width=True)
                if submitted:
                    st.session_state.df_filtered = apply_custom_filters(
                        st.session_state.df_original.copy(), filters
                    )
                    st.rerun()
        else:
            st.info("请先上传或选择报告文件")

    with tab3:
        st.subheader("统计摘要")
        if st.session_state.df_filtered is not None:
            df = st.session_state.df_filtered
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("筛选结果", len(df))
            with col2:
                if '综合得分' in df.columns:
                    st.metric("平均得分", f"{df['综合得分'].mean():.1f}")
            with col3:
                if 'ppm' in df.columns:
                    st.metric("平均ppm", f"{df['ppm'].mean():.1f}")
            with col4:
                if '匹配碎片数' in df.columns:
                    st.metric("有碎片", (df['匹配碎片数'] > 0).sum())

            st.divider()
            if '评级名称' in df.columns:
                st.markdown("### 评级分布")
                st.bar_chart(df['评级名称'].value_counts())

            if '化合物类型' in df.columns:
                st.markdown("### 化合物类型 (Top 10)")
                st.bar_chart(df['化合物类型'].value_counts().head(10))
        else:
            st.info("请先加载报告文件")

    # 结果表格和下载
    if st.session_state.df_filtered is not None:
        st.divider()
        st.subheader("📋 筛选结果")

        display_cols = st.multiselect(
            "显示列",
            list(st.session_state.df_filtered.columns),
            default=['序号', '化合物中文名', '分子式', 'ppm', '综合得分', '评级名称', '匹配碎片数']
        )

        if display_cols:
            sort_col = st.selectbox("排序", ["无排序"] + display_cols)
            sort_asc = st.checkbox("升序")

            df_display = st.session_state.df_filtered[display_cols].copy()
            if sort_col != "无排序" and sort_col in df_display.columns:
                df_display = df_display.sort_values(sort_col, ascending=sort_asc)

            st.dataframe(df_display, use_container_width=True, height=400)

            col1, col2 = st.columns(2)
            with col1:
                from io import BytesIO
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    with_frag = df_display[df_display['匹配碎片数'] > 0] if '匹配碎片数' in df_display.columns else pd.DataFrame()
                    no_frag = df_display[df_display['匹配碎片数'] == 0] if '匹配碎片数' in df_display.columns else pd.DataFrame()
                    if not with_frag.empty:
                        with_frag.to_excel(writer, sheet_name='有碎片匹配', index=False)
                    if not no_frag.empty:
                        no_frag.to_excel(writer, sheet_name='无碎片匹配', index=False)
                    elif with_frag.empty:
                        df_display.to_excel(writer, sheet_name='筛选结果', index=False)

                st.download_button(
                    "📥 下载完整报告 (Excel)",
                    output.getvalue(),
                    f"筛选结果_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

            with col2:
                summary_cols = ['序号', '化合物中文名', '分子式', '匹配质量数', 'ppm', '综合得分', '评级名称', '匹配碎片数']
                available_summary = [c for c in summary_cols if c in df_display.columns]
                summary_df = df_display[available_summary]
                output_summary = BytesIO()
                summary_df.to_excel(output_summary, index=False, engine='openpyxl')

                st.download_button(
                    "📥 下载精简摘要",
                    output_summary.getvalue(),
                    f"摘要报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

        if st.button("🔄 重置筛选", type="secondary"):
            st.session_state.df_filtered = st.session_state.df_original
            st.rerun()


if __name__ == "__main__":
    main()
