# API Contracts: System Integrity & Auth

## 1. 用户与资料 (User Profile)
- `GET /api/v1/user/profile`: 获取当前登录用户详情。
- `PUT /api/v1/user/profile`: 更新姓名、机构、研究领域。
- `GET /api/v1/user/notifications`: 获取系统消息。

## 2. 统计看板 (Dashboard Stats)
- `GET /api/v1/stats/author`: 作者视角统计（投稿数、接受率）。
- `GET /api/v1/stats/editor`: 编辑视角统计（待分配、逾期）。
- `GET /api/v1/stats/system`: 首页大数字统计（总下载量、总引用）。

## 3. 期刊与学科 (Journal Portfolio)
- `GET /api/v1/public/topics`: 获取所有学科分类。
- `GET /api/v1/public/announcements`: 获取系统公告。

## 4. 稿件交互扩展 (Manuscript Extensions)
- `POST /api/v1/manuscripts/upload`: 投稿上传。
- `GET /api/v1/manuscripts/search`: 动态检索已发表文章。
- `GET /api/v1/manuscripts/history`: 查看稿件流转日志 (Planned)。