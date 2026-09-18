from dataclasses import dataclass
from .resolver import decision

@dataclass
class ACLDenied(PermissionError):
    action: str
    reason: str
    def __str__(self):
        return f"Accès refusé ({self.action}) : {self.reason}"

def require(user_id, action, **kwargs):
    result = decision(user_id, action, **kwargs)
    if not result.allowed:
        raise ACLDenied(result.action, result.reason)
    return result
