# -*- coding: utf-8 -*-
"""
中药化合物鉴定报告筛选工具 - 智能验证版
四步验证流程：确证级 → 高置信级 → 推定级 → 排除提示级
支持诊断离子文件上传验证
"""

import streamlit as st
import pandas as pd
import re
from datetime import datetime
from io import BytesIO

st.set_page_config(
    page_title="智能鉴定筛选",
    page_icon="🔬",
    layout="wide"
)

# 诊断离子示例（常见化合物类别特征离子）
DEFAULT_DIAGNOSTIC_IONS = {
    '生物碱': ['91.05', '77.04', '65.04', '107.05', '121.06'],
    '黄酮': ['153.02', '165.02', '271.06', '285.04', '286.05'],
    '苯丙素': ['119.05', '137.06', '163.04', '145.03', '117.03'],
    '萜类': ['95.05', '81.07', '109.07', '123.08', '137.13'],
    '有机酸': ['59.01', '71.01', '87.01', '103.04', '129.02'],
    '香豆素': ['145.03', '163.04', '189.05', '217.05', '247.06'],
    '环烯醚萜': ['101.06', '113.06', '127.08', '155.07', '169.09'],
}

@st.cache_data
def load_report(file):
    if file is None:
        return None
    try:
        if file.name.endswith('.csv'):
            return pd.read_csv(file)
        else:
            xlsx = pd.ExcelFile(file)
            dfs = []
            for sheet in xlsx.sheet_names:
                df = pd.read_excel(xlsx, sheet_name=sheet)
                df['_来源'] = sheet
                dfs.append(df)
            return pd.concat(dfs, ignore_index=True)
    except Exception as e:
        st.error(f"加载失败: {e}")
        return None

def load_diagnostic_ions(file):
    """加载诊断离子文件"""
    try:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)

        # 尝试识别列名
        for col in df.columns:
            col_lower = col.lower()
            if '化合物' in col or '类别' in col or '类型' in col or 'class' in col_lower:
                compound_col = col
            if '离子' in col or 'fragment' in col_lower or 'mz' in col_lower:
                ion_col = col

        # 解析为字典
        ions_dict = {}
        for _, row in df.iterrows():
            compound_type = str(row.get(compound_col, '')).strip()
            ion_val = str(row.get(ion_col, '')).strip()
            if compound_type and ion_val:
                if compound_type not in ions_dict:
                    ions_dict[compound_type] = []
                ions_dict[compound_type].append(ion_val)

        return ions_dict
    except Exception as e:
        st.error(f"诊断离子文件解析失败: {e}")
        return {}

def check_diagnostic_ions(row, ions_dict):
    """检查诊断离子匹配情况"""
    compound_type = str(row.get('化合物类型', ''))
    all_fragments = str(row.get('所有碎片离子', '')) + ' ' + str(row.get('主要碎片离子', ''))

    if compound_type in ions_dict:
        matched = 0
        for ion in ions_dict[compound_type]:
            if ion in all_fragments:
                matched += 1
        return matched, len(ions_dict[compound_type])
    return 0, 0

