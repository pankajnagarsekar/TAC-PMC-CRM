import logging
from typing import Callable, Any, Dict, Optional
from fastapi import BackgroundTasks
from core.config import settings

logger = logging.getLogger(__name__)

class JobOrchestrator:
    """
    Abstraction layer to switch between FastAPI BackgroundTasks (sync/thread) 
    and Celery (distributed queue) without changing the endpoint contract.
    """
    
    @staticmethod
    def enqueue(
        task_func: Callable,
        celery_task: Any = None,
        background_tasks: Optional[BackgroundTasks] = None,
        *args: Any,
        **kwargs: Any
    ) -> str:
        """
        Enqueue a task.
        
        Args:
            task_func: The actual function to run (for BackgroundTasks)
            celery_task: The Celery task object (e.g. my_task.delay)
            background_tasks: FastAPI BackgroundTasks object from request
            args: Positional arguments for the task
            kwargs: Keyword arguments for the task
            
        Returns:
            job_id: A string representing the job ID
        """
        if settings.USE_CELERY and celery_task:
            logger.info(f"Enqueuing task {celery_task.name} via Celery")
            result = celery_task.delay(*args, **kwargs)
            return str(result.id)
        
        elif background_tasks:
            logger.info(f"Enqueuing task {task_func.__name__} via FastAPI BackgroundTasks")
            background_tasks.add_task(task_func, *args, **kwargs)
            return "local_background_job"
            
        else:
            # Fallback to direct execution (blocking) if no background context provided
            logger.warning(f"No background context, executing task {task_func.__name__} synchronously")
            task_func(*args, **kwargs)
            return "sync_execution"

job_orchestrator = JobOrchestrator()
