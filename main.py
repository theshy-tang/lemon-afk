import requests
import time
import os
import random
import logging
from datetime import datetime, timezone, timedelta

# ========= 配置 =========

EMAIL = tangible4512@gmail.com
PASSWORD = jrwr0s4rst
BASE_URL = "https://servercreationlemon.onrender.com"
LOGIN_URL = f"{BASE_URL}/auth/login"
ME_URL = f"{BASE_URL}/auth/me"
AFK_URL = f"{BASE_URL}/credits/afk"

HEADERS = {
    "accept": "application/json",
    "content-type": "application/json",
    "user-agent": "LemonHostClient/1.1"
}

MIN_INTERVAL = 25
MAX_INTERVAL = 150
BASE_JITTER = 0.08

MAX_RUNTIME_HOURS = 6        # 最长连续运行时间
SKIP_PROB_DAY = 0.05
SKIP_PROB_NIGHT = 0.12

# ========= 日志 =========

logging.basicConfig(
    filename="afk_ultra_safe.log",
    level=logging.INFO,
    format="%(asctime)s - %(message)s"
)

start_time = time.time()

# ========= 工具函数 =========

def is_night():
    hour = datetime.now().hour
    return 0 <= hour < 8


def runtime_factor():
    """运行越久，间隔越大（最高 +30%）"""
    hours = (time.time() - start_time) / 3600
    return min(1 + hours * 0.1, 1.3)


# ========= API =========

def login():
    r = requests.post(
        LOGIN_URL,
        headers=HEADERS,
        json={"email": EMAIL, "password": PASSWORD},
        timeout=10
    )
    r.raise_for_status()
    return r.json().get("token")


def get_user_info(token):
    r = requests.get(
        ME_URL,
        headers={**HEADERS, "authorization": f"Bearer {token}"},
        timeout=10
    )
    if r.status_code == 401:
        return "EXPIRED"
    r.raise_for_status()
    return r.json()["user"]


def send_afk(token):
    r = requests.post(
        AFK_URL,
        headers={**HEADERS, "authorization": f"Bearer {token}"},
        timeout=10
    )
    r.raise_for_status()


# ========= 主逻辑 =========

def main():
    token = login()
    fail = 0

    while True:
        # 软退出
        if (time.time() - start_time) > MAX_RUNTIME_HOURS * 3600:
            logging.info("Max runtime reached, exit")
            break

        try:
            user = get_user_info(token)
            if user == "EXPIRED":
                token = login()
                continue

            afk_rate = user["afkRate"]
            last = datetime.fromisoformat(
                user["lastAFKHeartbeat"].replace("Z", "+00:00")
            )

            base = 30 / afk_rate
            interval = max(MIN_INTERVAL, min(base, MAX_INTERVAL))

            # 昼夜调节
            skip_prob = SKIP_PROB_NIGHT if is_night() else SKIP_PROB_DAY
            interval *= runtime_factor()
            interval *= random.uniform(1 - BASE_JITTER, 1 + BASE_JITTER)

            # 时间窗口（±15%）
            window_shift = random.uniform(-0.15, 0.15) * interval
            next_time = last + timedelta(seconds=interval + window_shift)

            wait = (next_time - datetime.now(timezone.utc)).total_seconds()
            if wait > 0:
                time.sleep(wait)

            # 概率跳过
            if random.random() < skip_prob:
                logging.info("Skip heartbeat (human-like idle)")
                continue

            send_afk(token)
            logging.info(
                f"AFK sent | interval={interval:.1f}s | night={is_night()}"
            )

            fail = 0

        except Exception as e:
            fail += 1
            backoff = min(60 * fail, 300)
            logging.error(f"Error: {e}, backoff={backoff}s")
            time.sleep(backoff)


if __name__ == "__main__":
    main()

