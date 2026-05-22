"""门户业务层统一异常（由 FastAPI 路由映射为 HTTPException）。"""


class PortalError(Exception):
    """业务校验或外部依赖失败；携带 HTTP 语义的状态码与文案。"""

    def __init__(self, detail: str, status_code: int = 400) -> None:
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)
