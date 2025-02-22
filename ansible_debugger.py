import ansible_runner
import click
import logging
import time
import json
from rich.console import Console
import subprocess


logging.basicConfig(filename="debugsible.log", level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")
console = Console()

MAX_RETRIES = 3 
BACKOFF_TIME = 2
DEBUG_SESSION_FILE = "debug_session.json"

try:
    with open(DEBUG_SESSION_FILE, "r") as file:
        debug_session = json.load(file)
except (FileNotFoundError, json.JSONDecodeError):
    debug_session = []

def save_debug_session():
    with open(DEBUG_SESSION_FILE, "w") as file:
        json.dump(debug_session, file, indent=4)

def log_task(task_name, status, command, stdout="", stderr="", return_code=None, modified=False):
    task_log = {
        "task": task_name,
        "status": status,
        "command": " ".join(command),
        "stdout": stdout.strip(),
        "stderr": stderr.strip(),
        "return_code": return_code,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "modified": modified
    }
    debug_session.append(task_log)
    save_debug_session()

def run_task(task_name, inventory):
    result = ansible_runner.interface.run(private_data_dir='.', playbook=task_name, inventory=inventory, quiet=True)
    return result

def run_playbook_step_by_step(playbook, inventory):
    console.print(f"[bold cyan]Starting playbook:[/bold cyan] {playbook}")

    runner = ansible_runner.interface.run(private_data_dir='.', playbook=playbook, inventory=inventory, quiet=True)

    task_list = []
    for event in runner.events:
        if event['event'] == 'runner_on_start':
            task = event['event_data'].get('task', 'Unknown Task')
            task_list.append(task)

    if task_list:
        console.print("[bold cyan]Available Tasks:[/bold cyan]")
        for i, task in enumerate(task_list, start=1):
            console.print(f"{i}. {task}")

        selected_tasks = console.input("[bold yellow]Enter task numbers to run (comma-separated) or press Enter for all:[/bold yellow] ")
        if selected_tasks:
            selected_tasks = {task_list[int(i)-1] for i in selected_tasks.split(',') if i.isdigit() and 1 <= int(i) <= len(task_list)}
        else:
            selected_tasks = set(task_list)  

    for event in runner.events:
        task = event['event_data'].get('task', 'Unknown Task')
        if task not in selected_tasks:
            continue  

        event_type = event['event']
        if event_type not in ['runner_on_start', 'runner_on_ok', 'runner_on_failed']:
            continue  

        task = event['event_data'].get('task', 'Unknown Task')
        res_data = event['event_data'].get('res', {})  
        cmd = res_data.get('cmd', [])  

        if event_type == 'runner_on_start':
            console.print(f"\n➡ [bold yellow]Running Task:[/bold yellow] {task}")
            logging.info(f"Running Task: {task}")
            user_input = console.input("[bold green]Press Enter to continue or type 'exit' to stop:[/bold green] ")
            if user_input.lower() == 'exit':
                console.print("[bold red]❌ Debugging stopped by user.[/bold red]")
                logging.info("Debugging stopped by user.")
                break

        elif event_type == 'runner_on_ok':
            console.print(f"[bold green]✅ Task '{task}' completed successfully.[/bold green]")
            logging.info(f"Task '{task}' completed successfully.")
            log_task(task, "success", cmd)

        elif event_type == 'runner_on_failed':
            error_msg = res_data.get('msg', 'No details')
            stderr_output = res_data.get('stderr', 'No stderr output')
            stdout_output = res_data.get('stdout', 'No stdout output')
            return_code = res_data.get('rc', 'Unknown')

            console.print(f"[bold red]❌ Task '{task}' failed.[/bold red]")
            console.print(f"[bold magenta]🔍 Error Message:[/bold magenta] {error_msg}")
            console.print(f"[bold magenta]📄 Command Run:[/bold magenta] {' '.join(cmd)}")
            console.print(f"[bold magenta]📄 Stderr Output:[/bold magenta] {stderr_output}")
            console.print(f"[bold magenta]📄 Stdout Output:[/bold magenta] {stdout_output}")
            console.print(f"[bold magenta]🔢 Return Code:[/bold magenta] {return_code}")

            logging.error(f"Task '{task}' failed. Command: {' '.join(cmd)}, Error: {error_msg}, Stderr: {stderr_output}, Stdout: {stdout_output}, Return Code: {return_code}")
            log_task(task, "failed", cmd, stdout_output, stderr_output, return_code)


            retry_count = 0
            while retry_count < MAX_RETRIES:
                user_input = console.input("[bold yellow]Do you want to retry this task? (yes/no/modify/exit): [/bold yellow]")

                if user_input.lower() == 'modify':
                    new_cmd = console.input("[bold cyan]Enter modified command: [/bold cyan]").strip()
                    if new_cmd:
                        cmd = new_cmd.split()
                        console.print(f"[bold blue]🔄 Running modified command: {' '.join(cmd)}...[/bold blue]")
                        try:
                            exit_code = run_command_live(cmd)
                            if exit_code == 0:
                                console.print(f"[bold green]✅ Modified command executed successfully.[/bold green]")
                                logging.info(f"Modified command executed successfully: {' '.join(cmd)}")
                                break  
                            else:
                                console.print(f"[bold red]❌ Modified command failed.[/bold red]")
                                logging.error(f"Modified command failed: {' '.join(cmd)}")
                                retry_count += 1
                                continue  
                        except FileNotFoundError:
                            console.print(f"[bold red]❌ Command not found: {' '.join(cmd)}[/bold red]")
                            logging.error(f"Command not found: {' '.join(cmd)}")
                            retry_count += 1
                            continue  
                        except subprocess.CalledProcessError as e:
                            console.print(f"[bold red]❌ Modified command failed.[/bold red]")
                            console.print(f"[bold magenta]📄 Stderr Output:[/bold magenta] {e.stderr.strip()}")
                            logging.error(f"Modified command failed: {' '.join(cmd)}, Error: {e.stderr.strip()}")
                            retry_count += 1
                            continue  


                elif user_input.lower() in ['yes']:
                    console.print(f"[bold blue]🔄 Retrying task (Attempt {retry_count + 1}/{MAX_RETRIES})...[/bold blue]")
                    logging.info(f"Retrying task '{task}', Attempt {retry_count + 1}/{MAX_RETRIES}")
                    time.sleep(BACKOFF_TIME * (2 ** retry_count))
                    retry_result = run_task(playbook, inventory)
                    if retry_result.rc == 0:
                        console.print(f"[bold green]✅ Task '{task}' retried successfully.[/bold green]")
                        logging.info(f"Task '{task}' retried successfully.")
                        log_task(task, "retried_success", cmd)
                        break
                    else:
                        console.print(f"[bold red]❌ Task '{task}' failed again.[/bold red]")
                        logging.error(f"Task '{task}' failed again.")
                        log_task(task, "retried_fail", cmd)
                        retry_count += 1
                elif user_input.lower() == 'no':
                    break
                elif user_input.lower() == 'exit':
                    return

            if retry_count == MAX_RETRIES:
                console.print(f"[bold red]🚨 Max retries reached for task '{task}'. Moving on.[/bold red]")
                logging.error(f"Max retries reached for task '{task}'. Moving on.")
    
    console.print("[bold cyan]📜 Debugging Summary:[/bold cyan]")
    for entry in debug_session:
        console.print(f"🔹 [bold magenta]{entry['task']}[/bold magenta] - [bold yellow]{entry['status']}[/bold yellow] at {entry['timestamp']}")
    console.print("[bold green]Execution completed.[/bold green]")

@click.command()
@click.option("--playbook", required=True, help="Path to playbook")
@click.option("--inventory", default="inventory.ini", help="Path to inventory file")
@click.option("--step", is_flag=True, help="Run step-by-step")
def main(playbook, inventory, step):
    if step:
        run_playbook_step_by_step(playbook, inventory)
    else:
        run_task(playbook, inventory)
        
def run_command_live(cmd):
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, universal_newlines=True)

    for line in iter(process.stdout.readline, ''):
        console.print(f"[bold cyan]📄 Stdout:[/bold cyan] {line.strip()}")

    for line in iter(process.stderr.readline, ''):
        console.print(f"[bold red]📄 Stderr:[/bold red] {line.strip()}")

    process.wait()  
    return process.returncode  

if __name__ == "__main__":
    main()
