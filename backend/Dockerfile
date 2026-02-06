FROM python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:0.9.30 /uv /usr/local/bin/uv

# 关键修复：安装 gcc 和编译工具
# Python 3.14 较新，pyroaring 等库需要现场编译，没有 gcc 会报错
RUN apt-get update && apt-get install -y \
    build-essential \
    libxml2-dev \
    libxslt-dev \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    shared-mime-info \
    fonts-dejavu-core \
    git \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 创建非 root 用户 (Hugging Face 安全要求)
RUN useradd -m -u 1000 user

# 创建缓存目录并授权
RUN mkdir -p /app/.cache/huggingface && \
    mkdir -p /app/.cache/sentence_transformers && \
    chown -R user:user /app

# 环境变量
ENV HF_HOME=/app/.cache/huggingface
ENV SENTENCE_TRANSFORMERS_HOME=/app/.cache/sentence_transformers
ENV PATH="/home/user/.local/bin:$PATH"

# 切换用户
USER user

# 复制依赖并安装
# 注意：此 Dockerfile 位于 backend/ 目录下，假设构建上下文也是 backend/
COPY --chown=user:user requirements.txt .
# 使用 uv 安装 Python 依赖（替换 pip，速度更快）
RUN uv pip install --system --no-cache -r requirements.txt

# 复制后端代码
COPY --chown=user:user . .

# 暴露端口
EXPOSE 7860

# 启动
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
