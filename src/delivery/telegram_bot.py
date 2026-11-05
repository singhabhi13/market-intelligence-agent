import os, requests

class TelegramDelivery:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")

    def send_message(self, text: str) -> bool:
        if not self.token or not self.chat_id:
            print("Telegram credentials missing. Skipping delivery.")
            return False
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        res = requests.post(url, json={"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"}, timeout=10)
        return res.status_code == 200
