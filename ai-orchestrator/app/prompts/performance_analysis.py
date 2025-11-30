"""Performance analysis prompt templates.

This module provides prompt templates for AI-powered performance analysis
using Gemini 2.5 Pro. Includes templates for:
- Performance analysis and insights generation
- Anomaly detection and root cause analysis
- Actionable recommendations

Requirements: 需求 8.2, 8.3, 8.4
"""

PERFORMANCE_ANALYSIS_SYSTEM_PROMPT = """You are an expert digital advertising analyst specializing in Meta and TikTok ads.
Your role is to analyze advertising performance data and provide actionable insights.

When analyzing data, consider:
1. Key performance indicators (KPIs): CTR, CPC, CPA, ROAS, conversion rate
2. Industry benchmarks for comparison
3. Trends over time (improving, declining, stable)
4. Anomalies that need attention
5. Actionable recommendations

Always provide:
- Clear, data-driven insights
- Specific recommendations with expected impact
- Priority ranking for actions
- Risk assessment for any changes

Use Chinese for all responses. Be concise but thorough."""

PERFORMANCE_ANALYSIS_USER_PROMPT = """请分析以下广告投放数据并提供洞察：

## 数据概览
- 时间范围: {date_range}
- 总花费: ${total_spend}
- 总展示: {total_impressions:,}
- 总点击: {total_clicks:,}
- 总转化: {total_conversions:,}
- 总收入: ${total_revenue}

## 核心指标
- CTR (点击率): {ctr}%
- CPC (单次点击成本): ${cpc}
- CPA (单次转化成本): ${cpa}
- ROAS (广告支出回报率): {roas}

## 趋势数据
{trend_data}

## 表现最好的广告
{top_performers}

## 表现最差的广告
{bottom_performers}

请提供：
1. 整体表现评估
2. 关键洞察（至少3条）
3. 具体优化建议（至少3条）
4. 需要关注的风险点
5. 下一步行动计划"""

ANOMALY_DETECTION_SYSTEM_PROMPT = """You are an expert at detecting anomalies in advertising performance data.
Your role is to identify unusual patterns that may indicate problems or opportunities.

Anomaly types to detect:
1. Sudden CTR drops (> 20% decrease)
2. CPA spikes (> 30% increase)
3. Spend anomalies (unusual spending patterns)
4. Conversion rate changes
5. ROAS fluctuations

For each anomaly:
- Assess severity (info, warning, critical)
- Identify potential root causes
- Suggest remediation actions

Use Chinese for all responses."""

ANOMALY_DETECTION_USER_PROMPT = """请检测以下数据中的异常：

## 当前数据 (最近 {current_period})
- CTR: {current_ctr}%
- CPC: ${current_cpc}
- CPA: ${current_cpa}
- ROAS: {current_roas}
- 花费: ${current_spend}

## 历史基准 (过去 {baseline_period})
- CTR: {baseline_ctr}%
- CPC: ${baseline_cpc}
- CPA: ${baseline_cpa}
- ROAS: {baseline_roas}
- 平均花费: ${baseline_spend}

## 变化幅度
- CTR 变化: {ctr_change}%
- CPC 变化: {cpc_change}%
- CPA 变化: {cpa_change}%
- ROAS 变化: {roas_change}%
- 花费变化: {spend_change}%

请识别所有异常并提供：
1. 异常类型和严重程度
2. 可能的原因分析
3. 建议的修复措施"""

INSUFFICIENT_DATA_MESSAGE = """📊 数据不足

当前数据量不足以进行有效分析：
- 当前数据天数: {days_available} 天
- 最低要求: {min_days} 天
- 当前展示量: {impressions:,}
- 最低要求: {min_impressions:,}

建议：
1. 等待更多数据积累（建议至少 7 天）
2. 确保广告已正常投放
3. 检查广告账户是否正确绑定

如有疑问，请联系客服获取帮助。"""
