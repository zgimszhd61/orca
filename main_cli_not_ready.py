import os
import sys
import json
import importlib
import traceback
import argparse  # 用于解析命令行参数
from time import sleep
from openai import OpenAI
from flask import Flask, Blueprint, request, send_from_directory, render_template_string, jsonify

MODEL_NAME = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')

LOG_FILE = "cli_app_builder_log.json"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
ROUTES_DIR = os.path.join(BASE_DIR, 'routes')

progress = {
    "status": "idle",
    "iteration": 0,
    "max_iterations": 50,
    "output": "",
    "completed": False
}

def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)
        if path == ROUTES_DIR:
            create_file(os.path.join(ROUTES_DIR, '__init__.py'), '')
        return f"Created directory: {path}"
    return f"Directory already exists: {path}"

def create_file(path, content):
    try:
        with open(path, 'x') as f:
            f.write(content)
        return f"Created file: {path}"
    except FileExistsError:
        with open(path, 'w') as f:
            f.write(content)
        return f"Updated file: {path}"
    except Exception as e:
        return f"Error creating/updating file {path}: {e}"

def update_file(path, content):
    try:
        with open(path, 'w') as f:
            f.write(content)
        return f"Updated file: {path}"
    except Exception as e:
        return f"Error updating file {path}: {e}"

def fetch_code(file_path):
    try:
        with open(file_path, 'r') as f:
            code = f.read()
        return code
    except Exception as e:
        return f"Error fetching code from {file_path}: {e}"

def load_routes():
    try:
        if BASE_DIR not in sys.path:
            sys.path.append(BASE_DIR)
        for filename in os.listdir(ROUTES_DIR):
            if filename.endswith('.py') and filename != '__init__.py':
                module_name = filename[:-3]
                module_path = f'routes.{module_name}'
                try:
                    if module_path in sys.modules:
                        importlib.reload(sys.modules[module_path])
                    else:
                        importlib.import_module(module_path)
                    module = sys.modules.get(module_path)
                    if module:
                        # Find all blueprint objects in the module
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            if isinstance(attr, Blueprint):
                                app.register_blueprint(attr)
                except Exception as e:
                    print(f"Error importing module {module_path}: {e}")
                    continue
        print("Routes loaded successfully.")
        return "Routes loaded successfully."
    except Exception as e:
        print(f"Error in load_routes: {e}")
        return f"Error loading routes: {e}"

def task_completed():
    progress["status"] = "completed"
    progress["completed"] = True
    return "Task marked as completed."

create_directory(TEMPLATES_DIR)
create_directory(STATIC_DIR)
create_directory(ROUTES_DIR) 

load_routes()

def log_to_file(history_dict):
    try:
        with open(LOG_FILE, 'w') as log_file:
            json.dump(history_dict, log_file, indent=4)
    except Exception as e:
        pass 

available_functions = {
    "create_directory": create_directory,
    "create_file": create_file,
    "update_file": update_file,
    "fetch_code": fetch_code,
    "task_completed": task_completed
}

