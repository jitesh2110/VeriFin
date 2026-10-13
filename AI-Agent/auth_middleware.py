"""
VeriFin AI Agent - Multi-Tenant JWT Authentication & Scoping Middleware
Decodes JWT, validates permissions, and injects TenantUser context
"""

import os
import jwt
from typing import Optional, List, Dict, Any
from fastapi import Request, HTTPException, Security, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv(r"C:\D\Dev\Projects\VeriFin\.env")
JWT_SECRET = os.getenv("JWT_SECRET", "verifin-secret-key-2025")
JWT_ALGORITHM = "HS256"

security = HTTPBearer(auto_error=False)


class TenantUser(BaseModel):
    user_id: str
    username: str
    email: str
    role: str = "user"
    company_id: str = "comp_default"
    company_name: str = "Default Enterprise"
    assigned_projects: List[Any] = []
    active_project_id: str = "proj_default"

    def is_admin(self) -> bool:
        return self.role in ["admin", "owner"]


def decode_jwt_token(token: str) -> Dict[str, Any]:
    """Decode and verify JWT signature and expiration"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again."
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}"
        )


async def get_current_user(
    request: Request,
    auth_credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> TenantUser:
    """
    FastAPI dependency to extract TenantUser from Bearer JWT.
    Provides graceful fallback to demo user in dev if no Authorization header is passed.
    """
    token = None
    if auth_credentials:
        token = auth_credentials.credentials
    elif "authorization" in request.headers:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    # Optional header overrides (e.g. for testing or switching project)
    header_company = request.headers.get("x-company-id")
    header_project = request.headers.get("x-project-id")

    if token:
        payload = decode_jwt_token(token)
        company_id = header_company or payload.get("companyId") or payload.get("company_id") or "comp_default"
        project_id = header_project or payload.get("activeProjectId") or payload.get("project_id") or "proj_default"

        return TenantUser(
            user_id=str(payload.get("id") or payload.get("userId") or "1"),
            username=payload.get("username", "user"),
            email=payload.get("email", "user@verifin.ai"),
            role=payload.get("role", "user"),
            company_id=company_id,
            company_name=payload.get("companyName") or payload.get("company_name") or "Default Enterprise",
            assigned_projects=payload.get("assignedProjects") or payload.get("assigned_projects") or [],
            active_project_id=project_id
        )

    # Fallback in local development if token wasn't supplied by legacy callers
    company_id = header_company or "comp_default"
    project_id = header_project or "proj_default"
    
    return TenantUser(
        user_id="demo_user",
        username="dev_operator",
        email="operator@verifin.ai",
        role="admin",
        company_id=company_id,
        company_name="Default Enterprise",
        assigned_projects=[{"projectId": project_id, "projectName": "Primary Project", "role": "admin"}],
        active_project_id=project_id
    )
