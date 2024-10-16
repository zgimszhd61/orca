import os
import sys
import json
import importlib
import traceback
from flask import Flask, Blueprint, request, send_from_directory, render_template_string, jsonify
from threading import Thread
from time import sleep

from litellm import completion, supports_function_calling

MODEL_NAME = os.environ.get('LITELLM_MODEL', 'gpt-4o')

app = Flask(__name__)

LOG_FILE = "flask_app_builder_log.json"

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

# Default route to serve generated index.html or render a form
@app.route('/', methods=['GET', 'POST'])
def home():
    index_file = os.path.join(TEMPLATES_DIR, 'index.html')
    if os.path.exists(index_file):
        return send_from_directory(TEMPLATES_DIR, 'index.html')
    else:
        if request.method == 'POST':
            user_input = request.form.get('user_input')
            progress["status"] = "running"
            progress["iteration"] = 0
            progress["output"] = ""
            progress["completed"] = False
            thread = Thread(target=run_main_loop, args=(user_input,))
            thread.start()
            return render_template_string('''
                <h1>进度</h1>
                <pre id="progress">{{ progress_output }}</pre>
                <script>
                    setInterval(function() {
                        fetch('/progress')
                        .then(response => response.json())
                        .then(data => {
                            document.getElementById('progress').innerHTML = data.output;
                            if (data.completed) {
                                document.getElementById('refresh-btn').style.display = 'block';
                            }
                        });
                    }, 2000);
                </script>
                <button id="refresh-btn" style="display:none;" onclick="location.reload();">刷新页面</button>
            ''', progress_output=progress["output"])
        else:
            return render_template_string('''
                <h1>Flask 应用生成器</h1>
                <form method="post">
                    <label for="user_input">描述您想要创建的 Flask 应用:</label><br>
                    <input type="text" id="user_input" name="user_input" placeholder="请输入应用描述"><br><br>
                    <input type="submit" value="提交">
                </form>
            ''')

