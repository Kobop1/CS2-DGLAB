# CS2&DGLab 联动控制工具

这是一个将CS2游戏状态与DGLab设备联动的控制工具，能够根据游戏内事件（如受伤、被闪光等）控制DGLab设备产生相应的振动反馈。

## 功能特点

- 实时接收CS2游戏状态（血量、受伤、闪光等）
- 控制DGLab设备产生对应振动反馈
- 提供现代化Web界面进行状态监控和参数配置
- 自动配置CS2游戏状态集成

## 安装与运行

### 前提条件

- Python 3.10 或更高版本
- UV 包管理器（会自动安装）
- CS2 游戏已安装
- DGLab 设备及配套App

### 安装步骤

1. 克隆或下载项目代码
2. 安装UV包管理器：
   ```bash
   # Windows (PowerShell)
   iwr https://astral.sh/uv/install.ps1 | iex

   # macOS/Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. 安装项目依赖：
   ```bash
   cd cs2_dglab
   uv sync
   ```

4. 运行应用：
   ```bash
   uv run python -m src.desktop
   ```
他妈的uv一直配置不上，真傻逼
## 使用方法

1. 启动应用后，会自动打开控制界面
2. 在"设备连接"页面，使用DGLab App扫描二维码进行连接
3. 确保CS2游戏已启动，工具会自动配置游戏状态集成
4. 在游戏中体验振动反馈，可在"参数配置"页面调整反馈强度

## 打包为可执行文件
# 安装打包工具
uv add pyinstaller --dev

# 打包
uv run pyinstaller --onefile --name "CS2&DGLab" --add-data "src/frontend:src/frontend" src/desktop.py
打包后的可执行文件会生成在`dist`目录下。