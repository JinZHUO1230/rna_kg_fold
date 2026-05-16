# RNA Knowledge Graph + Folding Prediction

RNA 知识图谱与结构折叠预测研究项目。

## 环境搭建（从零开始）

### Python 版本要求

本项目需要 **Python 3.11 或 3.12**（不支持 3.13+，因为 torch 2.4 尚未支持 3.13）。

### 第一步：安装 uv

`uv` 是一个现代 Python 依赖管理工具，比 pip/conda 快很多。

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

安装完成后重启终端，或运行：

```bash
source $HOME/.local/bin/env
```

验证安装：

```bash
uv --version
```

### 第二步：克隆仓库

```bash
git clone https://github.com/JinZHUO1230/rna_kg_fold.git
cd rna_kg_fold
```

### 第三步：创建虚拟环境并安装依赖

下面这一条命令会自动创建 `.venv/` 虚拟环境并安装所有依赖（含开发工具）：

```bash
uv sync --python 3.11
```

> **PyTorch 版本说明（自动按平台选择）**：
> - **macOS**：自动从 PyPI 安装 CPU 版 torch 2.4.x
> - **Linux（集群）**：自动从 PyTorch 官方 CUDA 源安装 CUDA 12.4 版 torch 2.4.x
>
> 无需手动指定，`uv` 会根据操作系统自动选择正确的版本。

> **如果 uv 选错了 Python 版本**（例如选了 3.13），用以下命令修复：
> ```bash
> uv python install 3.11
> uv sync --python 3.11
> ```

> **说明**：首次运行需要下载约 1-2 GB 的依赖包（主要是 PyTorch），请耐心等待。

### 第四步：激活虚拟环境

```bash
source .venv/bin/activate
```

激活后，命令行前面会出现 `(rna-kg-fold)` 字样，说明你已进入项目的独立 Python 环境。

### 第五步：安装 pre-commit hooks

`pre-commit` 会在每次 `git commit` 前自动检查代码格式和类型。

```bash
pre-commit install
```

### 第六步：验证安装

```bash
uv run python -m pytest tests/ -v
```

所有测试通过（绿色 PASSED）说明环境搭建成功。

### 集群（Linux/CUDA）验证 GPU 可用性

登录集群并完成上述环境搭建后，运行以下命令验证 GPU 可访问：

```bash
uv run python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

预期输出类似：`2.4.1+cu124 True`

---

## 项目结构

```
rna_kg_fold/
├── data/           # 原始数据和处理后的数据（不提交到 git）
├── kg/             # 知识图谱构建代码
├── models/         # 神经网络模型定义
├── training/       # 训练流程
├── evaluation/     # 评估指标
├── scripts/        # 一次性脚本（数据下载、格式转换等）
├── configs/        # Hydra 配置文件
├── notebooks/      # Jupyter 分析笔记本
├── tests/          # 测试代码
└── .github/        # GitHub Actions CI 配置
```

## 实验追踪（wandb）

本项目用 wandb 追踪实验，分为 4 个阶段分组：

| 分组 | 用途 |
|------|------|
| `data_eda` | 数据探索和分析 |
| `pretraining` | 预训练阶段 |
| `structure_training` | 结构预测训练 |
| `ablation` | 消融实验 |

首次使用需要登录：

```bash
wandb login
```

## GPU 集群部署

在 Linux 集群上执行同样的 `uv sync --python 3.11`，uv 会自动安装 CUDA 12.4 版的 torch 2.4.x，无需额外操作。

## License

MIT © 2026 JinZHUO1230
