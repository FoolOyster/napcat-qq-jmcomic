# Napcat-NTQQ-JMcomic
基于[NapCat](https://napneko.github.io/)之类的NTQQ框架，通过OneBot协议约定，调用[JMComic-Crawler-Python](https://github.com/hect0x7/JMComic-Crawler-Python)提供的Python API访问禁漫天堂，实现一个会发送禁漫天堂本子的QQ机器人

---
## 如何配置
### 开始之前
+ 自行确保python安装库：jmcomic，img2pdf，websockets，uvicorn，fastapi，psutil
### 配置工作
+ 在Napcat中登录作为发送禁漫本子机器人的QQ，在然后Napcat中设置好网络配置并开启：HTTP客户端和Websocket服务器，用于接收消息和发送消息和文件。
+ 记录好上述网络配置的端口，在main.py文件里调好对应端口。
+ main.py文件里的admin_id设置成能管控机器人的QQ号（管理者）。
+ option.yml文件里的配置可以参考 [JM配置文件指南](https://jmcomic.readthedocs.io/zh-cn/latest/option_file_syntax/#2-option
)按自己喜好配置。

---
## 流程说明
机器人接收信息，匹配相关指令，进行下载禁漫漫画，按option.yml要求转为pdf格式，下载完成后机器人发送pdf文件

---
## 使用方法
机器人QQ接收一切私聊消息和群聊消息做出回应
### 普通用户指令 (2)

| 指令格式 | 功能 |
|-------|-------|
| [/jm]() number | 请求下载车牌号为number的本子，下载成功后发送 |
| [/jm-look]() number | 请求检索车牌号为number本子的相关信息 |

### 管理者指令 (3)
| 指令格式 | 功能 |
|-------|-------|
| [/jm-setmax]() number | 将本子下载章节数阈值设置为number（本子章节数超过这个数不下载） |
| [开启禁漫功能]() | 开启机器人的请求禁漫漫画功能 |
| [关闭禁漫功能]() | 开启机器人的请求禁漫漫画功能 |
