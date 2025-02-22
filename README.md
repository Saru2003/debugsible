# Debugsible - An Interactive Ansible Playbook Debugger

##  Overview

**Debugsible** is a command-line tool designed to help users debug Ansible playbooks efficiently. It provides real-time execution logs, interactive retries, and error handling with detailed logging.  

This tool aims to streamline troubleshooting and debugging for Ansible users by enabling them to:
- Run playbooks step-by-step.
- Retry failed tasks with optional modifications.
- Log execution details for later review.

##  Features

- Interactive debugging with real-time logs  
- Step-by-step execution for better control  
- Automatic retry with exponential backoff  
- Option to modify commands before retrying  
- Task failure summaries and log tracking  

##  Installation

1. Clone this repository:
   ```bash
   git clone <repository_url>
   cd debugsible
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

##  Usage

Run the tool with an Ansible playbook and inventory file:

```bash
python debugsible.py --playbook <path_to_playbook> --inventory <path_to_inventory>
```

### Step-by-Step Debugging Mode

If you want to run tasks one by one, use the `--step` flag:

```bash
python debugsible.py --playbook <path_to_playbook> --inventory <path_to_inventory> --step
```

### Example

Running a sample playbook with an inventory file:

```bash
python debugsible.py --playbook sample_playbook.yml --inventory inventory.ini
```

##  Demo Video

Watch the tool in action:

[![Watch the Demo](https://img.shields.io/badge/Watch%20Demo-Click%20Here-blue)](<https://youtu.be/UUUG9zZkuRE>)

## How It Works

1. The tool reads tasks from the provided playbook.
2. If a task fails, the user can:
   - Retry the task.
   - Modify the command and rerun it.
   - Skip or exit debugging.
3. Execution details, including failures, are logged for review.
4. A **summary report** is generated at the end.

##  Why Debugsible?

1. **Saves time** - Debug and retry tasks without rerunning the entire playbook.  
2. **Improves efficiency** - Modify failing tasks on the go.  
3. **Easy to use** - Simple command-line interface with interactive options.  

##  License

This project is licensed under the **MIT License**. See the [LICENSE](https://github.com/Saru2003/debugsible/blob/main/LICENSE) file for details.
