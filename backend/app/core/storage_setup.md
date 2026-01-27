# Supabase Storage & Docker Setup

## 1. Storage Buckets
必须创建以下 Bucket 并配置权限：

### `manuscripts` (Private)
- **RLS 策略**:
  - `SELECT`: 仅限作者本人、关联编辑及持有有效 Token 的审稿人。
  - `INSERT`: 仅限已登录作者。
  - `UPDATE`: 仅限关联编辑或作者本人。

### `plagiarism-reports` (Private)
- **RLS 策略**:
  - 仅限编辑及主编 (Editor-in-Chief)。

## 2. Docker 国内镜像源 (Arch Linux / Linux)
在执行 Docker 任务前，请确保 `/etc/docker/daemon.json` 包含以下配置：

```json
{
  "registry-mirrors": [
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com",
    "https://docker.mirrors.ustc.edu.cn"
  ]
}
```

配置后重启 Docker 服务：
`sudo systemctl restart docker`
