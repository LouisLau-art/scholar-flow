# 2026-02-26 Editor 性能体检与索引补齐报告

## 执行范围
- API 基线复采：`editor_detail` / `editor_process` / `editor_workspace` / `editor_pipeline`
- 数据库体检：`supabase inspect db {db-stats,table-stats,index-stats,calls}`
- 云端迁移核对与补齐：`supabase migration list --linked` + `supabase db push --linked`

## 关键发现
1. 远端 Supabase 未应用 `20260224173000_editor_performance_indexes.sql`（本地与远端 migration list 不一致）。
2. 已执行云端补齐，复合索引与 trgm 索引均已创建成功。
3. 当前数据量较小（`manuscripts` 约 90 行），DB 命中率高（Index Hit Rate 0.99 / Table Hit Rate 1.00）；链路慢点更偏向跨区域网络、HF 冷启动和后端聚合逻辑，而不是纯数据库扫描。

## 基线对比（p95 / ms）

| Scenario | 2026-02-26 post-fixes | post-backend-hardening | post-index-push |
| --- | ---: | ---: | ---: |
| editor_detail | 6535 | 4137 | 4186 |
| editor_process | 3187 | 3215 | 3687 |
| editor_workspace | 3646 | 3258 | 3646 |
| editor_pipeline | 5052 | 4765 | 5554 |

说明：
- 采样数均为 8，短窗口存在抖动；本批次结果用于“方向判断”，不作为最终容量结论。
- `editor_detail` 在两轮后都显著优于 2/26 早先采样；其余链路波动较大，符合跨区域网络与运行时冷启动特征。

## 执行证据
- 新增基线文件：
  - `baseline-2026-02-26-post-backend-hardening-editor_{detail,process,workspace,pipeline}.json`
  - `baseline-2026-02-26-post-index-push-editor_{detail,process,workspace,pipeline}.json`
- 云端迁移状态：`20260224173000` 已在 remote 标记为已执行。

## 下一步建议（性能）
1. 把 `editor_pipeline` 做 10~30 秒短缓存 + 强制刷新旁路（与 process/workspace 同口径）。
2. 对 `editor_pipeline` 和 `editor_detail` 做分段计时日志（DB/聚合/序列化）以拆分后端耗时。
3. 统一后端和 DB 区域，或为中国用户提供大陆可达链路（当前跨区域 RTT 对 p95 影响大）。
