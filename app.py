import os
import time
import pymysql
from flask import Flask, request, jsonify
from google.cloud import storage
from google.auth.exceptions import DefaultCredentialsError

app = Flask(__name__)

# ──────────────────────────────────────────────
# MySQL 連線設定
#   本地開發：MYSQL_HOST=localhost, MYSQL_PORT=8625（預設）
#   Container 環境：MYSQL_HOST=mysql.clki101, MYSQL_PORT=3306
# ──────────────────────────────────────────────
DB_CONFIG = {
    "host":     os.environ.get("MYSQL_HOST", "localhost"),
    "port":     int(os.environ.get("MYSQL_PORT", 3306)),
    "user":     os.environ.get("MYSQL_USER", "root"),
    "password": os.environ.get("MYSQL_PASSWORD", "Roger1126"),
    "database": os.environ.get("MYSQL_DATABASE", "cki101"),
    "charset":  "utf8mb4",
}


def get_db():
    """建立並回傳一個 PyMySQL 連線"""
    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)


def init_db():
    """初始化：等待 MySQL ready 後建立 users 資料表"""
    retries = 10
    for i in range(retries):
        try:
            conn = get_db()
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS users (
                            id   INT AUTO_INCREMENT PRIMARY KEY,
                            name VARCHAR(100) NOT NULL,
                            age  INT NOT NULL
                        )
                    """)
                conn.commit()
            print("[init_db] 資料庫連線成功，資料表已就緒")
            return
        except pymysql.err.OperationalError as e:
            print(f"[init_db] MySQL 尚未就緒，{3} 秒後重試... ({i+1}/{retries})")
            time.sleep(3)
    raise RuntimeError("[init_db] 無法連線到 MySQL，請確認服務是否正常")


# ──────────────────────────────────────────────
# 路由
# ──────────────────────────────────────────────

@app.route('/')
def index():
    return "我是功能一的文字"


@app.route('/user', methods=['POST'])
def create_user():
    """新增用戶  Body: {"name": "王小明", "age": 25}"""
    data = request.get_json()
    name = data.get("name", "").strip()
    age  = data.get("age")

    if not name or age is None:
        return jsonify({"error": "name 和 age 為必填欄位"}), 400

    conn = get_db()
    with conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO users (name, age) VALUES (%s, %s)", (name, age)
            )
            new_id = cursor.lastrowid
        conn.commit()

    return jsonify({"id": new_id, "name": name, "age": age}), 201


@app.route('/user', methods=['GET'])
def get_users():
    """查詢所有用戶"""
    conn = get_db()
    with conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, name, age FROM users")
            users = cursor.fetchall()

    return jsonify(users), 200


@app.route('/user/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """刪除指定 id 的用戶"""
    conn = get_db()
    with conn:
        with conn.cursor() as cursor:
            affected = cursor.execute(
                "DELETE FROM users WHERE id = %s", (user_id,)
            )
        conn.commit()

    if affected == 0:
        return jsonify({"error": f"找不到 id={user_id} 的用戶"}), 404

    return jsonify({"message": f"用戶 id={user_id} 已刪除"}), 200


# ──────────────────────────────────────────────
@app.route('/gcp', methods=['GET'])
def list_gcs_buckets():
    """
    列出指定 GCP project 的 Cloud Storage buckets
    使用方式: GET /gcp?project_id=your-project-id
    憑證：自動使用 Application Default Credentials (ADC)
      - 本地開發：執行 `gcloud auth application-default login` 後自動取得
      - GCP 環境（GCE/Cloud Run/GKE）：自動使用 Service Account
    """
    project_id = request.args.get('project_id', '').strip()

    if not project_id:
        return jsonify({"error": "請提供 project_id 參數，例如: /gcp?project_id=my-project"}), 400

    try:
        # 使用 ADC 自動取得憑證，不需要手動指定金鑰檔
        client = storage.Client(project=project_id)
        buckets = client.list_buckets()
        bucket_list = [
            {
                "name": bucket.name,
                "location": bucket.location,
                "storage_class": bucket.storage_class,
            }
            for bucket in buckets
        ]
        return jsonify({
            "project_id": project_id,
            "bucket_count": len(bucket_list),
            "buckets": bucket_list,
        }), 200

    except DefaultCredentialsError:
        return jsonify({
            "error": "找不到 GCP 憑證，請執行 `gcloud auth application-default login` 或確認 Service Account 設定"
        }), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ──────────────────────────────────────────────
if __name__ == '__main__':
    init_db()   # 啟動時確保資料表已建立
    app.run(host='0.0.0.0', port=5000)
