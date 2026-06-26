from flask import Flask, request, jsonify
import requests
import binascii
import random
import sys
import os
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import my_pb2
    import output_pb2
except ImportError as e:
    logger.error(f"Failed to import protobuf: {e}")
    # Create dummy classes if imports fail
    class my_pb2:
        class GameData:
            def __init__(self):
                pass
    class output_pb2:
        class Garena_420:
            def __init__(self):
                pass

app = Flask(__name__)

# ---------- Constants ----------
MAJOR_LOGIN_URL = "https://loginbp.ggpolarbear.com/MajorLogin"
OAUTH_URL = "https://100067.connect.garena.com/oauth/guest/token/grant"
FREEFIRE_VERSION = "OB54"

KEY = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
IV = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

# ---------- Device Database ----------
DEVICES = [
    {"model": "SM-G998B", "android": "13", "api": "33", "cpu": "ARMv8 | 2800 | 8", "gpu": "Mali-G78", "res": ["1440", "1080"], "dpi": "480", "ram": "8192"},
    {"model": "realme C31", "android": "12", "api": "31", "cpu": "ARMv8 | 2000 | 8", "gpu": "Mali-G52", "res": ["720", "1600"], "dpi": "320", "ram": "4096"},
    {"model": "Mi 11", "android": "12", "api": "32", "cpu": "ARMv8 | 2500 | 8", "gpu": "Adreno 650", "res": ["1080", "2400"], "dpi": "395", "ram": "6144"},
    {"model": "OnePlus 9", "android": "13", "api": "33", "cpu": "ARMv8 | 2900 | 8", "gpu": "Adreno 660", "res": ["1080", "2400"], "dpi": "420", "ram": "8192"},
    {"model": "VIVO V21", "android": "12", "api": "31", "cpu": "ARMv8 | 2400 | 8", "gpu": "Mali-G57", "res": ["1080", "2400"], "dpi": "400", "ram": "8192"},
    {"model": "OPPO Reno6", "android": "11", "api": "30", "cpu": "ARMv8 | 2200 | 8", "gpu": "Mali-G52", "res": ["1080", "2400"], "dpi": "410", "ram": "6144"},
    {"model": "Pixel 6", "android": "13", "api": "33", "cpu": "ARMv8 | 2800 | 8", "gpu": "Mali-G78", "res": ["1080", "2400"], "dpi": "440", "ram": "8192"},
    {"model": "TECNO Spark 8", "android": "11", "api": "30", "cpu": "ARMv8 | 1800 | 8", "gpu": "Mali-G52", "res": ["720", "1640"], "dpi": "320", "ram": "4096"},
]

def get_random_device():
    device = random.choice(DEVICES)
    android_versions = ["11", "12", "13", "14"]
    api_levels = {"11": "30", "12": "31", "13": "33", "14": "34"}
    android = random.choice(android_versions)
    api = api_levels[android]
    return {
        "model": device["model"],
        "android": android,
        "api": api,
        "cpu": device["cpu"],
        "gpu": device["gpu"],
        "width": device["res"][0],
        "height": device["res"][1],
        "dpi": device["dpi"],
        "ram": device["ram"],
        "build": f"TP1A.220624.{random.randint(100,999)}"
    }

def encrypt_data(data_bytes):
    try:
        cipher = AES.new(KEY, AES.MODE_CBC, IV)
        padded = pad(data_bytes, AES.block_size)
        return cipher.encrypt(padded)
    except Exception as e:
        logger.error(f"Encryption error: {e}")
        return None

def get_name_region_from_reward(access_token):
    try:
        url = "https://prod-api.reward.ff.garena.com/redemption/api/auth/inspect_token/"
        headers = {
            "accept": "application/json, text/plain, */*",
            "access-token": access_token,
            "user-agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36"
        }
        resp = requests.get(url, headers=headers, verify=False, timeout=15)
        logger.debug(f"Reward API response: {resp.status_code}")
        data = resp.json()
        return data.get("uid"), data.get("name"), data.get("region")
    except Exception as e:
        logger.error(f"Reward API error: {e}")
        return None, None, None

def get_openid_from_shop2game(uid):
    if not uid:
        return None
    try:
        url = "https://topup.pk/api/auth/player_id_login"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36"
        }
        payload = {"app_id": 100067, "login_id": str(uid)}
        resp = requests.post(url, headers=headers, json=payload, verify=False, timeout=15)
        logger.debug(f"Shop2Game API response: {resp.status_code}")
        return resp.json().get("open_id")
    except Exception as e:
        logger.error(f"Shop2Game API error: {e}")
        return None

