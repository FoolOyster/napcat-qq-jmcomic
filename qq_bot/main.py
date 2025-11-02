import websockets
import json
import os
import re
import uvicorn
import jmcomic
from fastapi import FastAPI, Request
import gc
import asyncio
import psutil
import multiprocessing
import time
from datetime import datetime
import logging
from logging.handlers import TimedRotatingFileHandler

# ====================== 基础配置 ======================
app = FastAPI()
admin_id = 123456  # 管理者QQ号

HTTP_PORT = 8081  # HTTP客户端端口
WEBSOCKET_URL = "ws://127.0.0.1:3001"  # Websocket服务器地址
FILE_DIR = "./pdf/"
LOG_DIR = "./logs"

# ====================== 日志系统配置 ======================
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "jm_bot.log")

# 每4小时切换日志文件，保留14个（大约两天）
file_handler = TimedRotatingFileHandler(LOG_FILE, when="h", interval=4, backupCount=14, encoding="utf-8")
file_handler.suffix = "%Y-%m-%d_%H-%M.log"

log_formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
file_handler.setFormatter(log_formatter)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

logger = logging.getLogger("JM_BOT")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# ====================== 工具函数 ======================
def log(tag: str, msg: str, level="info"):
    """统一日志格式：写入控制台 + 文件"""
    full_msg = f"{tag} {msg}"
    if level == "error":
        logger.error(full_msg)
    elif level == "warning":
        logger.warning(full_msg)
    else:
        logger.info(full_msg)

# ================ 信息发送类 ================
class NapcatWebSocketBot:
    def __init__(self, websocket_url):
        self.websocket_url = websocket_url
    
    async def send_private_message(self, user_id, message):
        payload = {
            "action": "send_private_msg",
            "params": {
                "user_id": user_id,
                "message": [{"type": "text", "data": {"text": message}}],
            },
            "echo": f"private_text_{user_id}",
        }
        try:
            async with websockets.connect(self.websocket_url) as websocket:
                await websocket.send(json.dumps(payload))
                await websocket.recv()
        except Exception as e:
            log("[❌ message_sender]", f"发送私聊文本消息失败: {e}")

    async def send_group_message(self, group_id, message):
        payload = {
            "action": "send_group_msg",
            "params": {
                "group_id": group_id,
                "message": [{"type": "text", "data": {"text": message}}],
            },
            "echo": f"group_text_{group_id}",
        }
        try:
            async with websockets.connect(self.websocket_url) as websocket:
                await websocket.send(json.dumps(payload))
                await websocket.recv()
        except Exception as e:
            log("[❌ message_sender]", f"发送群文本消息失败: {e}")

    async def send_private_file(self, user_id, file_path):
        if not os.path.exists(file_path):
            return None
        file_url = f"file://{os.path.abspath(file_path)}"
        payload = {
            "action": "send_private_msg",
            "params": {
                "user_id": user_id,
                "message": [{"type": "file", "data": {"file": file_url}}],
            },
            "echo": f"private_file_{user_id}",
        }
        try:
            async with websockets.connect(self.websocket_url) as websocket:
                await websocket.send(json.dumps(payload))
                await websocket.recv()
            log("[✅ message_sender]", "私聊本子发送成功")
            return True
        except Exception as e:
            log("[❌ message_sender]", f"发送私聊文件失败: {e}")
            return False

    async def send_group_file(self, group_id, file_path):
        if not os.path.exists(file_path):
            return None
        file_url = f"file://{os.path.abspath(file_path)}"
        payload = {
            "action": "send_group_msg",
            "params": {
                "group_id": group_id,
                "message": [{"type": "file", "data": {"file": file_url}}],
            },
            "echo": f"group_file_{group_id}",
        }
        try:
            async with websockets.connect(self.websocket_url) as websocket:
                await websocket.send(json.dumps(payload))
                await websocket.recv()
            log("[✅ message_sender]", "群聊本子发送成功")
            return True
        except Exception as e:
            log("[❌ message_sender]", f"发送群文件失败: {e}")
            return False

# ====================== 全局状态管理 ======================
bot = NapcatWebSocketBot(WEBSOCKET_URL)
client = jmcomic.JmOption.default().new_jm_client()
max_episodes = 20
jm_functioning = True
jm_is_running = False

def get_jm_condition():
    return jm_functioning
def set_jm_condition(condition):
    global jm_functioning
    jm_functioning = condition
def get_jm_running():
    return jm_is_running
def set_jm_running(condition):
    global jm_is_running
    jm_is_running = condition
def set_download_max_epiosdes(num):
    global max_episodes
    max_episodes = num
def get_download_max_epiosdes():
    return max_episodes


