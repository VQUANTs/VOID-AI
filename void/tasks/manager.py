import uuid
from datetime import datetime


class TaskManager:

    def __init__(self, agent, max_steps=12):
        self.agent = agent
        self.max_steps = max_steps
        self.active_tasks = {}

    def create_task(self, description):
        task_id = uuid.uuid4().hex[:8]

        task = {
            "id": task_id,
            "description": description,
            "status": "created",
            "created_at": datetime.now().isoformat(),
            "steps": []
        }

        self.active_tasks[task_id] = task

        return task

    def run(self, description, conversation_id="default"):

        task = self.create_task(description)

        task["status"] = "running"

        messages = [
            {
                "role": "system",
                "content": """
You are VOID Task Manager.

Your job is to complete the user's task
using the available VOID agent tools.

Work systematically.

For complex tasks:
1. Understand the objective.
2. Break the task into useful steps.
3. Use tools when they provide real value.
4. Verify important results.
5. Give the user a concise final result.

Do not invent tool results or information.

For cybersecurity tasks, operate only within
authorized, educational, defensive, CTF, or
isolated laboratory contexts.
"""
            },
            {
                "role": "user",
                "content": description
            }
        ]

        try:

            result = self.agent.run(messages)

            task["status"] = "completed"
            task["conversation_id"] = str(conversation_id or "default")
            task["result"] = result
            task["completed_at"] = (
                datetime.now().isoformat()
            )

            return task

        except Exception as error:

            task["status"] = "failed"
            task["conversation_id"] = str(conversation_id or "default")
            task["error"] = str(error)
            task["completed_at"] = (
                datetime.now().isoformat()
            )

            raise

    def get(self, task_id):

        return self.active_tasks.get(task_id)

    def list_tasks(self):

        return list(
            self.active_tasks.values()
        )

    def cancel(self, task_id):

        task = self.active_tasks.get(task_id)

        if not task:
            return False

        if task["status"] in {
            "completed",
            "failed",
            "cancelled"
        }:
            return False

        task["status"] = "cancelled"
        task["completed_at"] = (
            datetime.now().isoformat()
        )

        return True
