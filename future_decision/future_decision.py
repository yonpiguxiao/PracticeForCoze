import uuid
import os
import time
import logging
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from cozepy import Coze, TokenAuth, COZE_CN_BASE_URL, Message, ChatStatus
from datetime import datetime
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


load_dotenv()

app = Flask(__name__)
CORS(app)
user_sessions = {}


class CozeService:
    def __init__(self):
        self.api_token = os.environ.get("COZE_API_TOKEN")
        self.bot_id = os.environ.get("BOT_ID")
        self.user_id = os.environ.get("USER_ID")
        logger.info(f"bot_id:{self.bot_id}")

        if not all([self.api_token, self.bot_id, self.user_id]):
            raise ValueError("缺少必要的环境变量，请检查 .env 文件")

        self.coze = Coze(
            auth = TokenAuth(token=self.api_token),
            base_url = COZE_CN_BASE_URL
        )


    def get_sdk_response(self, user_message,user_identifier):
        logger.info(f"收到用户消息：{user_message}")
        try: 
            if user_identifier in user_sessions:
                session_data = user_sessions[user_identifier]
                conversation_id = session_data['conversation_id']
                user_id = session_data['user_id']
                messages = [
                    Message(
                        role="user",
                        content=user_message,
                        content_type="text",
                        type="question"
                    )
                ]
                logger.info(f"创建对话，bot_id={self.bot_id}, user_id={self.user_id}")
                chat = self.coze.chat.create(
                    bot_id=self.bot_id,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    additional_messages=messages,
                    auto_save_history=True
                )
                logger.info(f"对话创建成功，chat_id={chat.id}, status={chat.status}, last_error={getattr(chat, 'last_error', 'N/A')}")
            else:
                user_id = str(uuid.uuid4())
                messages = [
                    Message(
                        role="user",
                        content=user_message,
                        content_type="text",
                        type="question"
                    )
                ]
                logger.info(f"创建对话，bot_id={self.bot_id}, user_id={self.user_id}")
                chat = self.coze.chat.create(
                    bot_id=self.bot_id,
                    user_id=user_id,
                    additional_messages=messages,
                    auto_save_history=True
                )
                logger.info(f"对话创建成功，chat_id={chat.id}, status={chat.status}, last_error={getattr(chat, 'last_error', 'N/A')}")
                user_sessions[user_identifier] = {
                    "conversation_id": chat.conversation_id,
                    "user_id": user_id,
                    "chat_id": chat.id
                }

            while chat.status == ChatStatus.IN_PROGRESS:
                time.sleep(0.5)  # 添加延迟避免过度轮询
                chat = self.coze.chat.retrieve(
                    conversation_id=chat.conversation_id,
                    chat_id=chat.id
                )
                logger.info(f"轮询对话状态：{chat.status}, last_error={getattr(chat, 'last_error', 'N/A')}, chat 对象：{chat}")
            
            logger.info(f"对话完成，最终状态：{chat.status}")
            
            if chat.status == ChatStatus.COMPLETED:
                messages = self.coze.chat.messages.list(
                    conversation_id=chat.conversation_id,
                    chat_id=chat.id
                )
                logger.info(f"获取到 {len(messages)} 条消息")
                for msg in messages:
                    if msg.role == 'assistant':
                        logger.info(f"找到助手消息：{msg.content[:50]}...")
                        return {"status": "success", "content": msg.content}
                logger.warning("没有找到助手消息")
                return {"status": "failed", "content": "对话完成但没有收到助手回复"}
            else:
                logger.error(f"对话状态异常：{chat.status}")
                return {"status": "failed", "content": f"对话状态异常：{chat.status}"}
                
        except Exception as e:
            logger.error(f"发生异常：{str(e)}", exc_info=True)
            return {"status": "error", "content": f"服务器错误：{str(e)}"}

coze_service = CozeService() 

@app.route('/')
def index():
    return send_file('future_decision.html')

@app.route('/chat', methods=["POST"])
def chat():
    data = request.json
    user_message = data.get('message')
    logger.info(f"/chat 接口收到请求：{user_message}")
    
    user_identifier = request.remote_addr

    result = coze_service.get_sdk_response(user_message, user_identifier)
    logger.info(f"返回结果：{result}")
    return jsonify(result)


def clean_sessions():
    expired_sessions = []
    for user_identifier, session_data in user_sessions:
        expired_sessions.append(user_identifier)
    for user_identifier in expired_sessions:
        del user_sessions[user_identifier]

if __name__ == '__main__':
    app.run(debug=True, port=5000)