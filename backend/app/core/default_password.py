import os


DEFAULT_BOOTSTRAP_PASSWORD = "12345678"


def get_default_bootstrap_password() -> str:
    """
    开发/UAT 阶段统一的默认口令。

    中文注释：
    - 优先允许通过环境变量覆盖，便于后续切换；
    - 未配置时固定回落到产品当前要求的 12345678。
    """

    value = str(os.environ.get("DEFAULT_BOOTSTRAP_PASSWORD") or "").strip()
    return value or DEFAULT_BOOTSTRAP_PASSWORD
