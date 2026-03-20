from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

class RegisterRequest(BaseModel):
    login: str
    password: str

class LoginRequest(BaseModel):
    login: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str


@router.post("/register")
async def register(req: RegisterRequest):
    try:
        user_id = await AuthService.register(req.login, req.password)
        return {"user_id": user_id, "message": "User created successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(response: Response, req: LoginRequest):
    token = await AuthService.login(req.login, req.password)
    if token is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=1800, 
        secure=False, 
        samesite="lax"
    )
    return {"access_token": token, "token_type": "bearer"}