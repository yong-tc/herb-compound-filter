AIGC:
ContentProducer: Minimax Agent AI
ContentPropagator: Minimax Agent AI
Label: AIGC
ProduceID: 3f12723e62bbe90f12f1d4100fb1ca52
PropagateID: 3f12723e62bbe90f12f1d4100fb1ca52
ReservedCode1: 30450220756fffb7f11a06bec0581ac3a8c3989b3f6ea8847612bcf2af35c91d5ba24f8e022100985fd3b64a3a985848ff7b9f2ce6012ba6783383ab8a6ca55bf02fa66ffd9dfd
ReservedCode2: 3046022100ad1d36b43709f23692e25ba8858cda35a756c3eabde6a47771b3cf34363d6928022100adf9d76cbf73583dbe0220a31c841302883f43bf12ccbd477740fa28a93b4e23
中药化合物鉴定报告筛选工具
基于 Streamlit 的 Web 端筛选工具，适用于所有药材的鉴定报告。

功能特点
通用设计：适用于任何药材的鉴定报告筛选
快速预设：14 种预设筛选模式
自定义筛选：多条件组合筛选
统计可视化：评级分布、类型分布图表
批量导出：完整报告 + 精简摘要
项目结构
tcm-filter/
├── app.py              # Streamlit Web应用 (主入口)
├── report_filter.py    # 命令行版本
├── requirements.txt    # Python依赖
├── README.md           # 说明文档
└── .gitignore          # Git忽略规则
在线部署 (Streamlit Cloud)
1.
将代码推送到 GitHub
2.
访问 share.streamlit.io
3.
连接 GitHub 仓库
4.
选择 app.py 作为主文件
5.
点击 Deploy
本地运行
bash
# 安装依赖
pip install -r requirements.txt

# 运行
streamlit run app.py
使用方法
1. 加载报告
上传鉴定报告文件 (Excel/CSV)
或选择本地报告文件
2. 快速筛选
点击预设按钮快速筛选：

序号	预设名称	说明
1	高置信模式	确证级+高置信级, ppm≤20, 有碎片
2	中等置信	推定级+, ppm≤50
3	宽松模式	ppm≤100, 有碎片
4	仅确证级	确证级
5	仅黄酮类	ppm≤30, 黄酮/黄酮醇/黄烷酮
6	仅生物碱	ppm≤30, 生物碱
7	仅萜类	ppm≤30, 萜/单萜/倍半萜/二萜/三萜
8	仅酚酸类	ppm≤30, 酚酸/苯甲酸
9	仅糖类	ppm≤30, 糖/糖苷/多糖
10	确证+高置信无碎片	高置信级, 无碎片
11	高质量无碎片	ppm≤10, 无碎片
12	综合评分高	得分≥85
13	低ppm精准匹配	ppm≤5, 有碎片
14	中等碎片匹配	碎片数3-10个
3. 自定义筛选
评级筛选
ppm范围
综合得分
碎片数
关键词包含/排除
4. 下载结果
完整报告 (Excel，双Sheet)
精简摘要 (Excel)
系统要求
Python 3.8+
streamlit >= 1.20.0
pandas >= 1.5.0
openpyxl >= 3.0.0
许可证
MIT License
