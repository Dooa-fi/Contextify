from flask import Flask, render_template_string, request, Response
import os
import re
import base64
from datetime import datetime
import requests

# Create Flask app
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

GITHUB_REPO_REGEX = re.compile(r'^https://github\.com/([\w\-]+)/([\w\-]+)(/?|\.git)?$')

# Your HTML template (same as before)
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
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
        
        <form method="POST">
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
    </div>
</body>
</html>
'''

# All your helper functions
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

def get_clean_repo_context(user, repo):
    repo_info = get_repo_info(user, repo)
    if not repo_info:
        return None, "Repository not found or private"
    
    branch = repo_info.get('default_branch', 'main')
    repo_name = repo_info.get('name', repo)
    description = repo_info.get('description', 'No description available')
    
    # Simple context for demo
    context = f"""
=== PROJECT CONTEXT: {repo_name} ===
Repository: https://github.com/{user}/{repo}
Description: {description}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This is a simplified context for Vercel deployment.
Full context generation coming soon!
"""
    return context, None

# Flask routes
@app.route('/', methods=['GET', 'POST'])
def index():
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
            
            filename = f'{repo}_context.txt'
            return render_template_string(HTML_TEMPLATE,
                                        success='Context generated successfully!',
                                        context_text=context_text,
                                        filename=filename,
                                        github_link=github_link)
            
        except Exception as e:
            return render_template_string(HTML_TEMPLATE,
                                        error=f'Error: {str(e)}',
                                        github_link=github_link)
    
    return render_template_string(HTML_TEMPLATE)

@app.route('/download', methods=['POST'])
def download():
    context_data = request.form.get('context_data', '')
    filename = request.form.get('filename', 'context.txt')
    
    if not context_data:
        return render_template_string(HTML_TEMPLATE, error='No context data found')
    
    return Response(
        context_data,
        mimetype='text/plain',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )

# CRITICAL: This is what Vercel needs
def handler(event, context):
    return app

# For local testing
if __name__ == '__main__':
    app.run(debug=True)
