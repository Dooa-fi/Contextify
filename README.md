# Project Context Extractor

**Transform any GitHub repository into AI-ready project context in seconds!**

A powerful Flask web application that automatically extracts comprehensive project information from GitHub repositories and generates structured context files—perfect for AI coding assistants like ChatGPT, Claude, and Gemini.

---

## 🚀 What It Does

Ever struggled to give your AI coding assistant enough context about your project? This tool solves that problem by:

- **Automatically downloading** any public GitHub repository  
- **Analyzing the project structure** and extracting key insights  
- **Generating comprehensive context files** with project overview, tech stack, file structure, and actual code  
- **Creating AI-ready output** in structured text format for maximum compatibility  

---

## 🔑 Key Features

### ✅ One-Click Context Generation
- Simple web interface with a GitHub URL input
- Auto-download and unpack public repositories
- Instant structured context file generation

### 📊 Comprehensive Project Analysis
- **Project Overview** – Includes README content and high-level summary
- **Tech Stack Detection** – Extracted from `requirements.txt`, `package.json`, and others
- **Project Structure** – Full directory tree of the codebase
- **Configuration Files** – Listed and extracted
- **Source Code** – Organized by language with snippets
- **Raw Code Content** – Important code files with inline paths

### 💻 Beautiful Web Interface
- Responsive, clean UI with gradients
- Works smoothly on all devices
- Real-time loading and error messages
- Direct download button for output

### 🧠 Smart Processing
- Detects over 20 programming languages
- Skips build/cache dirs like `node_modules`, `.git`, `__pycache__`
- File size caps to ensure readable context
- Graceful handling of errors and bad inputs

---

## ⚡ Quick Start

### 🧰 Prerequisites
- Python 3.8+
- pip (Python package installer)

### 🔧 Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-username/context-extractor.git
cd context-extractor

# 2. Install dependencies
pip install flask requests

# 3. Save the application code as app.py
# (Use the complete app.py provided)

# 4. Run the server
python app.py

🌐 Open Your Browser
Go to http://localhost:5000, paste a GitHub URL, click “🚀 Generate Context”, and download your .txt file!

📁 Generated Context Structure
pgsql
Copy
Edit
================================================================================
PROJECT CONTEXT: [Repository Name]
Generated on: [YYYY-MM-DD HH:MM:SS]

PROJECT OVERVIEW
[README content and project description]

TECHNOLOGY STACK
[List of dependencies]

PROJECT STRUCTURE
[Tree of folders/files]

CONFIGURATION FILES
[List of config files found]

SOURCE CODE FILES
[Categorized by programming language]

RAW CODE CONTENT
[Key code snippets with file paths]
================================================================================
💡 Usage Examples
Basic Workflow
Visit http://localhost:5000

Paste a GitHub URL (e.g., https://github.com/psf/requests)

Click "🚀 Generate Context"

Download the [repo-name]_context.txt file

Paste it into your AI assistant

Works With:
Python (Django, Flask, FastAPI)

JavaScript (React, Express, Vue)

Java (Spring, Maven, Gradle)

Go, Rust, PHP, Ruby, etc.

⚙️ Technical Details
Built With:
Flask – Web server framework

Requests – For GitHub downloads

Standard Python Libraries – For ZIP extraction, path handling, and encoding detection

Architecture
Web UI – Clean HTML/CSS + Flask backend

Repo Downloader – Downloads and extracts ZIPs

Analyzer – Parses structure, dependencies, code

File Generator – Outputs .txt file with structured project context

Supported Languages
Python, JavaScript, TypeScript, Java, C/C++, C#

Go, Rust, PHP, Ruby, Swift, Kotlin, Scala

HTML, CSS, SQL, Shell scripts, and more

🧠 Smart File Detection & Filtering
Recognizes project type automatically

Detects key configuration files: requirements.txt, package.json, pom.xml, etc.

Focuses on files like main.py, index.js, App.java, etc.

Filters out cache, hidden, and binary files

Truncates large code files to 1,500 chars for readability

🧪 Customization Options
Section	Character Limit	Max Files
Code Snippets	1,500 characters	20 files
README	3,000 characters	1 file
Config Files	1,000 characters	—

Output saved in /outputs/, auto-named as [repo-name]_context.txt

🎯 Ideal For
Learning New Codebases – Instantly understand any repo

AI Code Reviews – Get feedback with complete project info

AI-Powered Documentation – Auto-generate technical docs

Debugging – Let AI assist with full context

Code Refactoring – AI helps rewrite with full awareness

📄 License
Licensed under the MIT License. Feel free to use, modify, and share!

