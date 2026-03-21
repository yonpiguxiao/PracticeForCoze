import random
import os
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from cozepy import Coze, TokenAuth, COZE_CN_BASE_URL, Message, ChatStatus
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)
COMMON_IDIOMS = ["十全十美", "三心二意"]

class IdiomGame:
    def __init__(self):
        self.api_token = os.environ.get("COZE_API_TOKEN")
        self.bot_id = os.environ.get("BOT_ID")
        self.user_id = os.environ.get("USER_ID")

        if not all([self.api_token, self.bot_id, self.user_id]):
            raise ValueError("缺少必要的环境变量，请检查 .env 文件")

        self.current_idiom = None
        self.game_history = []
        self.coze = Coze(
            auth = TokenAuth(token=self.api_token),
            base_url = COZE_CN_BASE_URL
        )


    def get_random_idiom(self):
        return random.choice(COMMON_IDIOMS)

    def reset_game(self):
        """重置游戏"""
        self.current_idiom = None
        self.game_history = []

    def add_to_history(self, user_idiom, sdk_response):
        record = {
            "user": user_idiom,
            "ai": sdk_response,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
        self.game_history.insert(0, record)

        if len(self.game_history) > 20:
            self.game_history = self.game_history[:20]


    def get_sdk_response(self, user_input):
        try:
            # 如果是开始游戏，让 AI 生成一个成语
            if user_input == "开始":
                messages = [
                    Message(
                        role="user",
                        content="请生成一个四字成语作为成语接龙的开始",
                        content_type="text",
                        type="question"
                    )
                ]
            else:
                messages = [
                    Message(
                        role="user",
                        content=f"成语接龙游戏，上一个成语是:{self.current_idiom},请接下一个成语",
                        content_type="text",
                        type="question"
                    ),
                    Message(
                        role="user",
                        content=user_input,
                        content_type="text",
                        type="question"
                    )
                ]
            chat = self.coze.chat.create(
                bot_id=self.bot_id,
                user_id=self.user_id,
                additional_messages=messages,
                auto_save_history=True
            )
            while chat.status == ChatStatus.IN_PROGRESS:
                chat = self.coze.chat.retrieve(
                    conversation_id=chat.conversation_id,
                    chat_id=chat.id
                )
            if chat.status == ChatStatus.COMPLETED:
                messages = self.coze.chat.messages.list(
                    conversation_id=chat.conversation_id,
                    chat_id=chat.id
                )
            sdk_response = None
            for msg in messages:
                if hasattr(msg, 'role') and msg.role == 'assistant':
                    sdk_response = msg.content.strip()
                    sdk_response = "".join(filter(lambda x: '\u4e00' <= x <= '\u9fff', sdk_response))
                    break

            if sdk_response and len(sdk_response) == 4:
                # 如果是开始游戏，只更新当前成语，不添加到历史记录
                if user_input == "开始":
                    self.current_idiom = sdk_response
                    return {
                        'success': True,
                        'sdk_response': sdk_response,
                        'current_idiom': self.current_idiom,
                        "histroy": self.game_history
                    }
                else:
                    self.add_to_history(user_input, sdk_response)
                    self.current_idiom = sdk_response

                    return {
                        'success': True,
                        'sdk_response': sdk_response,
                        'current_idiom': self.current_idiom,
                        "histroy": self.game_history
                    }
            
        except Exception as e:
            return {"success": False, "error": str(e)}


game = IdiomGame()

@app.route('/')
def index():
    from flask import send_file
    return send_file('idiom_chain.html')


@app.route('/api/play', methods = ['POST'])
@app.route('/api/play/', methods = ['POST'])
def play_game():
    data = request.get_json()
    user_input = data.get('idiom', '').strip()
    
    # 处理重新开始
    if user_input == "重新开始":
        game.reset_game()
        # 重新开始时，让 AI 生成一个新成语
        result = game.get_sdk_response("开始")
        return jsonify(result)
    
    if len(user_input) != 4:
        return jsonify({"success": False, "error": "请输入 4 字成语"})
    result = game.get_sdk_response(user_input)
    return jsonify(result)


@app.route('/api/start', methods = ['POST'])
@app.route('/api/start/', methods = ['POST'])
def start_game():
    """开始新游戏，由 AI 生成第一个成语"""
    game.reset_game()
    result = game.get_sdk_response("开始")
    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True, port=5000)