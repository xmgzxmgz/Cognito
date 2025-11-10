import os
from dotenv import load_dotenv

load_dotenv()


def get_env(name: str, default: str | None = None) -> str:
    """
    获取环境变量的安全方法。

    参数:
        name: 环境变量名。
        default: 当环境变量不存在时的默认值。

    返回:
        环境变量的字符串值，如果不存在则返回默认值或抛出异常。
    """
    val = os.getenv(name, default)
    if val is None:
        raise RuntimeError(f"Missing environment variable: {name}")
    return val


DB_HOST = get_env("DB_HOST", "127.0.0.1")
DB_PORT = int(get_env("DB_PORT", "3306"))
DB_USER = get_env("DB_USER", "cognito")
DB_PASSWORD = get_env("DB_PASSWORD", "cognito_pass")
DB_NAME = get_env("DB_NAME", "cognito")

BACKEND_HOST = get_env("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = int(get_env("BACKEND_PORT", "8000"))
ALLOW_ORIGINS = [s.strip() for s in get_env("ALLOW_ORIGINS", "http://localhost:5173").split(",")]