# ====================== 下载逻辑 ======================
def jm_download_worker(number, result_dict):
    """子进程执行下载任务"""
    try:
        log("[🟢 JM]", f"开始下载本子: {number}")
        option = jmcomic.create_option_by_file('./option.yml')
        jmcomic.download_album(number, option)
        result_dict["result"] = True
        log("[📦 JM]", f"本子 {number} 下载完成")
    except Exception as e:
        log("[❌ JM]", f"下载失败: {e}")
        result_dict["result"] = False

def jm_download(number):
    """在独立进程中执行下载，防止内存污染"""
    manager = multiprocessing.Manager()
    result_dict = manager.dict()
    p = multiprocessing.Process(target=jm_download_worker, args=(number, result_dict))
    p.start()

    timeout = 1800  # 最长30分钟
    start_time = time.time()
    process = psutil.Process(os.getpid())

    while p.is_alive():
        #time.sleep(2)
        if time.time() - start_time > timeout:
            log("[⚠️ JM]", "下载超时，终止进程")
            p.terminate()
            break
    p.join()

    success = result_dict.get("result", False)
    del manager, result_dict
    gc.collect()
    return success


def find_file_by_name(title):
    """根据标题查找PDF"""
    safe_title = title.replace("?", "_").replace("/", "_")
    file_name = f"{safe_title}.pdf"
    file_path = os.path.join(FILE_DIR, file_name)
    if os.path.exists(file_path):
        return file_path, file_name
    return None, None


# ====================== 主要命令处理 ======================
async def process_jm_command(number, message_type, group_id, user_id):
    title = " "
    try:
        page = client.search_site(search_query=str(number))
        album = page.single_album
        title = album.title.replace("?", "_").replace("/", "_")
        if not title:
            log("[🚫 JM]", "本子标题为空，无法下载")
            return "❌ 本子标题为空"
        if len(album.episode_list) > get_download_max_epiosdes():
            log("[🚫 JM]", "本子章节太多，不支持下载")
            return f"❌ 本子章节过多(>{get_download_max_epiosdes()})"

        file_path, _ = find_file_by_name(title)
        if file_path:
            log("[✅ JM]", f"本地已存在该本子{number}")
            await send_message(message_type, group_id, user_id, f"📘 本地已存在本子 {number}")
            success = True
        else:
            await send_message(message_type, group_id, user_id, f"⏳ 正在下载本子 {number}")
            success = jm_download(number)
    except Exception as e:
        log("[❌ JM]", f"本子 {number} 下载失败 {e}")
        return "❌ 未能成功下载（可能ID错误或网络失败）"

    if success:
        file_path, _ = find_file_by_name(title)
        if not file_path:
            return "❌ 下载完成但未找到PDF文件"
        file_size = os.path.getsize(file_path) / (1024 * 1024)
        msg = f"✅ 天堂正在发送：\n车牌号：{number}\n本子名：{title}\n文件大小：({file_size:.2f}MB)"
        if message_type == "group":
            await bot.send_group_file(group_id, file_path)
        else:
            await bot.send_private_file(user_id, file_path)
        log("[✅ JM]", f"本子 {number} 处理完成并发送完成")
        return msg
    else:
        return "❌ 下载失败或超时"


async def look_jm_information(number):
    try:
        log("[⭕ JM]", f"正在检索本子{number}信息")
        page = client.search_site(search_query=str(number))
        album = page.single_album
        log("[🟢 JM]", f"本子{number}信息检索成功")
        return (
            f"🆔ID：{number}\n"
            f"⭕标题：{album.title}\n"
            f"💬描述：{album.description}\n"
            f"👥角色：{album.actors}\n"
            f"🏷标签：{album.tags}\n"
            f"⚛章节：{len(album.episode_list)}\n"
            f"👁浏览：{album.views}"
        )
    except Exception:
        log("[❌ JM]", f"本子{number}信息检索失败（可能ID错误或网络问题）")
        return "❌ 查询失败（可能ID错误或网络问题）"


# ====================== HTTP事件接收 ======================
@app.post("/")
async def root(request: Request):
    try:
        data = await request.json()
        asyncio.create_task(handle_message_event(data))
        return {"status": "success"}
    except Exception as e:
        log("[❌ System]", f"请求处理出错: {e}")
        return {"status": "error", "message": str(e)}


async def send_message(message_type, group_id, user_id, message):
    if message_type == "group" and group_id:
        await bot.send_group_message(group_id, message)
    elif message_type == "private" and user_id:
        await bot.send_private_message(user_id, message)

