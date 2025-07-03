from flask import Flask, render_template_string, request, send_file, flash, redirect, url_for
import os
import requests
from urllib.parse import urlparse
import zipfile
import io
import shutil
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

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
                       required>
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

def download_and_extract_github_repo(github_url, extract_to='temp_repo'):
    """Download and extract GitHub repository"""
    try:
        # Clean up any existing temp directory
        if os.path.exists(extract_to):
            shutil.rmtree(extract_to)
        
        # Parse the URL to get user and repo name
        parsed_url = urlparse(github_url)
        path_parts = parsed_url.path.strip('/').split('/')
        
        if len(path_parts) < 2:
            return None, 'Invalid GitHub URL format'
        
        user, repo = path_parts[0], path_parts[1]
        
        # Try main branch first, then master
        for branch in ['main', 'master']:
            zip_url = f'https://github.com/{user}/{repo}/archive/refs/heads/{branch}.zip'
            response = requests.get(zip_url)
            
            if response.status_code == 200:
                # Extract zip
                with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
                    zip_ref.extractall(extract_to)
                
                # Return extracted folder path
                extracted_folder = os.path.join(extract_to, f'{repo}-{branch}')
                return extracted_folder, None
        
        return None, f'Failed to download repository. Status code: {response.status_code}'
    
    except Exception as e:
        return None, f'Error downloading repository: {str(e)}'