def apply_four_step_filter(df, ions_dict=None, min_literature=1, min_frag_match=2):
    """四步验证流程筛选 - 所有级别均需验证"""
    if df is None:
        return None

    results = []

    for _, row in df.iterrows():
        level = row.get('评级名称', '')
        literature_count = row.get('文献来源数', 1) or 1
        frag_count = row.get('匹配碎片数', 0) or 0

        # 诊断离子检查
        diag_matched = 0
        diag_total = 0
        if ions_dict:
            diag_matched, diag_total = check_diagnostic_ions(row, ions_dict)

        if level == '确证级':
            # 第一步：确证级也需要验证
            # 诊断离子匹配且碎片数足够 → 高可信采纳
            if diag_total > 0 and diag_matched >= 1 and frag_count >= min_frag_match:
                results.append({
                    **row.to_dict(),
                    '验证结果': '采纳',
                    '验证级别': '确证级-诊断离子确认',
                    '诊断离子匹配': f'{diag_matched}/{diag_total}'
                })
            # 文献支持强 → 采纳
            elif literature_count >= min_literature + 1:
                results.append({
                    **row.to_dict(),
                    '验证结果': '采纳',
                    '验证级别': '确证级-多文献支持',
                    '诊断离子匹配': f'{diag_matched}/{diag_total}' if diag_total > 0 else 'N/A'
                })
            # 碎片数足够 → 采纳
            elif frag_count >= min_frag_match * 2:
                results.append({
                    **row.to_dict(),
                    '验证结果': '采纳',
                    '验证级别': '确证级-碎片确认',
                    '诊断离子匹配': f'{diag_matched}/{diag_total}' if diag_total > 0 else 'N/A'
                })
            else:
                results.append({
                    **row.to_dict(),
                    '验证结果': '候选',
                    '验证级别': '确证级-待核实',
                    '诊断离子匹配': f'{diag_matched}/{diag_total}' if diag_total > 0 else '未验证'
                })

        elif level == '高置信级':
            # 第二步：高置信级需诊断离子验证
            if diag_total > 0 and diag_matched >= 1 and frag_count >= min_frag_match:
                results.append({
                    **row.to_dict(),
                    '验证结果': '采纳',
                    '验证级别': '高置信级-诊断离子确认',
                    '诊断离子匹配': f'{diag_matched}/{diag_total}'
                })
            elif literature_count >= min_literature + 2:
                results.append({
                    **row.to_dict(),
                    '验证结果': '采纳',
                    '验证级别': '高置信级-多文献支持',
                    '诊断离子匹配': f'{diag_matched}/{diag_total}' if diag_total > 0 else 'N/A'
                })
            else:
                results.append({
                    **row.to_dict(),
                    '验证结果': '候选',
                    '验证级别': '高置信级-待核实',
                    '诊断离子匹配': f'{diag_matched}/{diag_total}' if diag_total > 0 else '未验证'
                })

        elif level == '推定级':
            # 第三步：推定级需要文献支持且诊断离子确认
            if literature_count >= min_literature and diag_matched >= 1:
                results.append({
                    **row.to_dict(),
                    '验证结果': '采纳',
                    '验证级别': '推定级-文献+诊断确认',
                    '诊断离子匹配': f'{diag_matched}/{diag_total}' if diag_total > 0 else 'N/A'
                })
            elif literature_count >= min_literature + 2:
                results.append({
                    **row.to_dict(),
                    '验证结果': '采纳',
                    '验证级别': '推定级-多文献支持',
                    '诊断离子匹配': f'{diag_matched}/{diag_total}' if diag_total > 0 else 'N/A'
                })
            else:
                results.append({
                    **row.to_dict(),
                    '验证结果': '暂不录入',
                    '验证级别': '推定级-证据不足',
                    '诊断离子匹配': f'{diag_matched}/{diag_total}' if diag_total > 0 else '未验证'
                })

        # 提示级：直接排除，不加入结果

    return pd.DataFrame(results)

# 页面标题
st.title("🔬 中药化合物鉴定 - 智能验证筛选")
st.caption("四步验证流程 + 诊断离子验证")

# 侧边栏设置
with st.sidebar:
    st.header("设置")

    # 诊断离子上传
    st.subheader("诊断离子文件")
    ions_file = st.file_uploader("上传诊断离子(CSV/Excel)", type=['csv', 'xlsx', 'xls'])

    if ions_file:
        custom_ions = load_diagnostic_ions(ions_file)
        st.success(f"已加载 {len(custom_ions)} 个类别")
    else:
        custom_ions = DEFAULT_DIAGNOSTIC_IONS
        st.info(f"使用默认离子库 ({len(custom_ions)} 个类别)")

    # 诊断离子库预览
    with st.expander("诊断离子库"):
        for compound_type, ions in custom_ions.items():
            st.text(f"{compound_type}: {', '.join(ions[:3])}...")

    # 文献来源数设置
    st.subheader("验证阈值设置")
    min_literature = st.slider("最低文献数", 1, 5, 2)
    min_frag_match = st.slider("最低碎片数", 1, 20, 4)

