# Azure AI Chatbot with Memory System

A production-ready AI chatbot built on Azure Functions with GPT-4, featuring persistent memory storage, multiple specialized agents, and easy deployment.

## 🚀 Features

- **GPT-4 Powered**: Uses Azure OpenAI Service with GPT-4 for intelligent conversations
- **Memory System**: Persistent memory storage with user-specific and shared memory capabilities
- **Modular Agent System**: Extensible architecture with specialized agents:
  - Context Memory Agent - Recalls past conversations
  - Manage Memory Agent - Stores important information
  - Email Drafting Agent - Composes and sends emails
  - Image Analysis Agent - Analyzes images using Vision AI
  - Learn New Agent - Dynamically creates new agents
- **Azure Native**: Built on Azure Functions for scalability and reliability
- **CORS Support**: Ready for web application integration
- **Monitoring**: Integrated Application Insights for debugging and analytics

## 📋 Prerequisites

- Azure subscription with access to Azure OpenAI Service
- Azure CLI installed ([Download](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli))
- Python 3.11 or higher (for local development)

## 🛠️ Quick Deploy

### Option 1: One-Click Deploy to Azure

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2F[YOUR-USERNAME]%2F[YOUR-REPO]%2Fmain%2Fazuredeploy.json)

### Option 2: Deploy via Azure CLI

1. Clone this repository:
```bash
git clone https://github.com/[YOUR-USERNAME]/azure-ai-chatbot.git
cd azure-ai-chatbot
```

2. Login to Azure:
```bash
az login
```

3. Run the deployment script:
```bash
./deploy.sh
```

The script will prompt you for:
- Resource group name (creates new if doesn't exist)
- Project name (3-11 characters, e.g., "mybot")
- Azure region (e.g., "eastus")
- OpenAI region (e.g., "eastus")

### Option 3: Manual Deployment

1. Deploy the ARM template:
```bash
az group create --name myResourceGroup --location eastus

az deployment group create \
  --resource-group myResourceGroup \
  --template-file azuredeploy.json \
  --parameters projectName="mybot"
```

2. Deploy the function code:
```bash
cd src
func azure functionapp publish <function-app-name> --python
```

## 📁 Repository Structure

```
azure-ai-chatbot/
├── README.md                 # This file
├── LICENSE                   # MIT License
├── azuredeploy.json         # ARM template for infrastructure
├── deploy.sh                # Automated deployment script
├── .github/
│   └── workflows/
│       └── deploy.yml       # GitHub Actions CI/CD
├── src/
│   ├── function_app.py      # Main function entry point
│   ├── requirements.txt     # Python dependencies
│   ├── host.json           # Function host configuration
│   ├── local.settings.json.example  # Local development settings
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── basic_agent.py
│   │   ├── context_memory_agent.py
│   │   ├── manage_memory_agent.py
│   │   ├── email_drafting_agent.py
│   │   ├── analyze_image_agent.py
│   │   └── learn_new_agent.py
│   └── utils/
│       ├── __init__.py
│       └── azure_file_storage.py
├── tests/                   # Test files
│   ├── test_api.py
│   └── test_agents.py
├── docs/                    # Additional documentation
│   ├── API.md              # API documentation
│   ├── AGENTS.md           # Agent development guide
│   └── MEMORY.md           # Memory system guide
└── examples/               # Example implementations
    ├── web-client/         # Sample web interface
    ├── teams-bot/          # Teams integration example
    └── postman/            # Postman collection
```

## 🔧 Configuration

### Environment Variables

The following environment variables are automatically configured by the ARM template:

| Variable | Description |
|----------|-------------|
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_VERSION` | API version (default: 2024-02-15-preview) |
| `ASSISTANT_NAME` | Your assistant's name |
| `CHARACTERISTIC_DESCRIPTION` | Assistant personality description |
| `AZURE_FILES_SHARE_NAME` | Azure Files share for memory storage |

### Local Development

1. Copy the example settings:
```bash
cp src/local.settings.json.example src/local.settings.json
```

2. Fill in your Azure credentials in `local.settings.json`

3. Run locally:
```bash
cd src
func start
```

## 📡 API Usage

### Basic Chat Request

```bash
curl -X POST "https://<your-function-app>.azurewebsites.net/api/businessinsightbot_function?code=<your-function-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "Hello, how are you?",
    "conversation_history": []
  }'
```

### With User-Specific Memory

```bash
curl -X POST "https://<your-function-app>.azurewebsites.net/api/businessinsightbot_function?code=<your-function-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "Remember that my favorite color is blue",
    "user_guid": "12345678-1234-1234-1234-123456789012",
    "conversation_history": []
  }'
```

### Response Format

```json
{
  "assistant_response": "I'll remember that your favorite color is blue!",
  "agent_logs": "Performed ManageMemory and got result: Successfully stored preference memory...",
  "user_guid": "12345678-1234-1234-1234-123456789012"
}
```

## 🧠 Memory System

The chatbot uses a dual-memory system:

1. **Shared Memory**: Accessible by all users (general knowledge)
2. **User-Specific Memory**: Private to each user (identified by GUID)

Default GUID: `c0p110t0-aaaa-bbbb-cccc-123456789abc`

See [docs/MEMORY.md](docs/MEMORY.md) for detailed information.

## 🤖 Creating Custom Agents

To create a new agent:

1. Create a new file in `src/agents/`
2. Extend the `BasicAgent` class
3. Implement the `perform` method

Example:
```python
from agents.basic_agent import BasicAgent

class WeatherAgent(BasicAgent):
    def __init__(self):
        self.name = "Weather"
        self.metadata = {
            "name": self.name,
            "description": "Gets weather information for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name or coordinates"
                    }
                },
                "required": ["location"]
            }
        }
        super().__init__(name=self.name, metadata=self.metadata)
    
    def perform(self, **kwargs):
        location = kwargs.get('location')
        # Your implementation here
        return f"Weather information for {location}"
```

See [docs/AGENTS.md](docs/AGENTS.md) for the complete guide.

## 📊 Monitoring

View your chatbot's performance and logs:

1. **Application Insights**: 
   - Go to Azure Portal → Your Resource Group → Application Insights
   - View real-time metrics, logs, and failures

2. **Function Logs**:
   ```bash
   az functionapp log tail --resource-group <rg-name> --name <function-name>
   ```

## 💰 Cost Estimation

Typical monthly costs:
- **Function App (Consumption)**: $0-20 based on usage
- **Storage**: $2-5
- **Azure OpenAI**: ~$0.03 per 1K tokens
- **Application Insights**: $0-5

## 🔒 Security Considerations

- Function uses key-based authentication
- All traffic is HTTPS-only
- Secrets stored in Azure Key Vault (optional upgrade)
- Configure CORS for your specific domains

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with Azure Functions and Azure OpenAI Service
- Inspired by Microsoft Copilot architecture
- Community contributions welcome!

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/[YOUR-USERNAME]/azure-ai-chatbot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/[YOUR-USERNAME]/azure-ai-chatbot/discussions)
- **Documentation**: [Full Docs](docs/)

---

**⭐ If you find this project useful, please consider giving it a star!**