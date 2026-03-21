import os
from cozepy import Coze, TokenAuth, COZE_CN_BASE_URL
from dotenv import load_dotenv

load_dotenv()


def get_space_list():
    api_token = os.environ.get("COZE_API_TOKEN")

    if not api_token:
        print("请先设置令牌")

    coze = Coze(
        auth = TokenAuth(token=api_token),
        base_url = COZE_CN_BASE_URL
    )

    try:
        spaces = coze.workspaces.list()
        if hasattr(spaces, "items"):
            spaces = spaces.items
        print(spaces)
    except Exception as e:
        print(f"调用访问空间列表SDK失败:{str(e)}")


if __name__ == "__main__":
    get_space_list()

    