@app.route('/progress')
def get_progress():
    return jsonify(progress)

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
            "description": "在指定路径创建新目录。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要创建的目录路径。"
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
            "description": "在指定路径创建或更新文件，并写入内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要创建或更新的文件路径。"
                    },
                    "content": {
                        "type": "string",
                        "description": "写入文件的内容。"
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
            "description": "在指定路径更新已有文件的内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要更新的文件路径。"
                    },
                    "content": {
                        "type": "string",
                        "description": "写入文件的新内容。"
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
            "description": "从指定文件路径获取代码内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "要获取代码内容的文件路径。"
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
            "description": "表示任务已完成。",
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

    if not supports_function_calling(MODEL_NAME):
        progress["status"] = "error"
        progress["output"] = "Model does not support function calling."
        progress["completed"] = True
        return "Model does not support function calling."

    max_iterations = progress["max_iterations"]  # Prevent infinite loops
    iteration = 0

    # Updated messages array with enhanced prompt
    messages = [
        {
            "role": "system",
            "content": (
                "你是一名资深的Flask开发者，任务是基于用户描述，构建一个完整且可用于生产的Flask应用程序。"
                "在开始编码之前，请仔细规划所有需要的文件、路由、模板和静态资源。"
                "请按照以下步骤执行：\n"
                "1. **理解需求**：分析用户的输入，全面理解应用程序的功能和特点。\n"
                "2. **规划应用结构**：列出需要创建的所有路由、模板和静态文件，考虑它们之间的相互关系。\n"
                "3. **逐步实现**：为每个组件使用提供的工具创建目录、文件并编写代码，确保每一步都完成再继续下一个。\n"
                "4. **检查和优化**：使用 fetch_code 审查已编写的代码，如果需要可以使用 update_file 更新文件。\n"
                "5. **确保完整性**：不要留下任何占位符或未完成的代码。所有函数、路由和模板都必须完整实现，以便投入生产使用。\n"
                "6. **不要修改 main.py**：只专注于 templates/、static/ 和 routes/ 目录。\n"
                "7. **完成后提交**：确保所有功能已完成并经过彻底测试后，调用 task_completed() 来结束任务。\n\n"
                "限制和说明：\n"
                "- 应用文件必须在预定义的目录中：templates/、static/ 和 routes/。\n"
                "- 路由应模块化，并放在 routes/ 目录下作为独立的Python文件。\n"
                "- templates/ 目录下的 index.html 是应用的入口。如果创建了额外的模板，请适当更新它。\n"
                "- 不要使用“内容放置在此类”占位符。所有代码应完整且功能齐全。\n"
                "- 不要向用户询问其他输入；根据上下文自行推断出所需的细节来完成应用。\n"
                "- 确保所有路由均正确链接，模板中包含必要的 CSS 和 JS 文件。\n"
                "- 内部处理任何错误，并在继续之前尝试解决它们。\n\n"
                "可用工具：\n"
                "- create_directory(path)：创建一个新目录。\n"
                "- create_file(path, content)：创建或覆盖一个文件，并写入内容。\n"
                "- update_file(path, content)：更新已存在的文件内容。\n"
                "- fetch_code(file_path)：从文件中检索代码以供查看。\n"
                "- task_completed()：当应用完全构建完毕并准备就绪时调用。\n\n"
                "请在每一步谨慎思考，确保应用程序完整、功能齐全，且满足用户的需求。"
            )
        },
        {"role": "user", "content": user_input},
        {"role": "system", "content": f"History:\n{json.dumps(history_dict, indent=2)}"}
    ]

    output = ""

    while iteration < max_iterations:
        progress["iteration"] = iteration + 1
        current_iteration = {
            "iteration": iteration + 1,  # Start from 1
            "actions": [],
            "llm_responses": [],
            "tool_results": [],
            "errors": []
        }
        history_dict['iterations'].append(current_iteration)

        try:
            response = completion(
                model=MODEL_NAME,
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )

            if not response.choices[0].message:
                error = response.get('error', 'Unknown error')
                current_iteration['errors'].append({'action': 'llm_completion', 'error': error})
                log_to_file(history_dict)
                sleep(5)
                iteration += 1
                continue

            response_message = response.choices[0].message
            content = response_message.content or ""
            current_iteration['llm_responses'].append(content)

            output += f"\n<h2>Iteration {iteration + 1}:</h2>\n"

            tool_calls = response_message.tool_calls

            if tool_calls:
                output += "<strong>Tool Call:</strong>\n<p>" + content + "</p>\n"
                messages.append(response_message)

                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_to_call = available_functions.get(function_name)

                    if not function_to_call:
                        error_message = f"Tool '{function_name}' is not available."
                        current_iteration['errors'].append({
                            'action': f'tool_call_{function_name}',
                            'error': error_message,
                            'traceback': 'No traceback available.'
                        })
                        continue

                    try:
                        function_args = json.loads(tool_call.function.arguments)

                        function_response = function_to_call(**function_args)

                        current_iteration['tool_results'].append({
                            'tool': function_name,
                            'result': function_response
                        })

                        output += f"<strong>Tool Result ({function_name}):</strong>\n<p>{function_response}</p>\n"

                        messages.append(
                            {"tool_call_id": tool_call.id, "role": "tool", "name": function_name, "content": function_response}
                        )

                        if function_name == "task_completed":
                            progress["status"] = "completed"
                            progress["completed"] = True
                            output += "\n<h2>COMPLETE</h2>\n"
                            progress["output"] = output
                            log_to_file(history_dict)
                            return output

                    except Exception as tool_error:
                        error_message = f"Error executing {function_name}: {tool_error}"
                        current_iteration['errors'].append({
                            'action': f'tool_call_{function_name}',
                            'error': error_message,
                            'traceback': traceback.format_exc()
                        })

                second_response = completion(
                    model=MODEL_NAME,
                    messages=messages
                )
                if second_response.choices and second_response.choices[0].message:
                    second_response_message = second_response.choices[0].message
                    content = second_response_message.content or ""
                    current_iteration['llm_responses'].append(content)
                    output += "<strong>LLM Response:</strong>\n<p>" + content + "</p>\n"
                    messages.append(second_response_message)
                else:
                    error = second_response.get('error', 'Unknown error in second LLM response.')
                    current_iteration['errors'].append({'action': 'second_llm_completion', 'error': error})

            else:
                output += "<strong>LLM Response:</strong>\n<p>" + content + "</p>\n"
                messages.append(response_message)

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)