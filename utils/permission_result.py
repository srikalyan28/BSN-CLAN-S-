from dataclasses import dataclass
from typing import Optional

@dataclass
class PermissionResult:
    """Result of a permission check"""
    allowed: bool
    reason: str
    error: Optional[str] = None
    
    @classmethod
    def allow(cls) -> 'PermissionResult':
        return cls(allowed=True, reason="Access granted")
    
    @classmethod
    def deny(cls, reason: str) -> 'PermissionResult':
        return cls(allowed=False, reason=reason)
    
    @classmethod
    def error(cls, error: str) -> 'PermissionResult':
        return cls(allowed=False, reason="An error occurred", error=error)