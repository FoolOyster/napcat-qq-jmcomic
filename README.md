# 📦 Napcat QQ 禁漫下载机器人

一个基于 **FastAPI + WebSocket + Napcat + jmcomic** 的 QQ 自动本子下载与发送机器人。  
支持 QQ 群聊与私聊命令触发下载，自动将禁漫漫画（jmcomic）保存为 PDF 并发送给请求者。

---

## ✨ 功能概述

- ✅ 支持 `/jm <本子ID>` 一键下载禁漫漫画  
- 🔍 支持 `/jm-look <本子ID>` 查询本子信息（标题、标签、角色等）  
- 💾 下载后自动生成 PDF 文件并缓存到本地  
- 📤 支持 QQ 群聊与私聊自动发送文件  
- 🧠 多进程下载防止内存污染，自动垃圾回收  
- 🔁 每 4 小时自动分割日志文件并保存 14 份  
- ⚙️ 内存监控与自动重启机制  
- 🔒 可通过管理员命令启用或关闭禁漫功能  

---

## 🧩 项目结构

```
napcat-qq-jmcomic/
├── qq_bot/
│   ├── main.py                               # 主程序，FastAPI + WebSocket + 下载逻辑
│   ├── option.yml                            # jmcomic 下载配置文件（需自行配置）
│   ├── download/                             # 已下载本子 ablum 存放目录
│   │   ├──本子标题1/
│   │   ├──本子标题2/
│   │   └── …
│   ├── pdf/                                  # 下载本子转换后 PDF 存放目录
│   │   ├──本子标题1.pdf
│   │   ├──本子标题2.pdf
│   │   └── …
│   └── logs/                                 # 日志文件目录
│       ├──jm_bot.log
│       ├──jm_bot.log.202x-xx-xx_xx-xx.log
│       └── …
└─ README.md                                  # 使用文档（本文件）
```

---

## ⚙️ 运行环境

- **Python 版本**：>= 3.9  
- **系统要求**：Windows / Linux / macOS  
- **依赖库**：

```bash
pip install fastapi uvicorn websockets jmcomic psutil img2pdf
```

推荐使用虚拟环境：

```bash
python -m venv venv
source venv/bin/activate   # Linux / macOS
venv\Scripts\activate      # Windows
```

---

## 🚀 启动方式

1. **克隆项目**

```bash
git clone https://github.com/FoolOyster/napcat-qq-jmcomic.git
cd napcat-qq-jmcomic
```

2. **配置 jmcomic**

编辑 `option.yml`，配置禁漫账号与下载路径（参考 jmcomic 官方说明）。

3. **运行 Napcat HTTP 客户 和 WebSocket 服务**

在 Napcat 网络配置中，启用 **HTTP客户段** 并设置为：
```
http://localhost:8081
```

启用 **WebSocket服务器** 并设置为：
```
127.0.0.1:3001
```

4. **启动机器人**

```bash
python main.py
```

日志输出类似：

```
[🚀 SYSTEM] Napcat QQ机器人启动中...
[📁 SYSTEM] 文件目录: /path/to/pdf
[🌐 SYSTEM] WebSocket服务器: ws://127.0.0.1:3001
[🔗 SYSTEM] HTTP监听端口: 8081
```

---

## 💬 使用指令

| 指令 | 权限 | 说明 |
|------|------|------|
| `/jm <ID>` | 所有人 | 下载对应禁漫本子并发送 |
| `/jm-look <ID>` | 所有人 | 查询本子信息 |
| `开启禁漫功能` | 管理员 | 开启机器人下载功能 |
| `关闭禁漫功能` | 管理员 | 关闭机器人下载功能 |
| `/jm-setmax <数字>` | 管理员 | 设置可下载的最大章节数 |

---

## 🧾 日志与内存管理

- 所有日志保存在 `./logs/jm_bot.log`
- 每 4 小时自动轮换日志文件，保留 14 份（约两天）
- 定期执行垃圾回收，每 5 分钟检测一次内存
- 若空闲状态内存 > 600MB，会自动退出以便外部守护进程重启

---

## 🧠 工作原理简介

1. **Napcat → FastAPI Webhook**
   - Napcat 收到 QQ 消息后转发到本地 `HTTP_PORT=8081`  
   - FastAPI 接收并触发对应命令解析。

2. **命令解析与任务调度**
   - 识别 `/jm` 或 `/jm-look` 指令  
   - 检查是否允许下载（功能开关 + 任务状态）

3. **jmcomic 下载逻辑**
   - 创建独立子进程执行下载任务  
   - 完成后生成 PDF 并存入 `/pdf/`

4. **WebSocket 文件发送**
   - 调用 Napcat WebSocket API 发送 QQ 消息或文件。

---

## 🧩 代码说明（核心组件）

- `NapcatWebSocketBot`：封装 Napcat WebSocket 调用（私聊、群聊、文件发送）  
- `jm_download_worker()`：子进程执行下载任务  
- `periodic_cleanup()`：周期性垃圾回收与内存检测  
- `handle_message_event()`：核心指令解析与命令分发  
- `process_jm_command()`：执行下载 + 文件发送  

---

## ⚠️ 注意事项

- 禁漫下载需科学上网，否则 jmcomic 访问失败。  
- `admin_id` 需在代码中自行设置为管理员 QQ。  
- Napcat WebSocket 与本程序端口不要冲突。  
- 建议使用 **守护脚本（如 pm2/supervisor）** 监控程序运行状态。

---

## 📜 License

本项目仅供学习与技术研究使用。请勿将本项目用于违反法律法规的用途。  
如有侵权或违规风险，请立即停止使用。

---

## 💡 致谢

- [JMComic-Crawler-Python](https://github.com/hect0x7/JMComic-Crawler-Python) - 禁漫漫画下载库  
- [Napcat](https://github.com/NapNeko/NapcatQQ) - QQ 协议端实现  
