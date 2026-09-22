from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Root endpoint
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

# Download endpoint
@app.route('/download', methods=['POST'])
def download():
    try:
        data = request.get_json()
        
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

        # External API
        api_url = "https://ytshorts.savetube.me/api/v1/terabox-downloader"
        
        payload = {"url": terabox_link}
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.post(api_url, json=payload, headers=headers, timeout=30)

        if response.status_code == 200:
            try:
                result = response.json()
                
                if not result.get('response') or len(result['response']) == 0:
                    return jsonify({
                        "status": "error",
                        "message": "No data found for this link"
                    }), 404

                video_data = result['response'][0]
                
                output_data = {
                    "status": "success",
                    "data": {
                        "title": video_data.get('title', 'Unknown'),
                        "thumbnail": video_data.get('thumbnail', ''),
                        "resolutions": {
                            "Fast Download": video_data.get('resolutions', {}).get('Fast Download'),
                            "HD Video": video_data.get('resolutions', {}).get('HD Video')
                        }
                    }
                }
                
                return jsonify(output_data)
            
            except (KeyError, IndexError, TypeError) as e:
                return jsonify({
                    "status": "error",
                    "message": f"Error parsing response: {str(e)}"
                }), 500
        
        else:
            return jsonify({
                "status": "error",
                "message": f"Downloader API returned status code: {response.status_code}",
                "details": response.text[:200]
            }), response.status_code

    except requests.exceptions.Timeout:
        return jsonify({
            "status": "error",
            "message": "Request timed out. Please try again."
        }), 504

    except requests.exceptions.RequestException as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to connect to downloader API: {str(e)}"
        }), 502

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Internal server error: {str(e)}"
        }), 500

# Documentation endpoint
@app.route('/docs')
def docs():
    try:
        # docs.md project root me hota hai
        docs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'docs.md')
        
        # Fallback: current directory se try karo
        if not os.path.exists(docs_path):
            docs_path = 'docs.md'
            
        with open(docs_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
        return content, 200, {'Content-Type': 'text/markdown; charset=utf-8'}
        
    except FileNotFoundError:
        return jsonify({
            "status": "error",
            "message": "Documentation file (docs.md) not found"
        }), 404
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error reading docs: {str(e)}"
        }), 500

# Vercel ke liye zaroori nahi, lekin local testing ke liye
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
