"""
Task queue manager for handling concurrent requests
Prevents bot from hanging under heavy load
"""

import asyncio
from typing import Callable, Any
from utils.logger import logger
from config import MAX_CONCURRENT_DOWNLOADS

class TaskQueue:
    """
    Asyncio-based task queue with concurrency control
    """
    
    def __init__(self, max_concurrent: int = MAX_CONCURRENT_DOWNLOADS):
        self.queue = asyncio.Queue()
        self.max_concurrent = max_concurrent
        self.active_tasks = 0
        self.semaphore = asyncio.Semaphore(max_concurrent)
        logger.info(f"TaskQueue initialized with max_concurrent={max_concurrent}")
    
    async def add_task(self, task_func: Callable, *args, **kwargs) -> Any:
        """
        Add a task to the queue and wait for completion
        """
        async with self.semaphore:
            self.active_tasks += 1
            logger.info(f"Task started. Active tasks: {self.active_tasks}/{self.max_concurrent}")
            
            try:
                result = await task_func(*args, **kwargs)
                return result
            except Exception as e:
                logger.error(f"Task failed: {e}", exc_info=True)
                raise
            finally:
                self.active_tasks -= 1
                logger.info(f"Task completed. Active tasks: {self.active_tasks}/{self.max_concurrent}")
    
    def get_queue_status(self) -> dict:
        """
        Get current queue status
        """
        return {
            "queued": self.queue.qsize(),
            "active": self.active_tasks,
            "max_concurrent": self.max_concurrent
        }

# Global task queue instance
task_queue = TaskQueue()