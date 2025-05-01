import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase_init import supabase_client

# Define the security scheme
bearer_scheme = HTTPBearer()

# Update the function signature to use Security and HTTPAuthorizationCredentials
async def get_authenticated_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> str:
    # credentials object has .scheme and .credentials attributes
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, # Use status codes
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        user_response = supabase_client.auth.get_user(token)
        # Explicitly check if the response object itself is valid
        if user_response and user_response.user:
            return user_response.user.id
        else:
            # This case might occur if the token is invalid, expired, or the user doesn't exist
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, # Use status codes
                detail="Invalid token or user not found",
                headers={'WWW-Authenticate': 'Bearer error="invalid_token"'},
            )
    except Exception as e:
        # Log the specific error for debugging
        print(f"Authentication error: {e}")
        # Distinguish between client-side token issues and server-side validation issues
        if "Invalid Refresh Token" in str(e) or "JWT" in str(e).upper(): # Check for common token errors
             raise HTTPException(
                 status_code=status.HTTP_401_UNAUTHORIZED, # Use status codes
                 detail="Invalid or expired token",
                 headers={'WWW-Authenticate': 'Bearer error="invalid_token"'},
                )
        else:
             # Catch-all for other auth-related errors (network issues, service down)
             raise HTTPException(
                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, # Use status codes
                 detail="Authentication service error"
             ) 