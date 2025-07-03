import os
import re
import requests
from datetime import datetime
from flask import Flask, render_template_string, request, send_file, flash, redirect, url_for
from markupsafe import Markup
import base64

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
        .download-link {
            display: inline-block;
            margin-top: 10px;
            padding: 10px 20px;
            background-color: #28a745;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 500;
        }
        .download-link:hover {
            background-color: #218838;
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
    </style>
</head>
<body>
    <div class="container">
        <h1>Context for your Code</h1>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">
                        {{ message|safe }}
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
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
    """Smart filtering - include ALL relevant files but exclude junk"""
    
    # Skip these directories completely
    skip_dirs = [
        '.git/', 'node_modules/', '__pycache__/', '.pytest_cache/', 
        'venv/', 'env/', '.venv/', '.env/', 'dist/', 'build/', 
        '.next/', '.nuxt/', 'vendor/', 'target/', 'bin/', 'obj/',
        '.idea/', '.vscode/', '.DS_Store'
    ]
    
    # Skip these file types
    skip_extensions = [
        '.pyc', '.pyo', '.pyd', '.so', '.dll', '.exe', '.bin', '.obj',
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.svg', '.webp',
        '.mp4', '.mp3', '.wav', '.avi', '.mov', '.wmv', '.flv',
        '.zip', '.tar', '.gz', '.rar', '.7z', '.bz2',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.lock', '.log', '.tmp', '.temp', '.cache'
    ]
    
    # Check directory exclusions
    if any(skip_dir in file_path for skip_dir in skip_dirs):
        return False
    
    # Check file extension exclusions
    if any(file_path.lower().endswith(ext) for ext in skip_extensions):
        return False
    
    return True

def get_all_repo_files(user, repo):
    """Get ALL relevant files from repository - comprehensive approach"""
    
    # Get repo info
    repo_info = get_repo_info(user, repo)
    if not repo_info:
        return None, "Repository not found or private"
    
    branch = repo_info.get('default_branch', 'main')
    repo_name = repo_info.get('name', repo)
    description = repo_info.get('description', 'No description available')
    language = repo_info.get('language', 'Unknown')
    
    # Get complete file tree
    api_url = f"https://api.github.com/repos/{user}/{repo}/git/trees/{branch}?recursive=1"
    response = requests.get(api_url)
    if response.status_code != 200:
        return None, "Could not fetch repository structure"
    
    tree = response.json().get('tree', [])
    
    # Categorize ALL files
    documentation_files = []
    config_files = []
    source_files = []
    
    for item in tree:
        if item['type'] == 'blob' and should_include_file(item['path']):
            file_path = item['path']
            filename = file_path.split('/')[-1].lower()
            
            # Documentation files
            if any(doc in filename for doc in ['readme', 'changelog', 'license', 'contributing', 'authors', 'todo']):
                documentation_files.append(file_path)
            
            # Configuration files
            elif any(filename.endswith(ext) for ext in ['.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf', '.env.example']):
                config_files.append(file_path)
            
            # Source files - ALL OF THEM
            elif any(filename.endswith(ext) for ext in [
                '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h', '.hpp',
                '.cs', '.rb', '.go', '.rs', '.php', '.swift', '.kt', '.scala', '.r',
                '.sql', '.sh', '.bat', '.ps1', '.html', '.css', '.scss', '.sass',
                '.vue', '.svelte', '.dart', '.lua', '.perl', '.clj', '.elm', '.haskell',
                '.ml', '.fs', '.vb', '.asm', '.dockerfile', '.makefile', '.gradle',
                '.xml', '.xsl', '.xsd'
            ]):
                source_files.append(file_path)
    
    # Build comprehensive context
    context_sections = []
    context_sections.append("=" * 100)
    context_sections.append(f"COMPLETE PROJECT CONTEXT: {repo_name}")
    context_sections.append("=" * 100)
    context_sections.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    context_sections.append(f"Repository: https://github.com/{user}/{repo}")
    context_sections.append(f"Primary Language: {language}")
    context_sections.append(f"Description: {description}")
    context_sections.append(f"Total Files Processed: {len(documentation_files + config_files + source_files)}")
    context_sections.append("")
    
    # DOCUMENTATION SECTION
    if documentation_files:
        context_sections.append("## 📚 DOCUMENTATION FILES")
        context_sections.append("=" * 50)
        for file_path in documentation_files:
            content = get_file_content_from_api(user, repo, file_path, branch)
            if content:
                context_sections.append(f"\n--- {file_path} ---")
                context_sections.append(content)
                context_sections.append("")
    
    # CONFIGURATION SECTION
    if config_files:
        context_sections.append("## ⚙️ CONFIGURATION FILES")
        context_sections.append("=" * 50)
        for file_path in config_files:
            content = get_file_content_from_api(user, repo, file_path, branch)
            if content:
                context_sections.append(f"\n--- {file_path} ---")
                context_sections.append(content)
                context_sections.append("")
    
    # SOURCE CODE SECTION - ALL FILES
    if source_files:
        context_sections.append("## 💻 SOURCE CODE FILES")
        context_sections.append("=" * 50)
        
        # Group by file type for better organization
        files_by_extension = {}
        for file_path in source_files:
            ext = '.' + file_path.split('.')[-1] if '.' in file_path else 'no_ext'
            files_by_extension.setdefault(ext, []).append(file_path)
        
        for ext, files in sorted(files_by_extension.items()):
            context_sections.append(f"\n### {ext.upper()} FILES")
            context_sections.append("-" * 30)
            
            for file_path in files:
                content = get_file_content_from_api(user, repo, file_path, branch)
                if content:
                    context_sections.append(f"\n--- {file_path} ---")
                    # Limit very large files
                    if len(content) > 10000:
                        context_sections.append(content[:10000] + "\n... (truncated - file too large)")
                    else:
                        context_sections.append(content)
                    context_sections.append("")
    
    context_sections.append("=" * 100)
    context_sections.append("END OF COMPLETE CONTEXT")
    context_sections.append("=" * 100)
    
    return '\n'.join(context_sections), None

@app.route('/', methods=['GET', 'POST'])
def home():
    github_link = ''
    if request.method == 'POST':
        github_link = request.form.get('github_link', '').strip()
        
        user, repo = validate_github_url(github_link)
        if not user or not repo:
            flash('Please enter a valid GitHub repository URL', 'error')
            return render_template_string(HTML_TEMPLATE, github_link=github_link)
        
        try:
            context_text, error = get_all_repo_files(user, repo)
            
            if error:
                flash(f'Error: {error}', 'error')
                return render_template_string(HTML_TEMPLATE, github_link=github_link)
            
            # Save context to file
            os.makedirs('outputs', exist_ok=True)
            output_filename = f'{repo}_complete_context.txt'
            output_path = os.path.join('outputs', output_filename)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(context_text)
            
            flash(Markup(f'Complete context generated! <a href="/download/{output_filename}" class="download-link">Download {output_filename}</a>'), 'success')
            
        except Exception as e:
            flash(f'Error generating context: {str(e)}', 'error')
        
        return render_template_string(HTML_TEMPLATE, github_link=github_link)
    
    return render_template_string(HTML_TEMPLATE)

@app.route('/download/<filename>')
def download_file(filename):
    try:
        file_path = os.path.join('outputs', filename)
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        flash(f'Error downloading file: {str(e)}', 'error')
        return redirect(url_for('home'))

if __name__ == '__main__':
    os.makedirs('outputs', exist_ok=True)
    print("🚀 Starting Complete Context Extractor...")
    print("📝 Open your browser and go to: http://localhost:5000")
    print("⚡ Ready to extract COMPLETE project contexts!")
    app.run(debug=True, port=5000)