# 文件上传
uploaded_file = st.file_uploader("上传鉴定报告 (Excel/CSV)", type=['xlsx', 'xls', 'csv'])

df_original = load_report(uploaded_file)

if df_original is not None:
    st.success(f"已加载 {len(df_original)} 条记录")

    # 原始数据统计
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("原始记录", len(df_original))
    with col2:
        confirmed = (df_original['评级名称'] == '确证级').sum()
        st.metric("确证级", confirmed)
    with col3:
        high = (df_original['评级名称'] == '高置信级').sum()
        st.metric("高置信级", high)
    with col4:
        probable = (df_original['评级名称'] == '推定级').sum()
        st.metric("推定级", probable)

    st.divider()

    # 四步验证筛选
    st.subheader("四步验证筛选")

    if st.button("▶ 启动四步验证", type="primary", use_container_width=True):
        with st.spinner("执行验证中..."):
            df_result = apply_four_step_filter(df_original, custom_ions, min_literature, min_frag_match)
            st.session_state.filtered = df_result

        if df_result is not None:
            st.success("验证完成!")

            # 验证结果统计
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                adopt = (df_result['验证结果'] == '采纳').sum()
                st.metric("采纳", adopt)
            with col2:
                candidate = (df_result['验证结果'] == '候选').sum()
                st.metric("候选", candidate)
            with col3:
                pending = (df_result['验证结果'] == '暂不录入').sum()
                st.metric("暂不录入", pending)
            with col4:
                st.metric("总计", len(df_result))

    # 获取筛选结果
    if 'filtered' not in st.session_state or st.session_state.filtered is None:
        st.session_state.filtered = None

    df = st.session_state.filtered

    if df is not None and len(df) > 0:
        st.divider()

        # 验证级别分布
        st.subheader("验证结果分布")

        level_dist = df['验证级别'].value_counts()
        col1, col2 = st.columns(2)

        with col1:
            st.bar_chart(level_dist)

        with col2:
            st.dataframe(
                level_dist.reset_index().rename(columns={'index': '验证级别', '验证级别': '数量'}),
                use_container_width=True
            )

        st.divider()

        # 筛选结果表格
        st.subheader(f"筛选结果: {len(df)} 条")

        display_cols = ['序号', '化合物中文名', '评级名称', '验证结果', '验证级别',
                       '文献来源数', '综合得分', '匹配碎片数']
        available = [c for c in display_cols if c in df.columns]

        df_show = df[available].sort_values(['验证结果', '综合得分'],
                                             ascending=[True, False])
        st.dataframe(df_show, use_container_width=True, height=400)

        # 详细查看
        with st.expander("查看完整列信息"):
            st.dataframe(df, use_container_width=True)

        st.divider()

        # 下载功能
        col1, col2 = st.columns(2)

        with col1:
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='验证结果', index=False)
            st.download_button(
                "📥 下载Excel",
                output.getvalue(),
                f"验证结果_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        with col2:
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                "📥 下载CSV",
                csv,
                f"验证结果_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )

        # 重置
        if st.button("重置", type="secondary"):
            st.session_state.filtered = None
            st.rerun()

else:
    st.info("请上传鉴定报告文件 (Excel或CSV格式)")

    # 四步验证说明
    st.divider()
    st.subheader("四步验证流程")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("""
        **第一步：确证级**
        🔍 诊断离子+碎片验证
        多重确认才采纳
        """)
    with col2:
        st.markdown("""
        **第二步：高置信级**
        🔍 诊断离子验证
        有匹配则采纳
        """)
    with col3:
        st.markdown("""
        **第三步：推定级**
        📚 需文献支持
        多文献+诊断离子
        """)
    with col4:
        st.markdown("""
        **第四步：提示级**
        ❌ 直接排除
        不进入报告
        """)

    st.divider()
    st.caption("支持自定义诊断离子文件上传 | 四步验证流程")
