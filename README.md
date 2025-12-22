以下是一个推荐的纯Python项目结构，适用于中小型项目：

```
your_project/
├── src/                     # 源代码目录（推荐使用）
│   └── your_package/       # 主包目录
│       ├── __init__.py     # 包初始化文件
│       ├── module1.py      # 模块1
│       ├── module2.py      # 模块2
│       └── subpackage/     # 子包（可选）
│           ├── __init__.py
│           └── ...
├── tests/                  # 测试目录
│   ├── __init__.py
│   ├── test_module1.py
│   └── test_module2.py
├── docs/                   # 文档目录
├── scripts/                # 脚本目录（可执行文件）
│   └── cli.py
├── data/                   # 数据文件（可选）
├── .gitignore             # Git忽略文件
├── README.md              # 项目说明
├── requirements.txt       # 项目依赖
├── pyproject.toml         # 项目配置和依赖（现代方式）
├── setup.py               # 安装脚本（传统方式，可选）
└── LICENSE                # 许可证文件
```

# 关键文件说明：

### 1. **src/目录结构**（推荐）
- 将源代码放在`src/`目录下可以防止导入时与测试文件冲突
- 符合Python打包最佳实践

### 2. **主要配置文件**
- **pyproject.toml**（现代标准）：
  ```toml
  [build-system]
  requires = ["setuptools>=61.0", "wheel"]
  build-backend = "setuptools.build_meta"
  
  [project]
  name = "your-package"
  version = "0.1.0"
  authors = [{name = "Your Name", email = "your@email.com"}]
  description = "Your project description"
  readme = "README.md"
  requires-python = ">=3.8"
  dependencies = [
      "requests>=2.25.0",
      "numpy>=1.20.0",
  ]
  
  [project.optional-dependencies]
  dev = ["pytest", "black", "flake8"]
  ```

- **requirements.txt**（传统方式）：
  ```
  requests>=2.25.0
  numpy>=1.20.0
  ```

### 3. **setup.py**（传统打包方式，可选）
```python
from setuptools import setup, find_packages

setup(
    name="your-package",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "requests>=2.25.0",
        "numpy>=1.20.0",
    ],
)
```

## 更简单的结构（小型项目）

对于非常简单的小项目：

```
simple_project/
├── your_package/
│   ├── __init__.py
│   ├── main.py
│   └── utils.py
├── tests/
│   └── test_basic.py
├── requirements.txt
└── README.md
```

## 推荐实践

1. **使用虚拟环境**：
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

2. **安装开发依赖**：
   ```bash
   pip install -e ".[dev]"  # 如果使用pyproject.toml
   ```

3. **测试结构**：
   ```python
   # tests/test_example.py
   import pytest
   from your_package.module1 import some_function
   
   def test_something():
       assert some_function() == expected_result
   ```

这个结构平衡了简洁性和最佳实践，可以根据项目需求调整。对于需要分发的项目，推荐使用`src/`布局；对于简单脚本，可以直接将模块放在根目录。