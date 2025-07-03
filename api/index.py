import os
import re
import io
import base64
from datetime import datetime
import requests
from flask import Flask, render_template_string, request, Response
from markupsafe import Markup

app = Flask(__name__)
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
            <form method="POST" action="/download">
                <input type="hidden" name="context_data" value="{{ context_text }}">
                <input type="hidden" name="filename" value="{{ filename }}">
                <button type="submit" class="download-btn">📥 Download Context File</button>
            </form>
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
    
    useful_configs = {
        'package.json', 'tsconfig.json', 'vite.config.js', 'vite.config.ts',
        'tailwind.config.js', 'requirements.txt', 'pyproject.toml', 
        'Cargo.toml', 'go.mod', 'Makefile', 'Dockerfile'
    }
    
    for item in tree:
        if item['type'] == 'blob' and should_include_file(item['path']):
            file_path = item['path']
            filename = file_path.split('/')[-1].lower()
            
            if any(doc in filename for doc in ['readme', 'changelog', 'license']):
                readme_files.append(file_path)
            elif file_path.split('/')[-1] in useful_configs:
                important_config_files.append(file_path)
            elif any(filename.endswith(ext) for ext in [
                '.py', '.js', '.ts', '.jsx', '.tsx', '.vue', '.html', '.css', 
                '.java', '.cpp', '.c', '.go', '.rs', '.php', '.rb'
            ]):
                source_files.append(file_path)
    
    context_sections = []
    context_sections.append("=" * 80)
    context_sections.append(f"🚀 CLEAN PROJECT CONTEXT: {repo_name}")
    context_sections.append("=" * 80)
    context_sections.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    context_sections.append(f"Repository: https://github.com/{user}/{repo}")
    context_sections.append(f"Language: {language}")
    context_sections.append(f"Description: {description}")
    context_sections.append("")
    
    # README & DOCUMENTATION
    if readme_files:
        context_sections.append("## 📚 PROJECT DOCUMENTATION")
        context_sections.append("=" * 50)
        for file_path in readme_files[:3]:  # Limit to 3 files
            content = get_file_content_from_api(user, repo, file_path, branch)
            if content:
                context_sections.append(f"\n--- {file_path} ---")
                context_sections.append(content[:7000])
                if len(content) > 5000:
                    context_sections.append("\n... (truncated)")
                context_sections.append("")
    
    # CONFIGURATION
    if important_config_files:
        context_sections.append("## ⚙️ PROJECT CONFIGURATION")
        context_sections.append("=" * 50)
        for file_path in important_config_files[:5]:  # Limit to 5 files
            content = get_file_content_from_api(user, repo, file_path, branch)
            if content:
                context_sections.append(f"\n--- {file_path} ---")
                context_sections.append(content[:3000])
                if len(content) > 2000:
                    context_sections.append("\n... (truncated)")
                context_sections.append("")
    
    # SOURCE CODE
    if source_files:
        context_sections.append("## 💻 SOURCE CODE")
        context_sections.append("=" * 50)
        
        files_by_type = {}
        for file_path in source_files:
            ext = '.' + file_path.split('.')[-1] if '.' in file_path else 'no_ext'
            files_by_type.setdefault(ext, []).append(file_path)
        
        for ext, files in sorted(files_by_type.items()):
            if files:
                context_sections.append(f"\n### {ext.upper()} FILES")
                context_sections.append("-" * 30)
                
                for file_path in files[:20]:  # Max 8 files per type
                    content = get_file_content_from_api(user, repo, file_path, branch)
                    if content:
                        context_sections.append(f"\n--- {file_path} ---")
                        if len(content) > 3000:
                            context_sections.append(content[:7000] + "\n... (truncated)")
                        else:
                            context_sections.append(content)
                        context_sections.append("")
    
    context_sections.append("=" * 80)
    context_sections.append("🎯 END OF CLEAN CONTEXT")
    context_sections.append("=" * 80)
    
    return '\n'.join(context_sections), None

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
            context_text, error = get_clean_repo_context(user, repo)
            
            if error:
                return render_template_string(HTML_TEMPLATE, 
                                            error=f'Error: {error}',
                                            github_link=github_link)
            
            filename = f'{repo}_clean_context.txt'
            return render_template_string(HTML_TEMPLATE,
                                        success='Context generated successfully!',
                                        context_text=context_text,
                                        filename=filename,
                                        github_link=github_link)
            
        except Exception as e:
            return render_template_string(HTML_TEMPLATE,
                                        error=f'Error generating context: {str(e)}',
                                        github_link=github_link)
    
    return render_template_string(HTML_TEMPLATE)

@app.route('/download', methods=['POST'])
def download_file():
    context_data = request.form.get('context_data', '')
    filename = request.form.get('filename', 'context.txt')
    
    if not context_data:
        return render_template_string(HTML_TEMPLATE, error='No context data found')
    
    return Response(
        context_data,
        mimetype='text/plain',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )

# Vercel entry point
# Vercel requires the app to be exported as 'app'
# Do not run app.run()
# Vercel will handle starting the server
