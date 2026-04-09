"""Authorization and security checks for task operations."""

from fastapi import HTTPException


class TaskAuthorizationManager:
    """Manages authorization checks for task operations."""

    @staticmethod
    def verify_user_org_scoping(user_org_id: str, task_org_id: str) -> None:
        """
        Verify that the user's organization matches the task's organization.

        Args:
            user_org_id: The user's organization ID
            task_org_id: The task's organization ID

        Raises:
            HTTPException: If organizations don't match (403 Forbidden)
        """
        if user_org_id != task_org_id:
            raise HTTPException(
                status_code=403,
                detail="You do not have access to this task"
            )

    @staticmethod
    def verify_project_access(user: dict, project_id: str) -> None:
        """
        Verify that project_id is provided and valid.

        Args:
            user: The authenticated user dict
            project_id: The project ID to verify

        Raises:
            HTTPException: If project_id is missing or invalid (400 Bad Request)
        """
        if not project_id:
            raise HTTPException(
                status_code=400,
                detail="project_id is required"
            )
