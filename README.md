# NetCatcher

一个基于 Python 的网络抓包工具，支持全协议数据包捕获和 HTTP/HTTPS 请求监控，提供专业的 GUI 界面进行实时分析和数据导出。

## 功能特性

- **全协议捕获** — 通过 Scapy 捕获 TCP、UDP、ICMP、ARP、DNS、TLS 等所有协议的网络数据包
- **HTTPS 解密** — 通过 mitmproxy MITM 代理拦截并解密 HTTPS 流量，查看请求/响应明文内容
- **实时显示** — 高性能批量 UI 更新，环形缓冲支持 50,000 个数据包的实时滚动
- **过滤搜索** — 按协议、IP、端口、关键字等条件实时过滤数据包和 HTTP 流
- **详情查看** — 四标签页详情面板：Overview（结构树）、Headers、Body、Hex（十六进制+ASCII）
- **统计仪表盘** — 协议分布饼图、流量统计卡片
- **数据导出** — 支持 PCAP（Wireshark 兼容）、HAR、cURL 三种格式导出
- **系统代理管理** — 自动配置和恢复 Windows 系统代理
- **深色/浅色主题** — 支持深色和浅色两种主题切换

## 系统要求

| 依赖 | 说明 |
|------|------|
| Windows 10/11 | 目前仅支持 Windows |
| [uv](https://docs.astral.sh/uv/) | Python 包管理器 |
| [Npcap](https://npcap.com/) | 网络驱动，安装时勾选 "WinPcap API-compatible Mode" |
| 管理员权限 | 抓包和系统代理设置需要以管理员身份运行 |

## 快速开始

### 1. 安装 Npcap

从 [npcap.com](https://npcap.com/) 下载安装，安装时勾选 **"Install Npcap in WinPcap API-compatible Mode"**。

### 2. 克隆项目并安装依赖

```bash
git clone https://github.com/Jelysium/chat-netcatcher.git
cd chat-netcatcher
uv sync
```

> uv 会自动安装 Python 3.12+ 并创建虚拟环境。

### 3. 运行

```bash
# 以管理员身份运行（推荐，否则部分功能受限）
uv run python -m netcatcher
```

安装后也可以直接使用命令：

```bash
uv run chat-netcatcher
```

## 使用说明

### 基本抓包

1. 启动应用后，在工具栏选择网络接口（默认"All Interfaces"）
2. 点击 **Start** 开始捕获
3. 数据包实时显示在 Packets 标签页中
4. 点击任意行，下方详情面板显示该包的完整信息

### HTTPS 拦截

1. 勾选工具栏的 **HTTPS Intercept**
2. 设置代理端口（默认 8080）
3. 点击 Start 开始捕获
4. 首次使用需要安装 CA 证书（见下方证书安装章节）
5. 浏览器流量将通过代理，可在 HTTP Flows 标签页查看解密后的请求

### 数据过滤

在列表上方的过滤输入框中输入关键词进行实时过滤：

- `tcp` — 过滤 TCP 协议包
- `192.168.1.1` — 过滤包含该 IP 的包
- `GET` — 过滤 HTTP GET 请求
- `example.com` — 过滤包含该域名的流量

### 数据导出

- **Export PCAP** — 导出为 .pcap 文件，可用 Wireshark 打开
- **Export HAR** — 导出为 HTTP Archive 格式，可在浏览器开发者工具中查看
- **Copy cURL** — 将选中的 HTTP 请求导出为 cURL 命令

### 证书安装

HTTPS 拦截需要将 mitmproxy 的 CA 证书安装到系统信任存储：

```bash
# 自动安装（需要管理员权限）
certutil -addstore -user Root "%USERPROFILE%\.mitmproxy\mitmproxy-ca-cert.cer"
```

或手动操作：

1. 运行 `certmgr.msc`
2. 导航到"受信任的根证书颁发机构" → "证书"
3. 右键 → "所有任务" → "导入"
4. 选择 `~/.mitmproxy/mitmproxy-ca-cert.p12`

> 卸载证书：`certutil -delstore -user Root mitmproxy`

## 项目结构

```
src/netcatcher/
├── app.py                        # 应用入口
├── __main__.py                   # CLI 入口
├── config/
│   ├── constants.py              # 常量定义
│   └── settings.py               # 用户配置
├── capture/
│   ├── engine_base.py            # 引擎基类
│   ├── scapy_engine.py           # Scapy 抓包引擎 (QThread)
│   ├── mitm_engine.py            # HTTPS MITM 引擎 (asyncio)
│   └── capture_manager.py       # 引擎管理器
├── models/
│   ├── packet.py                 # 数据包模型
│   ├── http_flow.py              # HTTP 流模型
│   ├── packet_table_model.py     # 数据包表格模型
│   └── flow_table_model.py       # HTTP 流表格模型
├── parsers/
│   ├── protocol_parser.py        # 协议解析器
│   ├── http_parser.py            # HTTP 解析器
│   ├── dns_parser.py             # DNS 解析器
│   └── tls_parser.py             # TLS 解析器
├── storage/
│   ├── ring_buffer.py            # 线程安全环形缓冲
│   ├── database.py               # SQLite 持久化
│   └── exporter.py               # 数据导出
├── proxy/
│   ├── system_proxy.py           # Windows 系统代理
│   └── cert_manager.py           # 证书管理
├── gui/
│   ├── main_window.py            # 主窗口
│   ├── capture_toolbar.py        # 工具栏
│   ├── packet_list_view.py       # 数据包列表
│   ├── flow_list_view.py         # HTTP 流列表
│   ├── detail_panel.py           # 详情面板
│   ├── hex_editor.py             # Hex 查看器
│   └── stats_dashboard.py        # 统计仪表盘
└── resources/
    └── styles/
        ├── dark.qss              # 深色主题
        └── light.qss             # 浅色主题
```

## 技术栈

| 组件 | 技术 | 用途 |
|------|------|------|
| 底层捕获 | [Scapy](https://scapy.readthedocs.io/) | 全协议数据包捕获和解析 |
| HTTPS 拦截 | [mitmproxy](https://mitmproxy.org/) | HTTPS 中间人代理和流量解密 |
| GUI | [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) | 桌面界面，表格模型，图表 |
| 存储 | SQLite + deque | 实时环形缓冲 + 持久化存储 |
| 包管理 | [uv](https://docs.astral.sh/uv/) | Python 版本和依赖管理 |

## 许可证

本项目使用 GPL v2 许可证，因为 Scapy 是 GPL v2 许可的库。
