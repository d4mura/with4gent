import re


def anonymize_text(text: str) -> str:
    """
    送受信メッセージ内のユーザーIDやグループIDなどの特定のパターンを匿名化する。
    例: U[0-9a-f]{32}, G[0-9a-f]{32}, C[0-9a-f]{32}
    """
    if not text:
        return text

    # LINEのIDパターン (User: U..., Group: G..., Room: C...)
    line_id_pattern = r"(U[0-9a-f]{32}|G[0-9a-f]{32}|C[0-9a-f]{32})"

    # 匿名化処理
    anonymized_text = re.sub(line_id_pattern, "[ID]", text)

    return anonymized_text
