"""验证所有关键依赖版本符合项目规范。"""

import importlib.metadata


def test_torch_version() -> None:
    import torch

    major, minor = torch.__version__.split(".")[:2]
    assert (major, minor) == ("2", "4"), f"需要 torch 2.4.x，当前: {torch.__version__}"


def test_pytorch_lightning_version() -> None:
    version = importlib.metadata.version("pytorch-lightning")
    major, minor = version.split(".")[:2]
    assert (major, minor) == ("2", "4"), (
        f"需要 pytorch-lightning 2.4.x，当前: {version}"
    )


def test_hydra_version() -> None:
    version = importlib.metadata.version("hydra-core")
    assert version.startswith("1.3"), f"需要 hydra-core 1.3.x，当前: {version}"


def test_e3nn_version() -> None:
    version = importlib.metadata.version("e3nn")
    assert version.startswith("0.5"), f"需要 e3nn 0.5.x，当前: {version}"
