# -*- coding: utf-8 -*-
"""筛选引擎模块"""

import pandas as pd
import re


class FilterEngine:
    """筛选引擎类"""
    
    def __init__(self, df):
        self.df = df
    
    def apply_preset(self, preset_name):
        """应用预设筛选"""
        data = self.df.copy()
        
        presets = {
            '高置信模式': self._high_confidence_filter,
            '中等置信模式': self._medium_confidence_filter,
            '宽松模式': self._loose_filter,
            '确证级': self._confirmed_filter,
            '仅黄酮类': lambda d: self._compound_type_filter(d, ['黄酮', '黄酮醇', '黄烷酮']),
            '仅生物碱': lambda d: self._compound_type_filter(d, ['生物碱', '碱']),
            '仅萜类': lambda d: self._compound_type_filter(d, ['萜', '萜类', 'terpene'])
        }
        
        if preset_name in presets:
            return presets[preset_name](data)
        return data
    
    def _high_confidence_filter(self, df):
        """高置信模式"""
        if '评级名称' in df.columns:
            df = df[df['评级名称'].isin(['确证级', '高置信级'])]
        if 'ppm' in df.columns:
            df = df[df['ppm'] <= 20]
        if '匹配碎片数' in df.columns:
            df = df[df['匹配碎片数'] > 0]
        return df
    
    def _medium_confidence_filter(self, df):
        """中等置信模式"""
        if '评级名称' in df.columns:
            df = df[df['评级名称'].isin(['确证级', '高置信级', '推定级'])]
        if 'ppm' in df.columns:
            df = df[df['ppm'] <= 50]
        return df
    
    def _loose_filter(self, df):
        """宽松模式"""
        if 'ppm' in df.columns:
            df = df[df['ppm'] <= 100]
        if '匹配碎片数' in df.columns:
            df = df[df['匹配碎片数'] > 0]
        return df
    
    def _confirmed_filter(self, df):
        """仅确证级"""
        if '评级名称' in df.columns:
            df = df[df['评级名称'] == '确证级']
        return df
    
    def _compound_type_filter(self, df, keywords):
        """化合物类型筛选"""
        if 'ppm' in df.columns:
            df = df[df['ppm'] <= 30]
        
        cols = []
        if '化合物中文名' in df.columns:
            cols.append('化合物中文名')
        if '化合物类型' in df.columns:
            cols.append('化合物类型')
        
        if cols:
            mask = pd.Series([False] * len(df))
            for col in cols:
                for kw in keywords:
                    mask = mask | df[col].str.contains(kw, na=False, case=False)
            df = df[mask]
        
        return df
    
    def apply_conditions(self, conditions):
        """应用筛选条件"""
        df = self.df.copy()
        
        # 药材筛选
        if 'herb' in conditions and conditions['herb']:
            if '药材名称' in df.columns:
                df = df[df['药材名称'].isin(conditions['herb'])]
        
        # 评级筛选
        if 'rating' in conditions and conditions['rating']:
            if '评级名称' in df.columns:
                df = df[df['评级名称'].isin(conditions['rating'])]
        
        # ppm范围
        if 'ppm_range' in conditions:
            min_ppm, max_ppm = conditions['ppm_range']
            if 'ppm' in df.columns:
                df = df[(df['ppm'] >= min_ppm) & (df['ppm'] <= max_ppm)]
        
        # 最低得分
        if 'min_score' in conditions:
            if '综合得分' in df.columns:
                df = df[df['综合得分'] >= conditions['min_score']]
        
        # 碎片匹配
        if 'has_fragment' in conditions:
            if '匹配碎片数' in df.columns:
                if conditions['has_fragment']:
                    df = df[df['匹配碎片数'] > 0]
                else:
                    df = df[df['匹配碎片数'] == 0]
        
        # 包含关键词
        if 'keywords' in conditions and conditions['keywords']:
            name_cols = []
            if '化合物中文名' in df.columns:
                name_cols.append('化合物中文名')
            if '化合物英文名' in df.columns:
                name_cols.append('化合物英文名')
            
            if name_cols:
                mask = pd.Series([False] * len(df))
                for kw in conditions['keywords']:
                    for col in name_cols:
                        mask = mask | df[col].str.contains(kw, na=False, case=False)
                df = df[mask]
        
        # 排除关键词
        if 'exclude_keywords' in conditions and conditions['exclude_keywords']:
            name_cols = []
            if '化合物中文名' in df.columns:
                name_cols.append('化合物中文名')
            if '化合物英文名' in df.columns:
                name_cols.append('化合物英文名')
            
            if name_cols:
                mask = pd.Series([True] * len(df))
                for kw in conditions['exclude_keywords']:
                    for col in name_cols:
                        mask = mask & ~df[col].str.contains(kw, na=False, case=False)
                df = df[mask]
        
        # 化合物类型
        if 'compound_type' in conditions:
            if '化合物类型' in df.columns:
                df = df[df['化合物类型'].str.contains(conditions['compound_type'], na=False)]
        
        # 分子量范围
        if 'mw_range' in conditions:
            min_mw, max_mw = conditions['mw_range']
            if '匹配质量数' in df.columns:
                df = df[(df['匹配质量数'] >= min_mw) & (df['匹配质量数'] <= max_mw)]
        
        return df


def create_summary_stats(df):
    """创建统计摘要"""
    stats = {}
    
    stats['total'] = len(df)
    
    if '评级名称' in df.columns:
        stats['rating_distribution'] = df['评级名称'].value_counts().to_dict()
    
    if '匹配碎片数' in df.columns:
        stats['has_fragment'] = int((df['匹配碎片数'] > 0).sum())
        stats['no_fragment'] = int((df['匹配碎片数'] == 0).sum())
    
    if 'ppm' in df.columns:
        stats['ppm_mean'] = df['ppm'].mean()
        stats['ppm_median'] = df['ppm'].median()
        stats['ppm_min'] = df['ppm'].min()
        stats['ppm_max'] = df['ppm'].max()
    
    if '综合得分' in df.columns:
        stats['score_mean'] = df['综合得分'].mean()
        stats['score_max'] = df['综合得分'].max()
    
    if '化合物类型' in df.columns:
        stats['top_types'] = df['化合物类型'].value_counts().head(10).to_dict()
    
    return stats
