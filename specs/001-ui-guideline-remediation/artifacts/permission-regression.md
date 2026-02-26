# FR-010 Permission Regression Check (Analyze Remediation)

Date: 2026-02-26

## Scope

Feature `001-ui-guideline-remediation` only touches frontend UI behavior and documentation artifacts.

## Checks

1. Backend permission API surface: no feature-scoped change required for this remediation.
2. Role visibility guard baseline test:

```bash
cd frontend
bun run test:run tests/unit/rbac-visibility.test.ts
```

Result: `1 file / 5 tests passed`.

3. Project tier-1 regression:

```bash
cd /root/scholar-flow
./scripts/test-fast.sh
```

Result: `PASS`.

## Conclusion

- FR-010 “不改变既有业务权限规则”在本次范围内保持成立。
- 若后续在同一 feature 增加后端接口改造，必须补充后端鉴权集成测试作为追加证据。
