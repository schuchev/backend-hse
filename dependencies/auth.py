from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from services.auth import AuthService

security = HTTPBearer(auto_error=False)


async def get_current_account(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = None
    if credentials:
        token = credentials.credentials
    else:
        token = request.cookies.get("access_token")
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    account = await AuthService.get_current_account(token)
    if not account:
        raise HTTPException(status_code=403, detail="Invalid token or account blocked")
    return account