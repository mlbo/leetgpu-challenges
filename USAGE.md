# 🚀 LeetGPU 挑战项目使用指南

欢迎来到 LeetGPU！这是一个专注于高性能 GPU 编程挑战的平台。本项目已为你配置了一套完整的本地开发、调试和文档预览工具链。

## 🛠 1. 环境准备

在开始之前，请确保你的本地环境满足以下要求：
*   **NVIDIA GPU**: 建议算力 7.0 以上（脚本会自动检测）。
*   **CUDA Toolkit**: 已安装 `nvcc`。
*   **Python 3.10+**: 建议使用 Anaconda 或 venv 环境。
*   **依赖库**: 运行以下命令安装必要依赖：
    ```bash
    pip install torch requests websocket-client markdownify
    ```

## 📖 2. 浏览题目

为了方便在 VS Code 中直接查看题目，我们提供了美化后的 Markdown 文档：

*   **题目总览**: 打开 [`challenge_docs/CHALLENGES_INDEX.md`](challenge_docs/CHALLENGES_INDEX.md)。
*   **查看详情**: 在索引中点击对应题目，使用 `Ctrl+Shift+V` 开启侧边预览。
*   **同步更新**: 如果有新题目加入，运行 `python scripts/convert_to_md.py` 即可重新生成文档。

## 💻 3. 高效解题流程 (推荐)

我们为你创建了一个交互式脚本 **`scripts/solve.py`**，这是最推荐的解题方式。

### 第一步：启动交互脚本
```bash
python scripts/solve.py
```

### 第二步：搜索与选择
*   输入 **`e` / `m` / `h`** 快速按难度筛选。
*   直接输入 **题号 (ID)**（如 `01`）或 **关键字** 搜索。
*   如果输入的是精确 ID，脚本会直接进入该题目。

### 第三步：编写代码
*   如果是新题，脚本会询问是否从 `starter` 模板创建。
*   确认后，脚本会**自动在 VS Code 中打开** `Testing/solution.cu` 文件。
*   你只需在编辑器中专注于编写 CUDA 核函数。

### 第四步：本地验证
*   回到终端，在菜单中选择 **`[r]un tests`**。
*   脚本会**自动检测你的 GPU 架构**（如 RTX 3060 的 `sm_86`），并调用 `nvcc -O3` 进行编译。
*   测试完成后，无论成功或失败，按回车即可回到题目列表，方便你修改代码后再次一键测试。

## 🧪 4. 目录结构说明

*   `challenges/`: 原始题目代码、参考实现和测试用例。
    *   `easy/1_vector_add/Testing/`: **你的练习场**，存放你的 `solution.cu` 和编译产物。
*   `challenge_docs/`: 所有的题目文档 (Markdown)。
*   `scripts/`:
    *   `solve.py`: **核心交互脚本**（日常使用）。
    *   `run_challenge.py`: 底层运行逻辑，支持本地/远程模式。
    *   `convert_to_md.py`: 文档转换工具。

## 🚩 5. 远程提交 (可选)

当你本地测试全部通过，并希望将成绩提交到官方排行榜时：
1.  确保你已设置环境变量：`export LEETGPU_API_KEY=你的密钥`。
2.  在 `solve.py` 运行测试时，或者直接使用 `run_challenge.py` 不带 `--local` 参数进行提交。

---

**祝你在 GPU 编程的征途中不断突破性能极限！** 🏎️💨
