# Stub for Phase 3 Policy Service
class PolicyService:
    @staticmethod
    def check_dpr_permission(user_role: str, action: str) -> bool:
        """Stub: Always allow for now"""
        return True
    
    @staticmethod
    def validate_dpr_state(dpr_status: str) -> bool:
        """Stub: Always valid for now"""
        return True

policy_service = PolicyService()
