# Python 代码质量检查

## 概述

本项目已配置自动化的 Python 代码质量检查，使用 flake8 工具来确保提交的代码符合 Python 编码规范。

## 自动检查

当您向以下分支推送代码或创建拉取请求时，GitHub Actions 会自动运行代码质量检查：
- `master`
- `main`
- `develop`

检查过程会：
1. 检测所有已更改的 Python 文件
2. 对这些文件运行 flake8 代码质量检查
3. 如果发现问题，构建将失败并显示具体的错误信息

## 本地检查

在提交代码之前，您可以在本地运行 flake8 来检查代码质量：

### 安装 flake8

```bash
pip install flake8
```

### 检查单个文件

```bash
flake8 path/to/your/file.py
```

### 检查整个项目

```bash
flake8 .
```

## 配置

项目的 flake8 配置位于 `.flake8` 文件中，主要设置包括：

- **最大行长度**: 120 字符
- **全局忽略的错误**:
  - E203: 冒号前的空白
  - W503: 二元运算符前的换行（与 black 冲突）
- **排除目录**: .git, __pycache__, venv, log, image, nginx 等
- **特殊文件忽略规则**:
  - `__init__.py`: 忽略 F401, F403（导入但未使用，通配符导入）
  - `main.py`: 忽略 F401, F403（用于模块加载的通配符导入）

## 常见问题

### 我的代码没有通过检查怎么办？

1. 查看 GitHub Actions 的输出，了解具体的错误
2. 根据错误信息修复代码
3. 在本地运行 flake8 确认问题已解决
4. 重新提交代码

### 如何临时忽略某些错误？

可以在代码行末添加 `# noqa: ERROR_CODE` 注释：

```python
example = lambda x: x  # noqa: E731
```

或者忽略整个文件的某个错误，在文件顶部添加：

```python
# flake8: noqa: E501
```

## 代码质量标准

本项目遵循的主要代码质量标准包括：

- PEP 8 Python 代码风格指南
- 合理的代码缩进和空白
- 避免未使用的导入
- 避免尾随空白
- 正确的函数和类之间的空行
- 合理的行长度（不超过 120 字符）

## 更多信息

- [flake8 官方文档](https://flake8.pycqa.org/)
- [PEP 8 风格指南](https://www.python.org/dev/peps/pep-0008/)