def get_file_content(file_path, max_chars=2000):
    """Get file content with size limit"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(max_chars)
            if len(content) == max_chars:
                content += '\n... (truncated)'
            return content
    except Exception as e:
        return f'Error reading file: {str(e)}'

def create_context_from_repo(repo_path, repo_name):
    """Create comprehensive context from repository"""
    
    context_sections = []
    
    # Header
    context_sections.append("=" * 80)
    context_sections.append(f"PROJECT CONTEXT: {repo_name}")
    context_sections.append("=" * 80)
    context_sections.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    context_sections.append("")
    
    # PROJECT OVERVIEW
    context_sections.append("## PROJECT OVERVIEW")
    context_sections.append("-" * 40)
    
    # Look for README files
    readme_found = False
    for readme_name in ['README.md', 'README.rst', 'README.txt', 'README']:
        readme_path = os.path.join(repo_path, readme_name)
        if os.path.isfile(readme_path):
            readme_content = get_file_content(readme_path, 3000)
            context_sections.append(f"Content from {readme_name}:")
            context_sections.append(readme_content)
            readme_found = True
            break
    
    if not readme_found:
        context_sections.append("No README file found in the repository.")
    
    context_sections.append("")
    
    # TECHNOLOGY STACK
    context_sections.append("## TECHNOLOGY STACK")
    context_sections.append("-" * 40)
    
    tech_files = {
        'requirements.txt': 'Python dependencies',
        'pyproject.toml': 'Python project configuration',
        'package.json': 'Node.js dependencies',
        'Gemfile': 'Ruby dependencies',
        'pom.xml': 'Java Maven dependencies',
        'build.gradle': 'Java Gradle dependencies',
        'Cargo.toml': 'Rust dependencies',
        'go.mod': 'Go module dependencies',
        'composer.json': 'PHP dependencies'
    }
    
    for filename, description in tech_files.items():
        filepath = os.path.join(repo_path, filename)
        if os.path.isfile(filepath):
            content = get_file_content(filepath, 1000)
            context_sections.append(f"{description} ({filename}):")
            context_sections.append(content)
            context_sections.append("")
    
    # PROJECT STRUCTURE
    context_sections.append("## PROJECT STRUCTURE")
    context_sections.append("-" * 40)
    
    structure_lines = []
    for root, dirs, files in os.walk(repo_path):
        # Skip hidden directories and common build/cache directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', 'env']]
        
        level = root.replace(repo_path, '').count(os.sep)
        indent = '  ' * level
        folder_name = os.path.basename(root) if level > 0 else repo_name
        structure_lines.append(f'{indent}{folder_name}/')
        
        # Sort files for consistent output
        files.sort()
        for file in files:
            if not file.startswith('.'):
                structure_lines.append(f'{indent}  {file}')
    
    context_sections.extend(structure_lines)
    context_sections.append("")
    
    # CONFIGURATION FILES
    context_sections.append("## CONFIGURATION FILES")
    context_sections.append("-" * 40)
    
    config_files = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', 'env']]
        
        for file in files:
            if file.endswith(('.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf')):
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, repo_path)
                config_files.append(rel_path)
    
    if config_files:
        context_sections.append("Configuration files found:")
        for config_file in sorted(config_files):
            context_sections.append(f"- {config_file}")
    else:
        context_sections.append("No configuration files found.")
    
    context_sections.append("")
    
    # SOURCE CODE FILES
    context_sections.append("## SOURCE CODE FILES")
    context_sections.append("-" * 40)
    
    # Common source file extensions
    source_extensions = {
        '.py': 'Python',
        '.js': 'JavaScript',
        '.ts': 'TypeScript',
        '.java': 'Java',
        '.cpp': 'C++',
        '.c': 'C',
        '.cs': 'C#',
        '.rb': 'Ruby',
        '.go': 'Go',
        '.rs': 'Rust',
        '.php': 'PHP',
        '.swift': 'Swift',
        '.kt': 'Kotlin',
        '.scala': 'Scala',
        '.r': 'R',
        '.sql': 'SQL',
        '.sh': 'Shell',
        '.bat': 'Batch',
        '.html': 'HTML',
        '.css': 'CSS',
        '.scss': 'SCSS',
        '.sass': 'Sass',
        '.vue': 'Vue',
        '.jsx': 'React JSX',
        '.tsx': 'React TSX'
    }
    
    source_files = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', 'env']]
        
        for file in files:
            file_ext = os.path.splitext(file)[1].lower()
            if file_ext in source_extensions:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, repo_path)
                source_files.append((rel_path, file_ext, file_path))
    
    # Group by file type
    files_by_type = {}
    for rel_path, ext, full_path in source_files:
        lang = source_extensions[ext]
        if lang not in files_by_type:
            files_by_type[lang] = []
        files_by_type[lang].append((rel_path, full_path))
    
    for lang, files in sorted(files_by_type.items()):
        context_sections.append(f"\n{lang} Files:")
        for rel_path, full_path in sorted(files):
            context_sections.append(f"- {rel_path}")
    
    context_sections.append("")
    
    # RAW CODE CONTENT
    context_sections.append("## RAW CODE CONTENT")
    context_sections.append("-" * 40)
    
    # Limit to most important files to avoid huge output
    important_files = []
    for rel_path, ext, full_path in source_files:
        # Prioritize main/index files and smaller files
        if any(keyword in rel_path.lower() for keyword in ['main', 'index', 'app', '__init__']):
            important_files.append((rel_path, full_path))
        elif os.path.getsize(full_path) < 5000:  # Files smaller than 5KB
            important_files.append((rel_path, full_path))
    
    # Limit to first 20 files to avoid overwhelming output
    important_files = important_files[:20]
    
    for rel_path, full_path in important_files:
        context_sections.append(f"\n--- File: {rel_path} ---")
        content = get_file_content(full_path, 1500)
        context_sections.append(content)
    
    context_sections.append("")
    context_sections.append("=" * 80)
    context_sections.append("END OF CONTEXT")
    context_sections.append("=" * 80)
    
    return '\n'.join(context_sections)

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        github_link = request.form.get('github_link', '').strip()
        
        if not github_link:
            flash('Please enter a GitHub repository URL', 'error')
            return redirect(url_for('home'))
        
        # Extract repo name for filename
        try:
            parsed_url = urlparse(github_link)
            repo_name = parsed_url.path.strip('/').split('/')[-1]
        except:
            repo_name = 'repository'
        
        # Download and extract repository
        extracted_path, error = download_and_extract_github_repo(github_link)
        
        if error:
            flash(f'Error: {error}', 'error')
            return redirect(url_for('home'))
        
        # Generate context
        try:
            context_text = create_context_from_repo(extracted_path, repo_name)
            
            # Save context to file
            output_filename = f'{repo_name}_context.txt'
            output_path = os.path.join('outputs', output_filename)
            
            # Create outputs directory if it doesn't exist
            os.makedirs('outputs', exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(context_text)
            
            # Clean up temp files
            if os.path.exists('temp_repo'):
                shutil.rmtree('temp_repo')
            
            flash(f'Context generated successfully! <a href="/download/{output_filename}" class="download-link">Download {output_filename}</a>', 'success')
            
        except Exception as e:
            flash(f'Error generating context: {str(e)}', 'error')
        
        return redirect(url_for('home'))
    
    return render_template_string(HTML_TEMPLATE)

@app.route('/download/<filename>')
def download_file(filename):
    """Download generated context file"""
    try:
        file_path = os.path.join('outputs', filename)
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        flash(f'Error downloading file: {str(e)}', 'error')
        return redirect(url_for('home'))

if __name__ == '__main__':
    # Create outputs directory
    os.makedirs('outputs', exist_ok=True)
    
    print("🚀 Starting Context Extractor...")
    print("📝 Open your browser and go to: http://localhost:5000")
    print("⚡ Ready to extract project contexts!")
    
    app.run(debug=True, port=5000)
