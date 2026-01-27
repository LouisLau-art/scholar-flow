# Research: ScholarFlow Core Workflow

## 决策记录

### 1. AI 解析失败回退 (Fallback Strategy)
- **Decision**: 允许作者手动填写所有字段。
- **Rationale**: 考虑到 AI 提取的不确定性，手动填表是确保流程不中断的最小必要代价，符合“效率至上”原则。

### 2. 质检不通过处理 (Editorial Rejection)
- **Decision**: 退回给作者进行修改。
- **Rationale**: 学术投稿常见流程，允许修正元数据或重传 PDF 优于直接拒稿，利于系统留存率。

### 3. 审稿人免登录 Token 安全 (Security)
- **Decision**: 系统生成随机高强度 Token + 14 天有效期。
- **Rationale**: 14 天足以覆盖标准审稿周期。随机 Token 避免了 ID 遍历攻击，比明文参数更安全。
- **Implementation**: 存储在 `ReviewReports` 表中，关联 `expiry_date`。

### 4. 财务确认逻辑 (Financial Flow)
- **Decision**: 财务人员在后台手动点击“确认到账”。
- **Rationale**: “拒绝过度工程”。初期不集成银行或支付网关 API，手动标记是最快实现业务闭环的方案。

### 5. 审稿人邀请机制 (Reviewer Invitation)
- **Decision**: 编辑从 AI 推荐列表中手动点击“邀请”发送。
- **Rationale**: 尊重编辑的决策权，防止 AI 自动邀请导致的低质量评审或学术骚扰。

### 6. PDF 预览加载方案
- **Decision**: 使用 Supabase Storage 公共 URL (配合 RLS) 或签名的私有 URL。
- **Rationale**: 审稿人需要预览 PDF，考虑到 Token 访问的特殊性，将使用基于稿件 ID 的带签名 URL。