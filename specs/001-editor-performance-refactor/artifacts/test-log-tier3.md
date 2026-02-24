# Tier-3 Full Regression Log

## 执行时间
- 2026-02-24

## Command
```bash
./scripts/run-all-tests.sh
```

## 结果摘要
- 总体：`FAILED`
- Pytest 汇总：`57 failed, 509 passed, 2 skipped`
- 覆盖率门槛：`61.36% < 80%`（触发 fail-under）
- 全量门禁结论：`NO-GO`

## 主要失败簇
- 大量 integration 用例出现 `httpx.ConnectError: [SSL: UNEXPECTED_EOF_WHILE_READING]`，集中在需要真实远端链路/云端数据的场景。
- 部分 RBAC/Process 相关用例返回 `404 Manuscript not found` 与断言不一致。
- 个别业务用例（如 DOI 注册）出现 `500`。

## 影响判断
- Feature 定向改动链路（US1/US2/US3）在 Tier-1/2 均通过。
- 当前 Tier-3 失败不满足发布门禁，需先收敛全量失败簇后再执行 release closure。
