import os
import sys
import json
import importlib
import traceback
from flask import Flask, Blueprint, request, send_from_directory, render_template_string, jsonify
from threading import Thread
from time import sleep

from litellm import completion, supports_function_calling
from litellm import set_verbose

MODEL_NAME = os.environ.get('LITELLM_MODEL', 'gpt-4o-mini')

set_verbose = True

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
        return f"创建了目录: {path}"
    return f"目录已存在: {path}"

def create_file(path, content):
    try:
        with open(path, 'x') as f:
            f.write(content)
        return f"创建了文件: {path}"
    except FileExistsError:
        with open(path, 'w') as f:
            f.write(content)
        return f"更新了文件: {path}"
    except Exception as e:
        return f"创建/更新文件 {path} 时出错: {e}"

def update_file(path, content):
    try:
        with open(path, 'w') as f:
            f.write(content)
        return f"更新了文件: {path}"
    except Exception as e:
        return f"更新文件 {path} 时出错: {e}"

def fetch_code(file_path):
    try:
        with open(file_path, 'r') as f:
            code = f.read()
        return code
    except Exception as e:
        return f"从 {file_path} 获取代码时出错: {e}"

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
                    print(f"导入模块 {module_path} 时出错: {e}")
                    continue
        print("路由加载成功。")
        return "路由加载成功。"
    except Exception as e:
        print(f"加载路由时出错: {e}")
        return f"加载路由时出错: {e}"

def task_completed():
    progress["status"] = "completed"
    progress["completed"] = True
    return "任务已标记为完成。"

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
                <h1>Flask 应用构建器</h1>
                <form method="post">
                    <label for="user_input">描述您想要创建的 Flask 应用：</label><br>
                    <input type="text" id="user_input" name="user_input"><br><br>
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
            "description": "在指定路径创建或更新文件，并写入给定内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要创建或更新的文件路径。"
                    },
                    "content": {
                        "type": "string",
                        "description": "要写入文件的内容。"
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
            "description": "更新指定路径的现有文件，写入新内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要更新的文件路径。"
                    },
                    "content": {
                        "type": "string",
                        "description": "要写入文件的新内容。"
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
            "description": "从指定的文件路径获取代码。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "要获取代码的文件路径。"
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
            "description": "指示助手已完成任务。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

def run_main_loop(user_input):
    # 每次运行时重置 history_dict
    history_dict = {
        "iterations": []
    }

    if not supports_function_calling(MODEL_NAME):
        progress["status"] = "error"
        progress["output"] = "模型不支持函数调用。"
        progress["completed"] = True
        return "模型不支持函数调用。"

    max_iterations = progress["max_iterations"]  # 防止无限循环
    iteration = 0

    # 使用增强提示更新消息数组
    messages = [
        {
            "role": "system",
            "content": (
                "你是一名专家级Flask开发人员，任务是基于用户的描述构建一个完整的、可用于生产的Flask应用程序。"
                "在编写代码之前，仔细规划需要的所有文件、路由、模板和静态资源。"
                "请按照以下步骤操作：\n"
                "1. **理解需求**：分析用户的输入，充分理解应用程序的功能和特性。\n"
                "2. **规划应用程序结构**：列出需要创建的所有路由、模板和静态文件，并考虑它们之间如何交互。\n"
                "3. **逐步实现**：对于每个组件，使用提供的工具来创建目录、文件并编写代码。在进入下一步之前确保每一步都彻底完成。\n"
                "4. **审查和优化**：使用 `fetch_code` 查看你编写的代码。如果有必要，可以使用 `update_file` 更新文件。\n"
                "5. **确保完整性**：不要留任何占位符或不完整的代码。所有功能、路由和模板必须完全实现，并可用于生产环境。\n"
                "6. **不要修改 `main.py`**：仅关注 `templates/`、`static/` 和 `routes/` 目录中的文件。\n"
                "7. **最终确定**：一旦所有内容都完成并经过彻底测试，调用 `task_completed()` 完成任务。\n\n"
                "约束与注意事项：\n"
                "- 应用程序文件必须结构化到预定义的目录中：`templates/`、`static/` 和 `routes/`。\n"
                "- 路由应模块化，并作为独立的Python文件放入 `routes/` 目录中。\n"
                "- 从 `templates/` 目录提供的 `index.html` 是应用的入口点。如果创建了其他模板，请相应更新。\n"
                "- 不要使用诸如“内容在此处”之类的占位符。所有代码应完整且功能正常。\n"
                "- 不要向用户请求额外输入；推断完成应用程序所需的任何细节。\n"
                "- 确保所有路由正确链接，并且模板包含必要的CSS和JS文件。\n"
                "- 在内部处理所有错误，并尝试在继续之前解决它们。\n\n"
                "可用工具：\n"
                "- `create_directory(path)`：创建一个新目录。\n"
                "- `create_file(path, content)`：使用内容创建或覆盖一个文件。\n"
                "- `update_file(path, content)`：使用新内容更新现有文件。\n"
                "- `fetch_code(file_path)`：从文件中获取代码进行查看。\n"
                "- `task_completed()`：当应用程序完全构建并准备好时调用此工具完成任务。\n\n"
                "请在每一步中仔细思考，确保应用程序完整、功能正常，并满足用户需求。"
            )
        },
        {"role": "user", "content": user_input},
        {"role": "system", "content": f"历史记录：\n{json.dumps(history_dict, indent=2)}"}
    ]

    output = ""

    while iteration < max_iterations:
        progress["iteration"] = iteration + 1
        current_iteration = {
            "iteration": iteration + 1,  # 从1开始
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
                error = response.get('error', '未知错误')
                current_iteration['errors'].append({'action': 'llm_completion', 'error': error})
                log_to_file(history_dict)
                sleep(5)
                iteration += 1
                continue

            response_message = response.choices[0].message
            content = response_message.content or ""
            current_iteration['llm_responses'].append(content)

            output += f"\n<h2>迭代 {iteration + 1}：</h2>\n"

            tool_calls = response_message.tool_calls

            if tool_calls:
                output += "<strong>工具调用：</strong>\n<p>" + content + "</p>\n"
                messages.append(response_message)

                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_to_call = available_functions.get(function_name)

                    if not function_to_call:
                        error_message = f"工具 '{function_name}' 不可用。"
                        current_iteration['errors'].append({
                            'action': f'tool_call_{function_name}',
                            'error': error_message,
                            'traceback': '没有可用的追溯信息。'
                        })
                        continue

                    try:
                        function_args = json.loads(tool_call.function.arguments)

                        function_response = function_to_call(**function_args)

                        current_iteration['tool_results'].append({
                            'tool': function_name,
                            'result': function_response
                        })

                        output += f"<strong>工具结果 ({function_name})：</strong>\n<p>{function_response}</p>\n"

                        messages.append(
                            {"tool_call_id": tool_call.id, "role": "tool", "name": function_name, "content": function_response}
                        )

                        if function_name == "task_completed":
                            progress["status"] = "completed"
                            progress["completed"] = True
                            output += "\n<h2>完成</h2>\n"
                            progress["output"] = output
                            log_to_file(history_dict)
                            return output

                    except Exception as tool_error:
                        error_message = f"执行 {function_name} 时出错：{tool_error}"
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
                    output += "<strong>LLM 响应：</strong>\n<p>" + content + "</p>\n"
                    messages.append(second_response_message)
                else:
                    error = second_response.get('error', '第二次 LLM 响应中未知错误。')
                    current_iteration['errors'].append({'action': 'second_llm_completion', 'error': error})

            else:
                output += "<strong>LLM 响应：</strong>\n<p>" + content + "</p>\n"
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