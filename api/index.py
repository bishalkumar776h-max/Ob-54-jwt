from flask import Flask, request, jsonify
import requests
import binascii
import random
import sys
import os
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import logging
import json
import base64

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import protobuf, if fails create dummy
try:
    import my_pb2
    import output_pb2
    PROTOBUF_AVAILABLE = True
except ImportError as e:
    logger.error(f"Failed to import protobuf: {e}")
    PROTOBUF_AVAILABLE = False
    
    # Create dummy classes
    class my_pb2:
        class GameData:
            def __init__(self):
                self.timestamp = ""
                self.game_name = ""
                self.game_version = 0
                self.version_code = ""
                self.os_info = ""
                self.device_type = ""
                self.network_provider = ""
                self.connection_type = ""
                self.screen_width = 0
                self.screen_height = 0
                self.dpi = ""
                self.cpu_info = ""
                self.total_ram = 0
                self.gpu_name = ""
                self.gpu_version = ""
                self.user_id = ""
                self.ip_address = ""
                self.language = ""
                self.open_id = ""
                self.access_token = ""
                self.platform_type = 0
                self.field_99 = ""
                self.field_100 = ""
                self.device_form_factor = ""
                self.device_model = ""
                self.region = ""
            def SerializeToString(self):
                return b""
    
    class output_pb2:
        class Garena_420:
            def __init__(self):
                self.token = ""
            def ParseFromString(self, data):
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

def get_real_region(uid):
    """Detect region from UID"""
    uid_str = str(uid)
    if uid_str.startswith('1'):
        return "BR", "Brazil"
    elif uid_str.startswith('2'):
        return "IN", "India"
    elif uid_str.startswith('3'):
        return "ID", "Indonesia"
    elif uid_str.startswith('4'):
        return "TH", "Thailand"
    elif uid_str.startswith('5'):
        return "VN", "Vietnam"
    elif uid_str.startswith('6'):
        return "PH", "Philippines"
    elif uid_str.startswith('7'):
        return "MY", "Malaysia"
    elif uid_str.startswith('8'):
        return "SG", "Singapore"
    elif uid_str.startswith('9'):
        return "PK", "Pakistan"
    else:
        # Default based on length
        if len(uid_str) == 9:
            return "BR", "Brazil"
        elif len(uid_str) == 10:
            return "IN", "India"
        else:
            return "IN", "India"

def get_name_region_from_reward(access_token):
    """Get user info from reward API"""
    try:
        url = "https://prod-api.reward.ff.garena.com/redemption/api/auth/inspect_token/"
        headers = {
            "accept": "application/json, text/plain, */*",
            "access-token": access_token,
            "user-agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36"
        }
        resp = requests.get(url, headers=headers, verify=False, timeout=15)
        logger.debug(f"Reward API response: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            uid = data.get("uid")
            name = data.get("name")
            return uid, name
    except Exception as e:
        logger.error(f"Reward API error: {e}")
    
    return None, None

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
        logger.debug(f"Shop2Game response: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            return data.get("open_id")
    except Exception as e:
        logger.error(f"Shop2Game error: {e}")
    
    return None

def perform_major_login(access_token, open_id):
    """Generate JWT token with multiple platform attempts"""
    platforms = [8, 3, 4, 6]
    
    for platform_type in platforms:
        try:
            logger.info(f"Trying platform type: {platform_type}")
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
            game_data.region = "IN"  # India region

            # Serialize and encrypt
            serialized = game_data.SerializeToString()
            logger.debug(f"Serialized data length: {len(serialized)}")
            
            encrypted = encrypt_data(serialized)
            if not encrypted:
                logger.error("Encryption failed")
                continue
            
            # Convert to hex and then to bytes
            hex_encrypted = binascii.hexlify(encrypted).decode()
            edata = bytes.fromhex(hex_encrypted)
            logger.debug(f"Encrypted data length: {len(edata)}")

            # Headers
            headers = {
                "User-Agent": f"Dalvik/2.1.0 (Linux; U; Android {device['android']}; {device['model']})",
                "Connection": "Keep-Alive",
                "Accept-Encoding": "gzip",
                "Content-Type": "application/octet-stream",
                "X-Unity-Version": "2018.4.11f1",
                "X-GA": "v1 1",
                "ReleaseVersion": FREEFIRE_VERSION,
                "Content-Length": str(len(edata))
            }

            # Send request
            logger.info(f"Sending request to MajorLogin with platform {platform_type}")
            resp = requests.post(
                MAJOR_LOGIN_URL, 
                data=edata, 
                headers=headers, 
                verify=False, 
                timeout=30
            )
            
            logger.info(f"MajorLogin response status: {resp.status_code}")
            logger.debug(f"Response content length: {len(resp.content)}")
            logger.debug(f"Response content (first 100 bytes): {resp.content[:100]}")
            
            if resp.status_code == 200:
                try:
                    # Parse response
                    msg = output_pb2.Garena_420()
                    msg.ParseFromString(resp.content)
                    
                    # Get token
                    if hasattr(msg, 'token'):
                        token = msg.token
                        if token:
                            logger.info(f"✅ Token generated successfully! Platform: {platform_type}")
                            return token
                        else:
                            logger.warning("Token is empty")
                    else:
                        logger.warning("Token field not found in response")
                        
                except Exception as e:
                    logger.error(f"Parse error: {e}")
                    # Try to find token in raw response
                    try:
                        # Check if token is in the response bytes
                        response_text = resp.content.decode('utf-8', errors='ignore')
                        if 'token' in response_text.lower():
                            logger.info("Token found in response text")
                            # Try to extract token
                            import re
                            token_match = re.search(r'"token":"([^"]+)"', response_text)
                            if token_match:
                                return token_match.group(1)
                    except:
                        pass
            else:
                logger.error(f"MajorLogin returned status {resp.status_code}")
                logger.debug(f"Response: {resp.content[:200]}")
                
        except Exception as e:
            logger.error(f"Major login error for platform {platform_type}: {e}")
            continue
    
    # If all platforms fail, try direct token extraction
    logger.warning("All platforms failed, trying alternative method...")
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
            'User-Agent': f"GarenaMSDK/4.0.19P9({random.choice(['SM-G998B','realme C31','Mi 11'])} ;Android {random.choice(['11','12','13'])};pt;IN;)",
            'Connection': "Keep-Alive",
            'Content-Type': "application/x-www-form-urlencoded"
        }
        
        resp = requests.post(OAUTH_URL, data=payload, headers=headers, timeout=15, verify=False)
        logger.info(f"Guest login response: {resp.status_code}")
        
        data = resp.json()
        logger.debug(f"Guest login response: {json.dumps(data, indent=2)}")
        
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
        "api": "JWT Generator API (OB54) - India",
        "credit": "SHAPPNO GMR",
        "telegram": "@SHAPPNO_004X",
        "status": "running on Vercel ✅",
        "region": "India (IN)",
        "endpoints": {
            "/Bmw": {
                "method": "GET",
                "params": {
                    "uid": "string (required)",
                    "password": "string (required)"
                },
                "example": "/Bmw?uid=234567890&password=yourpass"
            }
        }
    })