def perform_major_login(access_token, open_id):
    platforms = [8, 3, 4, 6]
    for platform_type in platforms:
        try:
            device = get_random_device()
            
            # Create game data
            game_data = my_pb2.GameData()
            game_data.timestamp = "2025-01-15 10:30:45"
            game_data.game_name = "free fire"
            game_data.game_version = 1
            game_data.version_code = "1.121.0"
            game_data.os_info = f"Android OS {device['android']} / API-{device['api']} ({device['build']})"
            game_data.device_type = "Handheld"
            game_data.network_provider = "Verizon Wireless"
            game_data.connection_type = "WIFI"
            game_data.screen_width = int(device['width'])
            game_data.screen_height = int(device['height'])
            game_data.dpi = device['dpi']
            game_data.cpu_info = device['cpu']
            game_data.total_ram = int(device['ram'])
            game_data.gpu_name = device['gpu']
            game_data.gpu_version = "OpenGL ES 3.2"
            game_data.user_id = f"Google|{random.randint(1000000000000, 9999999999999)}"
            game_data.ip_address = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
            game_data.language = "en"
            game_data.open_id = open_id
            game_data.access_token = access_token
            game_data.platform_type = platform_type
            game_data.field_99 = str(platform_type)
            game_data.field_100 = str(platform_type)
            game_data.device_form_factor = "Phone"
            game_data.device_model = device['model']

            serialized = game_data.SerializeToString()
            encrypted = encrypt_data(serialized)
            if not encrypted:
                continue
                
            hex_encrypted = binascii.hexlify(encrypted).decode()
            edata = bytes.fromhex(hex_encrypted)

            headers = {
                "User-Agent": f"Dalvik/2.1.0 (Linux; U; Android {device['android']}; {device['model']})",
                "Connection": "Keep-Alive",
                "Accept-Encoding": "gzip",
                "Content-Type": "application/octet-stream",
                "X-Unity-Version": "2018.4.11f1",
                "X-GA": "v1 1",
                "ReleaseVersion": FREEFIRE_VERSION
            }

            resp = requests.post(MAJOR_LOGIN_URL, data=edata, headers=headers, verify=False, timeout=15)
            logger.debug(f"Major Login response: {resp.status_code} for platform {platform_type}")
            
            if resp.status_code == 200:
                try:
                    msg = output_pb2.Garena_420()
                    msg.ParseFromString(resp.content)
                    for field in msg.DESCRIPTOR.fields:
                        if field.name == "token":
                            token = getattr(msg, field.name)
                            if token:
                                logger.info(f"Token generated successfully for platform {platform_type}")
                                return token
                except Exception as e:
                    logger.error(f"Parse error: {e}")
                    continue
        except Exception as e:
            logger.error(f"Major login error for platform {platform_type}: {e}")
            continue
    return None

def perform_guest_login(uid, password):
    try:
        payload = {
            'uid': str(uid),
            'password': str(password),
            'response_type': "token",
            'client_type': "2",
            'client_secret': "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
            'client_id': "100067"
        }
        headers = {
            'User-Agent': f"GarenaMSDK/4.0.19P9({random.choice(['SM-G998B','realme C31','Mi 11'])} ;Android {random.choice(['11','12','13'])};pt;BR;)",
            'Connection': "Keep-Alive",
            'Content-Type': "application/x-www-form-urlencoded"
        }
        
        resp = requests.post(OAUTH_URL, data=payload, headers=headers, timeout=15, verify=False)
        logger.debug(f"Guest login response: {resp.status_code}")
        logger.debug(f"Guest login response text: {resp.text[:200]}")
        
        data = resp.json()
        if 'access_token' in data:
            return data['access_token'], data.get('open_id')
        else:
            logger.error(f"Guest login failed: {data}")
            return None, None
    except Exception as e:
        logger.error(f"Guest login error: {e}")
        return None, None

# ---------- Routes ----------
@app.route('/', methods=['GET'])
def index():
    return jsonify({
        "api": "JWT Generator API (OB54)",
        "credit": "SHAPPNO GMR",
        "telegram": "@SHAPPNO_004X",
        "status": "running on Vercel ✅",
        "endpoints": {
            "/token": {
                "method": "GET",
                "params": {
                    "access_token": "string (optional)",
                    "uid": "string (optional)",
                    "password": "string (optional)"
                }
            },
            "/Bmw": {
                "method": "GET",
                "params": {
                    "uid": "string (required)",
                    "password": "string (required)"
                }
            }
        }
    })

