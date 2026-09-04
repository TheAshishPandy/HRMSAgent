from fastapi import HTTPException


def conflict(code: str, detail: str) -> HTTPException:
    return HTTPException(status_code=409, detail={"code": code, "message": detail})
