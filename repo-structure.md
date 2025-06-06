# Azure AI Chatbot - Complete Repository Structure

This document outlines the complete file structure for the GitHub repository. Create these files in your repository to have a production-ready AI chatbot.

## Repository Structure

```
azure-ai-chatbot/
├── README.md                        # Main documentation (provided)
├── LICENSE                          # MIT License file
├── .gitignore                       # Git ignore file (provided)
├── azuredeploy.json                # ARM template (provided)
├── deploy.sh                        # Automated deployment script (provided)
├── quickstart.sh                    # Quick start script (provided)
├── setup-github-secrets.sh          # GitHub secrets setup (provided)
│
├── .github/
│   └── workflows/
│       └── deploy.yml              # GitHub Actions CI/CD (provided)
│
├── src/                            # Source code directory
│   ├── function_app.py             # Main function (from your documents)
│   ├── requirements.txt            # Python dependencies
│   ├── host.json                   # Function host configuration
│   ├── local.settings.json.example # Example local settings (provided)
│   │
│   ├── agents/                     # Agent modules
│   │   ├── __init__.py            # Empty file
│   │   ├── basic_agent.py         # Base agent class (from your documents)
│   │   ├── context_memory_agent.py # Memory recall (from your documents)
│   │   ├── manage_memory_agent.py  # Memory storage (from your documents)
│   │   ├── email_drafting_agent.py # Email agent (from your documents)
│   │   ├── analyze_image_agent.py  # Image analysis (from your documents)
│   │   └── learn_new_agent.py      # Dynamic agents (from your documents)
│   │
│   └── utils/                      # Utility modules
│       ├── __init__.py            # Empty file
│       └── azure_file_storage.py   # Storage manager (from your documents)
│
├── tests/                          # Test directory
│   ├── __init__.py
│   ├── test_api.py                # API tests
│   ├── test_agents.py             # Agent tests
│   └── test_memory.py             # Memory system tests
│
├── docs/                          # Documentation
│   ├── API.md                     # API documentation (provided)
│   ├── AGENTS.md                  # Agent development guide
│   ├── MEMORY.md                  # Memory system guide
│   ├── DEPLOYMENT.md              # Deployment guide
│   └── TROUBLESHOOTING.md         # Common issues and solutions
│
├── examples/                      # Example implementations
│   ├── web-client/               # React web interface
│   │   ├── index.html
│   │   ├── app.js
│   │   └── style.css
│   │
│   ├── teams-bot/                # Microsoft Teams integration
│   │   ├── README.md
│   │   └── manifest.json
│   │
│   └── postman/                  # API testing
│       └── AI-Chatbot.postman_collection.json
│
└── scripts/                      # Additional scripts
    ├── backup-memory.sh          # Backup memory data
    └── test-endpoints.sh         # Test all endpoints
```

## File Creation Instructions

### 1. Create Empty Directories

```bash
mkdir -p .github/workflows
mkdir -p src/agents
mkdir -p src/utils
mkdir -p tests
mkdir -p docs
mkdir -p examples/web-client
mkdir -p examples/teams-bot
mkdir -p examples/postman
mkdir -p scripts
```

### 2. Create Empty __init__.py Files

```bash
touch src/agents/__init__.py
touch src/utils/__init__.py
touch tests/__init__.py
```

### 3. Create requirements.txt

Create `src/requirements.txt`:

```txt
azure-functions==1.18.0
azure-storage-file==2.1.0
openai==1.12.0
requests==2.31.0
```

### 4. Create host.json

Create `src/host.json`:

```json
{
  "version": "2.0",
  "logging": {
    "applicationInsights": {
      "samplingSettings": {
        "isEnabled": true,
        "excludedTypes": "Request"
      }
    }
  },
  "extensionBundle": {
    "id": "Microsoft.Azure.Functions.ExtensionBundle",
    "version": "[4.*, 5.0.0)"
  },
  "functionTimeout": "00:10:00"
}
```

### 5. Create LICENSE

Create `LICENSE` (MIT License):

```
MIT License

Copyright (c) 2024 [Your Name]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### 6. Copy Python Files

Copy all the Python files from your documents into the appropriate directories:
- `function_app.py` → `src/function_app.py`
- `basic_agent.py` → `src/agents/basic_agent.py`
- All other agent files → `src/agents/`
- `azure_file_storage.py` → `src/utils/azure_file_storage.py`

### 7. Make Scripts Executable

```bash
chmod +x deploy.sh
chmod +x quickstart.sh
chmod +x setup-github-secrets.sh
```

## Quick Deployment Steps

1. **Fork/Clone the repository**
   ```bash
   git clone https://github.com/kody-w/azure-ai-chatbot.git
   cd azure-ai-chatbot
   ```

2. **Run the quick start script**
   ```bash
   ./quickstart.sh
   ```

3. **Follow the prompts** to deploy your chatbot

## Repository Best Practices

1. **Never commit sensitive data**
   - Use `.gitignore` to exclude local.settings.json
   - Store secrets in GitHub Secrets or Azure Key Vault

2. **Keep documentation updated**
   - Update README when adding features
   - Document all agents in AGENTS.md

3. **Use semantic versioning**
   - Tag releases with version numbers
   - Update CHANGELOG.md for each release

4. **Test before deploying**
   - Run tests locally before pushing
   - Use GitHub Actions for automated testing

5. **Monitor issues and PRs**
   - Respond to issues promptly
   - Review and merge PRs regularly

## Setting Up GitHub

1. **Create a new repository**
   - Go to GitHub.com
   - Click "New repository"
   - Name it "azure-ai-chatbot"
   - Make it public

2. **Push your code**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/kody-w/azure-ai-chatbot.git
   git push -u origin main
   ```

3. **Set up GitHub Secrets**
   ```bash
   ./setup-github-secrets.sh
   ```

4. **Enable GitHub Actions**
   - Actions should be enabled by default
   - Check the Actions tab after pushing

## Customization Points

1. **Assistant Configuration**
   - Edit `ASSISTANT_NAME` and `CHARACTERISTIC_DESCRIPTION` in ARM template
   - Modify system prompt in `function_app.py`

2. **Add Custom Agents**
   - Create new files in `src/agents/`
   - Follow the agent template pattern

3. **Modify Memory System**
   - Update `azure_file_storage.py` for different storage patterns
   - Customize memory retention policies

4. **Integration Options**
   - Use examples as starting points
   - Integrate with your existing systems

## Support Resources

- **Documentation**: Check the `docs/` folder
- **Examples**: See `examples/` for integration patterns
- **Issues**: Use GitHub Issues for bugs/features
- **Discussions**: Use GitHub Discussions for questions

Remember to star the repository if you find it useful!