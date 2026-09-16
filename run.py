from void.core import VoidCore
from void.config import Config


def main():

    print(f"""
╔══════════════════════════════════╗
║                                  ║
║          V O I D  C O R E        ║
║                                  ║
║             v{Config.VERSION}             ║
║                                  ║
╚══════════════════════════════════╝

AI Core       : ON
Memory        : ON
Web           : ON
Cyber Mode    : READY
Model Router  : FOUNDATION
Agent Mode    : READY
Task Manager  : READY

Type /help
""")

    ai = VoidCore()

    agent = ai.agent
    tasks = ai.tasks

    while True:

        try:
            user = input("YOU > ").strip()

        except KeyboardInterrupt:
            print("\n")
            break

        if not user:
            continue

        if user == "/exit":
            break

        if user == "/clear":
            ai.memory.clear()
            print("VOID > Memory cleared.")
            continue

        if user == "/refresh":
            try:
                models = ai.model.refresh_models(force=True)
                print(f"VOID > Discovered {len(models)} models.")
                for item in models:
                    print(f"  {item.provider}:{item.id} [{', '.join(item.capabilities)}]")
            except Exception as e:
                print(f"VOID > Model discovery failed: {e}")
            continue

        if user == "/model":
            status = ai.model.get_status()
            print(f"ROUTE: {status['route']}")
            print(f"MODEL: {status['model']}")
            continue

        if user == "/status":
            status = ai.model.get_status()

            print("""
╔══════════════════════════════════╗
║          VOID STATUS             ║
╠══════════════════════════════════╣
║ CORE       : ONLINE              ║
║ MEMORY     : ONLINE              ║
║ MODEL      : {model:<20}║
║ PROVIDER   : {provider:<20}║
║ AGENT      : READY               ║
║ TASKS      : READY               ║
║ TOOLS      : {tools:<20}║
╚══════════════════════════════════╝
""".format(
                model=status["model"],
                provider=status["provider"],
                tools=len(agent.tools.definitions())
            ))
            continue

        if user == "/tasks":
            task_list = tasks.list_tasks()

            if not task_list:
                print("VOID > No tasks.")
                continue

            for task in task_list:
                print(
                    f"[{task['id']}] "
                    f"{task['status']} - "
                    f"{task['description']}"
                )

            continue

        if user == "/help":
            print("""
/help     Show commands
/clear    Clear conversation memory
/model    Show current model route\n/refresh  Discover models from configured gateways
/status   Show VOID system status
/agent    Run a multi-step agent task
/tasks    Show task history
/exit     Exit VOID

Normal chat:

Explain buffer overflow like I'm learning cybersecurity.

Agent Mode:

/agent <task>

Task Manager:

/task <task>

Example:

/task Research the latest Python version,
compare it with the previous release,
and summarize the important changes.

Agent tools:
- web_search
- memory_search
- knowledge_search
- system_info
""")
            continue

        try:

            if user.startswith("/task"):

                description = user[5:].strip()

                if not description:
                    print(
                        "VOID > Usage: /task <task>"
                    )
                    continue

                print(
                    "\nVOID TASK > Starting..."
                )

                task = tasks.run(
                    description,
                    conversation_id="cli"
                )

                print(
                    f"\nTASK ID: {task['id']}"
                )

                print(
                    f"STATUS: {task['status']}"
                )

                print(
                    "\nVOID TASK >"
                )

                print(
                    task["result"]
                )

                print()

                ai.memory.add(
                    "user",
                    "[TASK] " + description
                )

                ai.memory.add(
                    "assistant",
                    task["result"]
                )

                continue

            if user.startswith("/agent"):

                task = user[6:].strip()

                if not task:
                    print(
                        "VOID > Usage: /agent <task>"
                    )
                    continue

                print(
                    "\nVOID AGENT > Starting task..."
                )

                messages = [
                    {
                        "role": "system",
                        "content": Config.SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": task
                    }
                ]

                answer = agent.run(
                    messages
                )

                ai.memory.add(
                    "user",
                    "[AGENT] " + task
                )

                ai.memory.add(
                    "assistant",
                    answer
                )

                print(
                    "\nVOID AGENT >"
                )

                print(answer)
                print()

                continue

            print(
                "\nVOID > ",
                end="",
                flush=True
            )

            answer = ai.ask(user)

            print(answer)
            print()

        except Exception as e:

            print(
                f"\nVOID ERROR: {e}\n"
            )


if __name__ == "__main__":
    main()