# ====================== 本子请求者信息 ======================
def requester_information(message_type, group_name, nickname, group_id, user_id,number,request_type):
    if message_type == 'group':
        log("[🟢 Request]", f"{group_name}群（{group_id}）中{nickname}（{user_id}）请求{request_type}本子：{number}")
    elif message_type == 'private':
        log("[🟢 Request]", f"私聊中{nickname}（{user_id}）请求{request_type}本子：{number}")

# ====================== 消息事件处理 ======================
async def handle_message_event(data):
    post_type = data.get("post_type")
    if post_type != "message":
        return

    message_type = data.get("message_type")
    raw_message = data.get("raw_message", "").strip()
    user_id = data.get("user_id")
    group_id = data.get("group_id")

    match_ON = re.match(r"开启禁漫功能", raw_message)
    match_OFF = re.match(r"关闭禁漫功能", raw_message)
    match_MDE = re.match(r"^/jm-setmax\s+(\d+)$", raw_message)
    match_JM = re.match(r"^/jm\s+(\d+)$", raw_message)
    match_JML = re.match(r"^/jm-look\s+(\d+)$", raw_message)

    # 管理命令
    if match_ON and user_id == admin_id:
        set_jm_condition(True)
        log("[🟢 Admin]", "✅ 开启禁漫功能")
        await send_message(message_type, group_id, user_id, "✅ 禁漫功能已开启")
        return
    if match_OFF and user_id == admin_id:
        set_jm_condition(False)
        log("[🟢 Admin]", "🚫 关闭禁漫功能")
        await send_message(message_type, group_id, user_id, "🚫 禁漫功能已关闭")
        return
    if match_MDE and user_id == admin_id:
        num = int(match_MDE.group(1))
        set_download_max_epiosdes(num)
        log("[🟢 Admin]", f"📘 章节数阈值已设为 {num}")
        await send_message(message_type, group_id, user_id, f"📘 章节数阈值已设为 {num}")
        return

    if not get_jm_condition() and (match_JM or match_JML):
        requester_information(message_type, data.get('group_name'), data.get('sender').get('nickname'), group_id, user_id, number, "处理")
        log("[🚫 Request]", "请求驳回，禁漫功能已关闭")
        await send_message(message_type, group_id, user_id, "禁漫功能未开启")
        return

    # 下载或查看逻辑
    global jm_is_running
    if jm_is_running and (match_JM or match_JML):
        requester_information(message_type, data.get('group_name'), data.get('sender').get('nickname'), group_id, user_id, number, "处理")
        log("[🚫 Request]", "请求驳回，其他本子正在处理中")
        await send_message(message_type, group_id, user_id, "🚫 正在处理其他本子，请稍候")
        return

    jm_is_running = True
    if match_JM:
        number = match_JM.group(1)
        requester_information(message_type, data.get('group_name'), data.get('sender').get('nickname'), group_id, user_id, number, "下载")
        response = await process_jm_command(number, message_type, group_id, user_id)
        await send_message(message_type, group_id, user_id, response)
    elif match_JML:
        number = match_JML.group(1)
        requester_information(message_type, data.get('group_name'), data.get('sender').get('nickname'), group_id, user_id, number, "检索")
        await send_message(message_type, group_id, user_id, f"🔍 正在检索本子 {number}")
        info = await look_jm_information(number)
        await send_message(message_type, group_id, user_id, info)
    jm_is_running = False


# ====================== 内存管理任务 ======================
async def periodic_cleanup():
    """定期清理内存 + 智能重启"""
    while True:
        await asyncio.sleep(300)
        if hasattr(gc, "collect"):
            gc.collect()
        process = psutil.Process(os.getpid())
        mem = process.memory_info().rss / 1024 / 1024
        log("[🚀 SYSTEM]", f"定期检测内存: {mem:.2f} MB")

        if get_jm_running():
            log("[📘 SYSTEM]", "检测到任务运行中，跳过重启检查")
            continue

        if mem > 600:
            log("[⚠️ SYSTEM]", "检测到空闲状态且内存超限，准备自动重启")
            os._exit(0)


# ====================== 主函数入口 ======================
async def main():
    print("🚀 Napcat QQ机器人启动中...")
    print(f"📁 文件目录: {os.path.abspath(FILE_DIR)}")
    print(f"🌐 WebSocket服务器: {WEBSOCKET_URL}")
    print(f"🔗 HTTP监听端口: {HTTP_PORT}")

    asyncio.create_task(periodic_cleanup())

    config = uvicorn.Config(app, host="127.0.0.1", port=HTTP_PORT, loop="asyncio", access_log=False)
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    log("[🚀 SYSTEM]", "JM 下载管理器启动")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("[🛑 SYSTEM]", "用户手动终止程序")



