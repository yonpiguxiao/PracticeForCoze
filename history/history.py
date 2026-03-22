import os
from flask import Flask, request, jsonify,  send_file
from flask_cors import CORS
from dotenv import load_dotenv
from cozepy import Coze, TokenAuth, COZE_CN_BASE_URL
import json

load_dotenv()

app = Flask(__name__)
CORS(app)  # 允许跨域请求


@app.route('/')
def index():
    return send_file('history.html')


@app.route('/generate_images', methods=['POST'])
def generate_images():
    try:
        user_input = request.json.get('input', '')

        if not user_input:
            return jsonify({'error': '输入不能为空'}), 400

        api_token = os.environ.get("COZE_API_TOKEN")
        workflow_id = os.environ.get("WORKFLOW_ID")

        if not api_token:
            return jsonify({'error': 'API令牌未配置'}), 500

        # 初始化Coze客户端
        coze = Coze(
            auth=TokenAuth(token=api_token),
            base_url=COZE_CN_BASE_URL
        )

        # 执行工作流
        workflow = coze.workflows.runs.create(
            workflow_id=workflow_id,
            parameters={
                "input": user_input
            }
        )

        print(workflow.data)
        # 提取前两个图片URL
        if hasattr(workflow, 'data') and workflow.data:
            # 假设返回的数据结构中有图片URL
            # 这里需要根据实际API返回结构调整
            # 以下为示例代码，可能需要调整
            data = json.loads(workflow.data)
            data_content = data['output']

            # 取前两个元素
        return jsonify({'images': data_content[:2]})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)