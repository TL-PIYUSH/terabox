from flask import Flask, request, jsonify
import requests
import re
import os
from urllib.parse import quote

app = Flask(__name__)

# Multiple public APIs (fallback system)
PUBLIC_APIS = [
    "https://terabox-worker.robinkumarshakya103.workers.dev/api?url={url}",
    "https://terabox-worker.robinkumarshakya103.workers.dev/api?url=https://1024terabox.com/s/{surl}",
    "https://tbx-proxy.shakir-ansarii075.workers.dev/?mode=resolve&surl={surl}",
]

def extract_surl(url: str) -> str | None:
    """Extract shorturl from any Terabox link"""
    patterns = [
        r'/s/([a-zA-Z0-9_-]+)',
        r'surl=([a-zA-Z0-9_-]+)',
        r'terabox\.com/([a-zA-Z0-9_-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def try_public_apis(url: str, surl: str):
    """Try multiple public APIs until one works"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
    }

    for api_template in PUBLIC_APIS:
        try:
            api_url = api_template.format(url=quote(url, safe=''), surl=surl)
            print(f"Trying: {api_url}")  # Vercel logs me dikhega

            resp = requests.get(api_url, headers=headers, timeout=20)

            if resp.status_code != 200:
                continue

            data = resp.json()

            # Format 1: robin worker
            if data.get("success") and data.get("files"):
                files = []
                for f in data["files"]:
                    files.append({
                        "title": f.get("file_name") or f.get("filename") or "Unknown",
                        "size": f.get("size"),
                        "thumbnail": f.get("thumbnail") or f.get("thumbs", {}).get("url1", ""),
                        "download": f.get("original_download_url") or f.get("download_url") or f.get("dlink"),
                        "stream": f.get("streaming_url"),
                    })
                return {"status": "success", "files": files, "source": "robin-worker"}

            # Format 2: tbx-proxy
            if data.get("data") and not data.get("error"):
                d = data["data"]
                return {
                    "status": "success",
                    "files": [{
                        "title": d.get("name") or d.get("title") or "Unknown",
                        "size": d.get("size"),
                        "thumbnail": d.get("thumb") or "",
                        "download": d.get("dlink") or d.get("download_url"),
                        "stream": None,
                    }],
                    "source": "tbx-proxy"
                }

            # Format 3: list based
            if data.get("list"):
                files = []
                for f in data["list"]:
                    files.append({
                        "title": f.get("server_filename") or f.get("filename") or "Unknown",
                        "size": f.get("size"),
                        "thumbnail": (f.get("thumbs") or {}).get("url1", ""),
                        "download": f.get("dlink"),
                        "stream": None,
                    })
                return {"status": "success", "files": files, "source": "list-format"}

        except Exception as e:
            print(f"API failed: {e}")
            continue

    return None


@app.route('/')
def home():
    return jsonify({
        "status": "active",
        "message": "Welcome to the Terabox Downloader API",
        "creator": "Created by nano (t.me/genxnano)",
        "endpoints": {
            "/download": {
                "method": "POST",
                "description": "Download Terabox link",
                "required_body": {
                    "url": "The URL of the Terabox link to download"
                }
            },
            "/docs": {
                "method": "GET",
                "description": "API Documentation"
            }
        }
    })


@app.route('/download', methods=['POST'])
def download():
    try:
        data = request.get_json(silent=True)

        if not data or 'url' not in data:
            return jsonify({
                "status": "error",
                "message": "URL is required in request body"
            }), 400

        terabox_link = data['url'].strip()

        if not terabox_link:
            return jsonify({
                "status": "error",
                "message": "URL cannot be empty"
            }), 400

        surl = extract_surl(terabox_link)
        if not surl:
            return jsonify({
                "status": "error",
                "message": "Invalid Terabox URL. Could not extract shorturl."
            }), 400

        result = try_public_apis(terabox_link, surl)

        if result and result.get("files"):
            # Compatibility with old response format
            first = result["files"][0]
            return jsonify({
                "status": "success",
                "data": {
                    "title": first.get("title"),
                    "thumbnail": first.get("thumbnail"),
                    "resolutions": {
                        "Fast Download": first.get("download"),
                        "HD Video": first.get("download")
                    }
                },
                "files": result["files"],  # extra full list
                "source": result.get("source")
            })

        return jsonify({
            "status": "error",
            "message": "Could not fetch download links. The link may be private, password protected, expired, or all public resolvers are currently blocked by Terabox.",
            "surl": surl,
            "tip": "Try a different public link or wait some time."
        }), 502

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Internal server error: {str(e)}"
        }), 500


@app.route('/docs')
def docs():
    try:
        docs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'docs.md')
        if not os.path.exists(docs_path):
            docs_path = 'docs.md'

        with open(docs_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content, 200, {'Content-Type': 'text/markdown; charset=utf-8'}
    except:
        return jsonify({"status": "error", "message": "docs.md not found"}), 404


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
