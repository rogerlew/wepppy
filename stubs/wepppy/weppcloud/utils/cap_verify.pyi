from typing import Any, Dict

class CapVerificationError(RuntimeError):
    pass

def verify_cap_token(token: str) -> Dict[str, Any]: ...