@app.route('/token', methods=['GET'])
def token_endpoint():
    access_token = request.args.get('access_token')
    uid = request.args.get('uid')
    password = request.args.get('password')

    if access_token:
        uid_found, name, region = get_name_region_from_reward(access_token)
        if not uid_found:
            return jsonify({"status": "error", "message": "Invalid access_token"}), 400
        open_id = get_openid_from_shop2game(uid_found)
        if not open_id:
            return jsonify({"status": "error", "message": "Could not fetch open_id"}), 400
        jwt_token = perform_major_login(access_token, open_id)
        if jwt_token:
            return jsonify({"status": "success", "token": jwt_token, "uid": uid_found, "open_id": open_id})
        return jsonify({"status": "error", "message": "JWT generation failed"}), 500

    elif uid and password:
        acc_token, open_id = perform_guest_login(uid, password)
        if not acc_token or not open_id:
            return jsonify({"status": "error", "message": "Guest login failed"}), 401
        jwt_token = perform_major_login(acc_token, open_id)
        if jwt_token:
            return jsonify({"status": "success", "token": jwt_token, "uid": uid, "open_id": open_id})
        return jsonify({"status": "error", "message": "JWT generation failed"}), 500

    return jsonify({"status": "error", "message": "Provide access_token or uid+password"}), 400

# ---------- BMW Endpoint (Fixed) ----------
@app.route('/Bmw', methods=['GET', 'POST'])
def bmw_endpoint():
    # Support both GET and POST
    if request.method == 'POST':
        uid = request.json.get('uid') if request.json else request.form.get('uid')
        password = request.json.get('password') if request.json else request.form.get('password')
    else:
        uid = request.args.get('uid')
        password = request.args.get('password')
    
    # Log the request
    logger.info(f"BMW endpoint called with uid: {uid}, password: {'*' * len(password) if password else 'None'}")
    
    if not uid or not password:
        return jsonify({
            "status": "error", 
            "message": "uid and password are required",
            "usage": "/Bmw?uid=YOUR_UID&password=YOUR_PASSWORD",
            "example": "/Bmw?uid=123456789&password=yourpass"
        }), 400
    
    try:
        # Step 1: Guest login to get access_token
        logger.info("Attempting guest login...")
        acc_token, open_id = perform_guest_login(uid, password)
        
        if not acc_token:
            return jsonify({
                "status": "error", 
                "message": "Guest login failed. Invalid uid or password",
                "step": "guest_login_failed"
            }), 401
            
        if not open_id:
            return jsonify({
                "status": "error", 
                "message": "Guest login succeeded but open_id not found",
                "step": "open_id_missing"
            }), 400
        
        logger.info(f"Guest login successful. OpenID: {open_id}")
        
        # Step 2: Get user info from reward API
        logger.info("Fetching user info from reward API...")
        uid_found, name, region = get_name_region_from_reward(acc_token)
        
        if not uid_found:
            return jsonify({
                "status": "error", 
                "message": "Failed to fetch user info from reward API",
                "step": "reward_api_failed"
            }), 400
        
        logger.info(f"User info: UID={uid_found}, Name={name}, Region={region}")
        
        # Step 3: Get open_id from shop2game
        logger.info("Fetching open_id from shop2game...")
        open_id_from_shop = get_openid_from_shop2game(uid_found)
        
        if not open_id_from_shop:
            return jsonify({
                "status": "error", 
                "message": "Could not fetch open_id from shop2game",
                "step": "shop2game_failed"
            }), 400
        
        logger.info(f"Shop2Game open_id: {open_id_from_shop}")
        
        # Step 4: Generate JWT token
        logger.info("Generating JWT token...")
        jwt_token = perform_major_login(acc_token, open_id_from_shop)
        
        if not jwt_token:
            return jsonify({
                "status": "error", 
                "message": "JWT generation failed. Could not get token from MajorLogin",
                "step": "jwt_generation_failed"
            }), 500
        
        logger.info("JWT token generated successfully!")
        
        # Success response
        return jsonify({
            "status": "success",
            "token": jwt_token,
            "uid": uid_found,
            "open_id": open_id_from_shop,
            "name": name,
            "region": region,
            "platform": "Free Fire OB54",
            "message": "Token generated successfully"
        })
        
    except Exception as e:
        logger.error(f"BMW endpoint error: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e),
            "step": "exception"
        }), 500

# ========== VERCEL IMPORTANT ==========
# This is the key part - Vercel needs 'app' exported
app = app  # Make sure app is exported

# For Vercel serverless
def handler(request, context):
    return app(request, context)