# ---------- BMW Endpoint ----------
@app.route('/Bmw', methods=['GET', 'POST'])
def bmw_endpoint():
    # Get parameters
    if request.method == 'POST':
        if request.json:
            uid = request.json.get('uid')
            password = request.json.get('password')
        else:
            uid = request.form.get('uid')
            password = request.form.get('password')
    else:
        uid = request.args.get('uid')
        password = request.args.get('password')
    
    logger.info(f"BMW endpoint called with uid: {uid}")
    
    if not uid or not password:
        return jsonify({
            "status": "error", 
            "message": "uid and password are required",
            "usage": "/Bmw?uid=YOUR_UID&password=YOUR_PASSWORD",
            "example": "/Bmw?uid=234567890&password=yourpass"
        }), 400
    
    try:
        # Step 1: Guest login
        logger.info("Step 1: Guest login...")
        acc_token, open_id = perform_guest_login(uid, password)
        
        if not acc_token:
            return jsonify({
                "status": "error", 
                "message": "Guest login failed. Invalid uid or password",
                "step": "guest_login_failed"
            }), 401
            
        logger.info(f"✅ Guest login successful!")
        
        # Step 2: Get user info
        logger.info("Step 2: Getting user info...")
        uid_found, name = get_name_region_from_reward(acc_token)
        
        if not uid_found:
            logger.warning("Reward API failed, using provided uid...")
            uid_found = uid
            name = "Unknown"
        
        # Get region from UID
        region_code, region_name = get_real_region(uid_found)
        logger.info(f"User: {name}, UID: {uid_found}, Region: {region_code}")
        
        # Step 3: Get open_id from shop2game
        logger.info("Step 3: Getting open_id...")
        open_id_from_shop = get_openid_from_shop2game(uid_found)
        
        if not open_id_from_shop:
            logger.warning("Shop2Game failed, using open_id from guest login...")
            open_id_from_shop = open_id
            
        if not open_id_from_shop:
            return jsonify({
                "status": "error", 
                "message": "Could not fetch open_id",
                "step": "open_id_failed"
            }), 400
        
        logger.info(f"✅ OpenID: {open_id_from_shop}")
        
        # Step 4: Generate JWT
        logger.info("Step 4: Generating JWT token...")
        jwt_token = perform_major_login(acc_token, open_id_from_shop)
        
        if not jwt_token:
            # Try one more time with different approach
            logger.warning("JWT generation failed, retrying with different platform...")
            jwt_token = perform_major_login(acc_token, open_id_from_shop)
            
            if not jwt_token:
                return jsonify({
                    "status": "error", 
                    "message": "JWT generation failed. Please try again.",
                    "step": "jwt_generation_failed"
                }), 500
        
        logger.info("✅ JWT token generated successfully!")
        
        return jsonify({
            "status": "success",
            "token": jwt_token,
            "uid": uid_found,
            "open_id": open_id_from_shop,
            "name": name or "Unknown",
            "region": region_code,
            "region_name": region_name,
            "platform": "Free Fire OB54",
            "message": f"Token generated for {region_name} 🇮🇳"
        })
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e),
            "step": "exception"
        }), 500

# ========== VERCEL ==========
app = app

def handler(request, context):
    return app(request, context)
