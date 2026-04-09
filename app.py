from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from github import Github, GithubException
import base64

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/get-files', methods=['POST'])
def get_files():
    try:
        data = request.json
        token = data.get('token')
        owner = data.get('owner')
        repo_name = data.get('repo')
        branch = data.get('branch', 'main')
        
        g = Github(token)
        repo = g.get_repo(f"{owner}/{repo_name}")
        
        try:
            contents = repo.get_contents("", ref=branch)
        except:
            contents = repo.get_contents("", ref="master")
            branch = "master"
        
        files = []
        def get_files_recursive(path=""):
            try:
                if path:
                    items = repo.get_contents(path, ref=branch)
                else:
                    items = contents
                for item in items:
                    if item.type == "file":
                        files.append({
                            "name": item.name,
                            "path": item.path,
                            "size": item.size,
                            "sha": item.sha
                        })
                    elif item.type == "dir":
                        get_files_recursive(item.path)
            except:
                pass
        
        get_files_recursive()
        return jsonify({"success": True, "files": files, "branch": branch})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# API: ফাইলের কন্টেন্ট পড়ার জন্য (টেক্সট ফাইলের জন্য)
@app.route('/api/get-file-content', methods=['POST'])
def get_file_content():
    try:
        data = request.json
        token = data.get('token')
        owner = data.get('owner')
        repo_name = data.get('repo')
        branch = data.get('branch', 'main')
        file_path = data.get('path')
        
        g = Github(token)
        repo = g.get_repo(f"{owner}/{repo_name}")
        
        file_content = repo.get_contents(file_path, ref=branch)
        content_base64 = file_content.content
        
        # টেক্সট ফাইল চেক করার চেষ্টা
        try:
            content = base64.b64decode(content_base64).decode('utf-8')
            return jsonify({"success": True, "content": content, "is_binary": False})
        except UnicodeDecodeError:
            # বাইনারি ফাইলের জন্য মেসেজ দেখানো
            return jsonify({
                "success": True, 
                "content": "[Binary file - cannot display as text]", 
                "is_binary": True,
                "size": file_content.size
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# API: ফাইল আপডেট করার জন্য (এডিট)
@app.route('/api/update-file-content', methods=['POST'])
def update_file_content():
    try:
        data = request.json
        token = data.get('token')
        owner = data.get('owner')
        repo_name = data.get('repo')
        branch = data.get('branch', 'main')
        file_path = data.get('path')
        content = data.get('content')  # This is base64 encoded
        
        g = Github(token)
        repo = g.get_repo(f"{owner}/{repo_name}")
        
        # পুরনো ফাইলের SHA পাওয়া
        file_content = repo.get_contents(file_path, ref=branch)
        
        # ফাইল আপডেট করা (base64 content সরাসরি ব্যবহার করে)
        repo.update_file(
            file_path, 
            f"Edit {file_path} via Web Manager", 
            content,  # সরাসরি base64 স্ট্রিং
            file_content.sha, 
            branch=branch
        )
        
        return jsonify({"success": True, "message": f"File {file_path} updated successfully"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# API: ফাইল আপলোড/রিপ্লেস করার জন্য
@app.route('/api/upload-file', methods=['POST'])
def upload_file():
    try:
        data = request.json
        token = data.get('token')
        owner = data.get('owner')
        repo_name = data.get('repo')
        file_path = data.get('path')
        content = data.get('content')  # This is base64 encoded from frontend
        branch = data.get('branch', 'main')
        commit_message = data.get('message', f"Upload/Update {file_path}")
        
        g = Github(token)
        repo = g.get_repo(f"{owner}/{repo_name}")
        
        try:
            existing = repo.get_contents(file_path, ref=branch)
            # আপডেট করার সময় base64 content সরাসরি ব্যবহার
            repo.update_file(file_path, commit_message, content, existing.sha, branch=branch)
            action = "updated"
        except GithubException as e:
            if e.status == 404:
                # ফাইল নেই, নতুন তৈরি
                repo.create_file(file_path, commit_message, content, branch=branch)
                action = "created"
            else:
                raise e
        
        return jsonify({"success": True, "action": action, "message": f"File {action} successfully"})
    except GithubException as e:
        return jsonify({"success": False, "error": f"GitHub API Error: {e.data.get('message', str(e))}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# API: ফাইল ডিলিট করার জন্য
@app.route('/api/delete-file', methods=['POST'])
def delete_file():
    try:
        data = request.json
        token = data.get('token')
        owner = data.get('owner')
        repo_name = data.get('repo')
        file_path = data.get('path')
        branch = data.get('branch', 'main')
        
        g = Github(token)
        repo = g.get_repo(f"{owner}/{repo_name}")
        
        file_content = repo.get_contents(file_path, ref=branch)
        repo.delete_file(file_path, f"Delete {file_path}", file_content.sha, branch=branch)
        
        return jsonify({"success": True, "message": f"File {file_path} deleted successfully"})
    except GithubException as e:
        if e.status == 404:
            return jsonify({"success": False, "error": "File not found in repository"})
        return jsonify({"success": False, "error": e.data.get('message', str(e))})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':

    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)