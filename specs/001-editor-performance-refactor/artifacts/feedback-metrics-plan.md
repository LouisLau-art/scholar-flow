# 7-Day Feedback Metrics Plan (SC-005)

## 目标
验证 SC-005：上线后连续 7 天内，编辑端“页面长时间转圈/加载过慢”反馈量较优化前窗口下降 50%+。

## 指标定义
- 主指标：`slow_loading_feedback_count`
- 统计口径：仅计入编辑端（`/editor/*`）并明确包含以下关键词之一：
  - `转圈`
  - `加载慢`
  - `卡住`
  - `页面很卡`
- 去重规则：同一用户同一稿件 30 分钟内重复反馈记 1 次。

## 数据源
- UAT/线上反馈表单（结构化标签）
- 内部工单（按标签 `editor-performance`）
- Sentry issue/transaction 注释（仅用于佐证，不单独计数）

## 对比窗口
- 基线窗口（before）：上线前连续 7 天
- 观察窗口（after）：上线后连续 7 天

## 计算公式
```text
delta_ratio = (after_count - before_count) / before_count
success_if = (before_count > 0) AND (after_count <= before_count * 0.5)
```

## 发布后执行节奏
1. D+1：确认标签与埋点一致性
2. D+3：中期抽查，识别异常峰值
3. D+7：输出最终对比报告（`feedback-7day-report.md`）