tools = [
    {
        "type": "function",
        "function": {
            "name": "create_directory",
            "description": "Creates a new directory at the specified path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The directory path to create."
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "Creates or updates a file at the specified path with the given content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The file path to create or update."
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write into the file."
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_file",
            "description": "Updates an existing file at the specified path with the new content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The file path to update."
                    },
                    "content": {
                        "type": "string",
                        "description": "The new content to write into the file."
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_code",
            "description": "Retrieves the code from the specified file path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The file path to fetch the code from."
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "task_completed",
            "description": "Indicates that the assistant has completed the task.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

def run_main_loop(user_input):
    # Reset the history_dict for each run
    history_dict = {
        "iterations": []
    }

    max_iterations = progress["max_iterations"]
    iteration = 0

    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert Flask developer tasked with building a complete, production-ready Flask application based on the user's description. "
                "Before coding, carefully plan out all the files, routes, templates, and static assets needed. "
                "Follow these steps:\n"
                "1. **Understand the Requirements**: Analyze the user's input to fully understand the application's functionality and features.\n"
                "2. **Plan the Application Structure**: List all the routes, templates, and static files that need to be created. Consider how they interact.\n"
                "3. **Implement Step by Step**: For each component, use the provided tools to create directories, files, and write code. Ensure each step is thoroughly completed before moving on.\n"
                "4. **Review and Refine**: Use `fetch_code` to review the code you've written. Update files if necessary using `update_file`.\n"
                "5. **Ensure Completeness**: Do not leave any placeholders or incomplete code. All functions, routes, and templates must be fully implemented and ready for production.\n"
                "6. **Do Not Modify `main.py`**: Focus only on the `templates/`, `static/`, and `routes/` directories.\n"
                "7. **Finalize**: Once everything is complete and thoroughly tested, call `task_completed()` to finish.\n\n"
                "Constraints and Notes:\n"
                "- The application files must be structured within the predefined directories: `templates/`, `static/`, and `routes/`.\n"
                "- Routes should be modular and placed inside the `routes/` directory as separate Python files.\n"
                "- The `index.html` served from the `templates/` directory is the entry point of the app. Update it appropriately if additional templates are created.\n"
                "- Do not use placeholders like 'Content goes here'. All code should be complete and functional.\n"
                "- Do not ask the user for additional input; infer any necessary details to complete the application.\n"
                "- Ensure all routes are properly linked and that templates include necessary CSS and JS files.\n"
                "- Handle any errors internally and attempt to resolve them before proceeding.\n\n"
                "Available Tools:\n"
                "- `create_directory(path)`: Create a new directory.\n"
                "- `create_file(path, content)`: Create or overwrite a file with content.\n"
                "- `update_file(path, content)`: Update an existing file with new content.\n"
                "- `fetch_code(file_path)`: Retrieve the code from a file for review.\n"
                "- `task_completed()`: Call this when the application is fully built and ready.\n\n"
                "Remember to think carefully at each step, ensuring the application is complete, functional, and meets the user's requirements."
            )
        },
        {"role": "user", "content": user_input},
        {"role": "system", "content": f"History:\n{json.dumps(history_dict, indent=2)}"}
    ]
    output = ""

    while iteration < max_iterations:
        progress["iteration"] = iteration + 1
        current_iteration = {
            "iteration": iteration + 1,
            "actions": [],
            "llm_responses": [],
            "tool_results": [],
            "errors": []
        }
        history_dict['iterations'].append(current_iteration)

        try:
            client = OpenAI()
            # 使用 OpenAI API 替换 LiteLLM 的调用
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                max_tokens=1500,
                temperature=0.7
            )

            if not response.choices:
                error = "No response received from the model"
                current_iteration['errors'].append({'action': 'llm_completion', 'error': error})
                log_to_file(history_dict)
                sleep(5)
                iteration += 1
                continue

            response_message = response.choices[0].message
            content = response_message.content
            print("{}. {}".format(progress["iteration"],content))
            print("==========================================")
            current_iteration['llm_responses'].append(content)

            output += f"\nIteration {iteration + 1}:\n{content}\n"

            progress["output"] = output

        except Exception as e:
            error = str(e)
            current_iteration['errors'].append({
                'action': 'main_loop',
                'error': error,
                'traceback': traceback.format_exc()
            })

        iteration += 1
        log_to_file(history_dict)
        sleep(2)

    if iteration >= max_iterations:
        progress["status"] = "completed"

    progress["completed"] = True
    progress["status"] = "completed"

    return output

# 定义 CLI 参数解析
def main():
    parser = argparse.ArgumentParser(description="Flask App Builder CLI")
    parser.add_argument('user_input', type=str, help="Description of the Flask app you want to create")
    args = parser.parse_args()

    # 运行主循环
    result = run_main_loop(args.user_input)
    print(result)

if __name__ == '__main__':
    main()
