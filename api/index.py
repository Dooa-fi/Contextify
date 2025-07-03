import os
import re
import io
import base64
from datetime import datetime
import requests
from flask import Flask, render_template_string, request, Response, session
from markupsafe import Markup
from flask_session import Session


app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './.flask_session/'  # Optional, default
app.config['SESSION_PERMANENT'] = False
Session(app)

app.secret_key = 'your-secret-key-here'

GITHUB_REPO_REGEX = re.compile(r'^https://github\.com/([\w\-]+)/([\w\-]+)(/?|\.git)?$')

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Context for your Code</title>
    <style>
        body { 
            display: flex; 
            justify-content: center; 
            align-items: center; 
            min-height: 100vh; 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            box-sizing: border-box;
        }
        .container { 
            background: white; 
            padding: 30px; 
            border-radius: 12px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.2); 
            width: 100%;
            max-width: 500px;
        }
        h1 { 
            text-align: center; 
            margin-bottom: 30px; 
            color: #333;
            font-size: 28px;
            font-weight: 600;
        }
        .input-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: #555;
        }
        input[type="text"] { 
            width: 100%; 
            padding: 15px; 
            border: 2px solid #ddd;
            border-radius: 8px; 
            font-size: 16px;
            transition: border-color 0.3s;
            box-sizing: border-box;
        }
        input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
        }
        button { 
            width: 100%; 
            padding: 15px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; 
            border: none; 
            border-radius: 8px; 
            cursor: pointer; 
            font-size: 16px;
            font-weight: 600;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        button:hover { 
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        button:active {
            transform: translateY(0);
        }
        .alert {
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 8px;
            font-weight: 500;
        }
        .alert-success {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .alert-error {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .download-btn {
            width: 100%;
            padding: 15px;
            background: #28a745;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            margin-top: 20px;
        }
        .download-btn:hover {
            background: #218838;
        }
        .loading {
            display: none;
            text-align: center;
            margin-top: 20px;
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 10px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        textarea {
            width: 100%;
            height: 300px;
            margin-top: 20px;
            font-family: monospace;
            font-size: 12px;
            border-radius: 8px;
            border: 1px solid #ccc;
            padding: 10px;
            background: #f9f9f9;
            resize: vertical;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Context for your Code</h1>
        
        {% if error %}
            <div class="alert alert-error">{{ error }}</div>
        {% endif %}
        
        {% if success %}
            <div class="alert alert-success">{{ success }}</div>
        {% endif %}
        
        <form method="POST" onsubmit="showLoading()">
            <div class="input-group">
                <label for="github_link">GitHub Repository URL:</label>
                <input type="text" 
                       id="github_link" 
                       name="github_link" 
                       placeholder="https://github.com/username/repository" 
                       required
                       value="{{ github_link|default('') }}">
            </div>
            <button type="submit">🚀 Generate Context</button>
        </form>
        
        {% if context_text %}
            <textarea readonly>{{ context_text }}</textarea>
            {% if success %}
                {% for i in range(session['chunks']|length) %}
                <form method="POST" action="/download">
                    <input type="hidden" name="chunk_index" value="{{ i }}">
                    <input type="hidden" name="filename" value="{{ filename }}">
                    <button type="submit" class="download-btn">📥 Download File {{ i + 1 }}</button>
                </form>
                {% endfor %}
            {% endif %}

        {% endif %}
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>Analyzing repository... This may take a moment.</p>
        </div>
    </div>
    
    <script>
        function showLoading() {
            document.getElementById('loading').style.display = 'block';
        }
    </script>
</body>
</html>
'''

def validate_github_url(url):
    match = GITHUB_REPO_REGEX.match(url)
    if not match:
        return None, None
    return match.group(1), match.group(2)

def get_repo_info(user, repo):
    api_url = f"https://api.github.com/repos/{user}/{repo}"
    response = requests.get(api_url)
    if response.status_code == 200:
        return response.json()
    return None

def get_file_content_from_api(user, repo, file_path, branch='main'):
    try:
        api_url = f"https://api.github.com/repos/{user}/{repo}/contents/{file_path}?ref={branch}"
        response = requests.get(api_url)
        if response.status_code == 200:
            file_data = response.json()
            if file_data.get('encoding') == 'base64':
                content = base64.b64decode(file_data['content']).decode('utf-8', errors='ignore')
                return content
    except:
        pass
    return None

def should_include_file(file_path):
    # Files to always exclude
    blacklisted_filenames = {
        'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', 'composer.lock',
        'Pipfile.lock', 'poetry.lock', 'go.sum', 'Cargo.lock',
        '.DS_Store'
    }

    # Directories to skip entirely
    skip_dirs = [
        '.git/', 'node_modules/', '__pycache__/', 'venv/', 'env/',
        'dist/', 'build/', '.next/', '.nuxt/', 'vendor/', 'target/',
        '.idea/', '.vscode/', '.pytest_cache/', '.mypy_cache/', '.coverage/',
        '.github/', 'coverage/', '.husky/', '.circleci/', '.cache/', 'logs/',
    ]

    # Skip binary or irrelevant extensions
    skip_extensions = {
        '.exe', '.dll', '.bin', '.pyc', '.o', '.so',
        '.zip', '.tar', '.gz', '.rar', '.7z',
        '.jpg', '.jpeg', '.png', '.gif', '.ico',
        '.log', '.tmp', '.swp', '.db', '.lock', '.pdf',
        '.min.js', '.min.css', '.map'
    }

    # Normalize path
    file_path_lower = file_path.lower()
    filename = file_path.split('/')[-1].lower()

    if filename in blacklisted_filenames:
        return False
    if any(skip_dir in file_path_lower for skip_dir in skip_dirs):
        return False
    if any(file_path_lower.endswith(ext) for ext in skip_extensions):
        return False

    return True

def get_clean_repo_context(user, repo):
    repo_info = get_repo_info(user, repo)
    if not repo_info:
        return None, "Repository not found or private"

    branch = repo_info.get('default_branch', 'main')
    repo_name = repo_info.get('name', repo)
    description = repo_info.get('description', 'No description available')
    language = repo_info.get('language', 'Unknown')

    api_url = f"https://api.github.com/repos/{user}/{repo}/git/trees/{branch}?recursive=1"
    response = requests.get(api_url)
    if response.status_code != 200:
        return None, "Could not fetch repository structure"

    tree = response.json().get('tree', [])

    readme_files = []
    important_config_files = []
    source_files = []
    image_files = []
    all_files = []

    useful_configs = {
        'package.json', 'tsconfig.json', 'vite.config.js', 'vite.config.ts',
        'tailwind.config.js', 'requirements.txt', 'pyproject.toml', 
        'Cargo.toml', 'go.mod', 'Makefile', 'Dockerfile'
    }

    for item in tree:
        if item['type'] == 'blob':
            path = item['path']
            all_files.append(path)
            filename = path.split('/')[-1].lower()

            if not should_include_file(path):
                if any(path.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp']):
                    image_files.append(path)
                continue

            if any(doc in filename for doc in ['readme', 'changelog', 'license']):
                readme_files.append(path)
            elif filename in useful_configs:
                important_config_files.append(path)
            elif any(filename.endswith(ext) for ext in [
                '.py', '.js', '.ts', '.jsx', '.tsx', '.vue', '.html', '.css', 
                '.java', '.cpp', '.c', '.go', '.rs', '.php', '.rb'
            ]):
                source_files.append(path)

    # Start assembling context content
    context_parts = []
    context_parts.append("=" * 80)
    context_parts.append(f"🚀 CLEAN PROJECT CONTEXT: {repo_name}")
    context_parts.append("=" * 80)
    context_parts.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    context_parts.append(f"Repository: https://github.com/{user}/{repo}")
    context_parts.append(f"Language: {language}")
    context_parts.append(f"Description: {description}\n")

    context_parts.append("📁 FULL FILE STRUCTURE:")
    context_parts += [f" - {f}" for f in all_files]

    if image_files:
        context_parts.append("\n🖼️ IMAGE FILES (Not Included, Just Listed):")
        context_parts += [f" - {f}" for f in image_files]

    # Add README
    if readme_files:
        context_parts.append("\n## 📚 PROJECT DOCUMENTATION")
        for file in readme_files[:3]:
            content = get_file_content_from_api(user, repo, file, branch)
            if content:
                context_parts.append(f"\n--- {file} ---\n{content.strip()}")

    # Config
    if important_config_files:
        context_parts.append("\n## ⚙️ CONFIGURATION FILES")
        for file in important_config_files:
            content = get_file_content_from_api(user, repo, file, branch)
            if content:
                context_parts.append(f"\n--- {file} ---\n{content.strip()}")

    # Source
    if source_files:
        context_parts.append("\n## 💻 SOURCE CODE")
        for file in source_files:
            content = get_file_content_from_api(user, repo, file, branch)
            if content:
                context_parts.append(f"\n--- {file} ---\n{content.strip()}")

    # Attribution
    context_parts.append("\n—" * 40)
    context_parts.append("Generated using Contextify by @Dooafi → https://github.com/Dooa-fi")

    # Final join
    full_context = '\n'.join(context_parts)
    max_chunk_size = 5 * 1024 * 1024  # 5 MB
    chunks = []

    current = ""
    for line in full_context.splitlines(keepends=True):
        if len(current.encode('utf-8')) + len(line.encode('utf-8')) > max_chunk_size:
            chunks.append(current)
            current = ""
        current += line
    if current:
        chunks.append(current)

    return chunks, None


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        github_link = request.form.get('github_link', '').strip()
        
        user, repo = validate_github_url(github_link)
        if not user or not repo:
            return render_template_string(HTML_TEMPLATE, 
                                          error='Please enter a valid GitHub repository URL',
                                          github_link=github_link)
        
        try:
            chunks, error = get_clean_repo_context(user, repo)

            if error:
                return render_template_string(HTML_TEMPLATE, 
                                              error=f'Error: {error}',
                                              github_link=github_link)

            # Save chunks in session
            session['chunks'] = chunks
            session['base_filename'] = repo

            return render_template_string(HTML_TEMPLATE,
                                          success='Context generated successfully!',
                                          context_text='Context has been chunked and saved.',
                                          filename=repo,
                                          github_link=github_link)

        except Exception as e:
            return render_template_string(HTML_TEMPLATE,
                                          error=f'Error generating context: {str(e)}',
                                          github_link=github_link)

    return render_template_string(HTML_TEMPLATE)

@app.route('/download', methods=['POST'])
def download_file():
    index = int(request.form.get('chunk_index', 0))
    filename = request.form.get('filename', 'context')
    from flask import session
    chunks = session.get('chunks', [])
    base = session.get('base_filename', filename)

    if index >= len(chunks):
        return "Invalid chunk", 400

    return Response(
        chunks[index],
        mimetype='text/plain',
        headers={'Content-Disposition': f'attachment; filename={base}_{index+1}.txt'}
    )

# Vercel entry point
# Vercel requires the app to be exported as 'app'
# Do not run app.run()
# Vercel will handle starting the server
