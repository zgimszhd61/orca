orca
版权声明

orca - 最简单的自动建设编码代理。

orca 是一个运行方便的工具，可以通过无代码界面，从简单的自然语言描述中生成多文件 Flask 应用。应用一些简单的 LLM 循环和少数工具，orca 自动化了编码过程，将想法转化为功能性的网页应用。

功能特性
- 简单的自然语言输入：只需用纯粹的英语描述想要构建的应用。
- 自动代码生成：根据描述生成路由、模板和静态文件。
- 自建代理：无需手动编码，自动计划和构建应用。
- 模块化的结构：把代码组织成清晰的模块化结构，模板、静态文件和路由会装在单独的目录中。

开始使用

前置准备
- Python 3.7 或更高版本
- pip 包管理器

安装
1. 克隆仓库

   ```bash
   git clone https://github.com/zgimszhd61/orca
   cd orca
   ```

2. 创建虚拟环境（可选，但建议）

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Windows上使用 venv\Scripts\activate
   ```

3. 安装依赖包

   ```bash
   pip install litellm
   ```

设置 OPENAI_API_KEY

使用 orca 需要在环境中设置 OPENAI_API_KEY，有以下两种方式可选：

- 方式 1：在终端中设置临时 API 密钥

  - macOS/Linux：
    ```bash
    export OPENAI_API_KEY=your-openai-api-key
    ```

  - Windows (Command Prompt)：
    ```bash
    set OPENAI_API_KEY=your-openai-api-key
    ```

  - Windows (PowerShell)：
    ```bash
    $env:OPENAI_API_KEY="your-openai-api-key"
    ```

- 方式 2：使用 .env 文件进行持久设置（建议）

  - 安装 python-dotenv 包，用于从 .env 文件中加载环境变量：
    ```bash
    pip install python-dotenv
    ```
  - 在项目目录下创建 .env 文件，并添加 API 密钥：
    ```
    OPENAI_API_KEY=your-openai-api-key
    ```

使用

- 运行应用
  ```bash
  python main.py
  ```

- 访问网页界面
  打开浏览器，访问 http://localhost:8080

- 描述想构建的应用
  首页上会有一个表单，可以描述想创建的 Flask 应用。

- 监控进度
  提交描述后，应用会对这个请求进行处理，可以实时监控进度。

- 查看生成的应用
  进程完成后，可再次运行 Flask 应用，互动与新生成的 Flask 应用：
  ```bash
  python main.py
  ```

## 例子：
 - 创建一个最简单的Flask应用，输出hello world，只有一个端口/hello
 - 创建一个最简单的Flask应用，有两个端口/helloa和hellob，其中/helloa输出helloa，/hellob输出hellob.