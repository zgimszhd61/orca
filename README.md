# Simplest Self-Refine Code Agent - 最简单的自动生成代码代理

**simplest-self-refine-code-agent** 是一个简单易用的工具，能够从自然语言描述中自动生成多文件的 Flask 应用。它结合了简单的 LLM 循环和少量工具，帮助自动化编码，将想法快速转化为功能性网页应用。

## 功能特性
- **自然语言输入**：使用简单的英文描述想要构建的应用。
- **自动代码生成**：根据描述生成 Flask 应用的路由、模板和静态文件。
- **自建代理**：无需手动编写代码，自动规划并构建应用。
- **模块化结构**：将代码组织成模块化的结构，模板、静态文件和路由分别放在不同的目录中。

## 快速开始

### 前置要求
- Python 3.7 或更高版本
- pip 包管理器

### 安装步骤

1. **克隆仓库**：
   ```bash
   git clone https://github.com/zgimszhd61/simplest-self-refine-code-agent.git
   cd simplest-self-refine-code-agent
   ```

2. **创建虚拟环境**（可选，但建议）：
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Windows 上使用 venv\Scripts\activate
   ```

3. **安装依赖包**：
   ```bash
   pip install litellm
   ```

### 设置 OPENAI_API_KEY

simplest-self-refine-code-agent 需要在环境中配置 `OPENAI_API_KEY`。有两种方式：

- **方式 1：临时设置 API 密钥**
  - macOS/Linux：
    ```bash
    export OPENAI_API_KEY=your-openai-api-key
    ```
  - Windows（命令提示符）：
    ```bash
    set OPENAI_API_KEY=your-openai-api-key
    ```
  - Windows（PowerShell）：
    ```bash
    $env:OPENAI_API_KEY="your-openai-api-key"
    ```

- **方式 2：使用 .env 文件（推荐）**
  - 安装 python-dotenv：
    ```bash
    pip install python-dotenv
    ```
  - 在项目目录下创建 `.env` 文件，并添加 API 密钥：
    ```
    OPENAI_API_KEY=your-openai-api-key
    ```

## 使用方法

1. **运行应用**：
   ```bash
   python main_web_cn.py
   ```

2. **访问网页界面**：
   在浏览器中访问 [http://localhost:8080](http://localhost:8080)。

3. **描述想构建的应用**：
   在主页的表单中，用自然语言描述你想要创建的 Flask 应用。

4. **监控进度**：
   提交描述后，应用会处理请求，并实时显示生成过程。

5. **查看生成的应用**：
   生成完成后，可以再次运行 Flask 应用，与新生成的应用进行交互：
   ```bash
   python main_web_cn.py
   ```

## 参考示例

- 创建一个简单的 Flask 应用，输出 "hello world"，只有一个路由 `/hello`。
- 创建一个 Flask 应用，有两个路由 `/helloa` 和 `/hellob`，分别输出 "helloa" 和 "hellob"。

应用生成后，刷新网页即可使用新的路由。

