from pydantic import BaseModel


class RegisterIn(BaseModel):
    email: str
    password: str
    name: str
    role: str = "candidate"


class LoginIn(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    role: str


class TokenOut(BaseModel):
    token: str
    user: UserOut
