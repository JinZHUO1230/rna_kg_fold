# RNA Knowledge Graph + Folding Prediction

RNA 知识图谱与结构折叠预测研究项目。

## 环境搭建（从零开始）

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

下面这一条命令会自动创建 `.venv/` 虚拟环境并安装所有依赖（包括 CPU 版 PyTorch）：

```bash
uv sync --extra dev
```

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
pytest tests/ -v
```

所有测试通过（绿色 PASSED）说明环境搭建成功。

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

> 本地开发使用 CPU 版 PyTorch。集群上的 GPU 版本安装详见 `scripts/install_gpu.sh`（待补充）。

## License

MIT © 2026 JinZHUO1230
