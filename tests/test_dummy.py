"""
Smoke tests（冒烟测试）：验证项目结构和核心依赖可以正常导入。
冒烟测试 = 最基本的健康检查，不测业务逻辑，只确认"点火不爆炸"。
"""


def test_basic_math() -> None:
    """最简单的测试：验证 pytest 框架本身工作正常。"""
    assert 1 + 1 == 2


def test_project_packages_importable() -> None:
    """验证项目的各个子模块可以被 Python 找到并导入。"""
    import evaluation  # noqa: F401
    import kg  # noqa: F401
    import models  # noqa: F401
    import training  # noqa: F401


def test_torch_importable() -> None:
    """验证 PyTorch 安装正确，版本符合要求（2.4.x）。"""
    import torch

    assert torch.__version__.startswith("2.4"), (
        f"期望 torch 2.4.x，实际安装的是 {torch.__version__}"
    )


def test_pytorch_lightning_importable() -> None:
    """验证 PyTorch Lightning 安装正确。"""
    import pytorch_lightning  # noqa: F401


def test_hydra_importable() -> None:
    """验证 Hydra 配置框架安装正确。"""
    import hydra  # noqa: F401
