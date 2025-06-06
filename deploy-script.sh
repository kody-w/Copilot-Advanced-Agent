#!/bin/bash

# Azure AI Chatbot - Automated Deployment Script
# This script handles the complete deployment process

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ASCII Art Banner
echo -e "${BLUE}"
cat << "EOF"
    _                          _    ___    ____ _           _   _           _   
   / \    _____   _ _ __ ___  / \  |_ _|  / ___| |__   __ _| |_| |__   ___ | |_ 
  / _ \  |_  / | | | '__/ _ \/ _ \  | |  | |   | '_ \ / _` | __| '_ \ / _ \| __|
 / ___ \  / /| |_| | | |  __/ ___ \ | |  | |___| | | | (_| | |_| |_) | (_) | |_ 
/_/   \_\/___|\__,_|_|  \___/_/   \_\___|  \____|_| |_|\__,_|\__|_.__/ \___/ \__|
                                                                                  
EOF
echo -e "${NC}"
echo -e "${GREEN}Automated Deployment Script v1.0${NC}"
echo "=================================="
echo ""

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -g, --resource-group    Resource group name (will create if doesn't exist)"
    echo "  -n, --name             Project name (3-11 characters, default: generates unique)"
    echo "  -l, --location         Azure region (default: eastus)"
    echo "  -o, --openai-location  OpenAI region (default: eastus)"
    echo "  -s, --subscription     Azure subscription ID (optional)"
    echo "  -y, --yes              Skip confirmation prompts"
    echo "  -h, --help             Display this help message"
    echo ""
    echo "Example:"
    echo "  $0 --resource-group myRG --name mybot --location eastus"
    exit 1
}

# Function to generate random name
generate_name() {
    echo "bot$(date +%s | tail -c 6)"
}

# Function to check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"
    
    # Check Azure CLI
    if ! command -v az &> /dev/null; then
        echo -e "${RED}Error: Azure CLI is not installed${NC}"
        echo "Please install from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        exit 1
    fi
    
    # Check if logged in to Azure
    if ! az account show &> /dev/null; then
        echo -e "${YELLOW}Not logged in to Azure. Logging in...${NC}"
        az login
    fi
    
    # Check if zip is installed
    if ! command -v zip &> /dev/null; then
        echo -e "${RED}Error: zip command is not installed${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ All prerequisites met${NC}"
}

# Function to validate parameters
validate_parameters() {
    # Validate project name length
    if [ ! -z "$PROJECT_NAME" ]; then
        if [ ${#PROJECT_NAME} -lt 3 ] || [ ${#PROJECT_NAME} -gt 11 ]; then
            echo -e "${RED}Error: Project name must be 3-11 characters long${NC}"
            exit 1
        fi
        
        # Check if project name is alphanumeric
        if ! [[ "$PROJECT_NAME" =~ ^[a-zA-Z0-9]+$ ]]; then
            echo -e "${RED}Error: Project name must be alphanumeric only${NC}"
            exit 1
        fi
    fi
}

# Parse command line arguments
RESOURCE_GROUP=""
PROJECT_NAME=""
LOCATION="eastus"
OPENAI_LOCATION="eastus"
SUBSCRIPTION=""
SKIP_CONFIRM=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -g|--resource-group)
            RESOURCE_GROUP="$2"
            shift 2
            ;;
        -n|--name)
            PROJECT_NAME="$2"
            shift 2
            ;;
        -l|--location)
            LOCATION="$2"
            shift 2
            ;;
        -o|--openai-location)
            OPENAI_LOCATION="$2"
            shift 2
            ;;
        -s|--subscription)
            SUBSCRIPTION="$2"
            shift 2
            ;;
        -y|--yes)
            SKIP_CONFIRM=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            ;;
    esac
done

# Check prerequisites
check_prerequisites

# Interactive mode if parameters not provided
if [ -z "$RESOURCE_GROUP" ]; then
    read -p "Enter resource group name: " RESOURCE_GROUP
fi

if [ -z "$PROJECT_NAME" ]; then
    DEFAULT_NAME=$(generate_name)
    read -p "Enter project name (3-11 chars) [$DEFAULT_NAME]: " PROJECT_NAME
    PROJECT_NAME=${PROJECT_NAME:-$DEFAULT_NAME}
fi

# Validate parameters
validate_parameters

# Set subscription if provided
if [ ! -z "$SUBSCRIPTION" ]; then
    echo -e "${YELLOW}Setting subscription to: $SUBSCRIPTION${NC}"
    az account set --subscription "$SUBSCRIPTION"
fi

# Get current subscription info
CURRENT_SUB=$(az account show --query name -o tsv)
CURRENT_SUB_ID=$(az account show --query id -o tsv)

# Display deployment summary
echo ""
echo -e "${BLUE}Deployment Summary:${NC}"
echo "==================="
echo "Subscription:      $CURRENT_SUB"
echo "Resource Group:    $RESOURCE_GROUP"
echo "Project Name:      $PROJECT_NAME"
echo "Location:          $LOCATION"
echo "OpenAI Location:   $OPENAI_LOCATION"
echo ""

# Confirm deployment
if [ "$SKIP_CONFIRM" = false ]; then
    read -p "Do you want to proceed with deployment? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Deployment cancelled${NC}"
        exit 0
    fi
fi

# Create resource group if it doesn't exist
echo -e "${YELLOW}Checking resource group...${NC}"
if ! az group show --name "$RESOURCE_GROUP" &> /dev/null; then
    echo -e "${YELLOW}Creating resource group: $RESOURCE_GROUP${NC}"
    az group create --name "$RESOURCE_GROUP" --location "$LOCATION"
else
    echo -e "${GREEN}✓ Resource group exists${NC}"
fi

# Deploy ARM template
echo ""
echo -e "${YELLOW}Deploying infrastructure...${NC}"
echo "This may take 5-10 minutes..."

DEPLOYMENT_NAME="deployment-$(date +%s)"
DEPLOYMENT_OUTPUT=$(az deployment group create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$DEPLOYMENT_NAME" \
    --template-file azuredeploy.json \
    --parameters \
        projectName="$PROJECT_NAME" \
        location="$LOCATION" \
        openAILocation="$OPENAI_LOCATION" \
    --output json)

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: ARM template deployment failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Infrastructure deployed successfully${NC}"

# Extract outputs
FUNCTION_APP_NAME=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.properties.outputs.functionAppName.value')
FUNCTION_URL=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.properties.outputs.functionUrl.value')
STORAGE_ACCOUNT=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.properties.outputs.storageAccountName.value')
FILE_SHARE=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.properties.outputs.fileShareName.value')

# Display infrastructure info
echo ""
echo -e "${BLUE}Infrastructure Created:${NC}"
echo "======================"
echo "Function App:      $FUNCTION_APP_NAME"
echo "Storage Account:   $STORAGE_ACCOUNT"
echo "File Share:       $FILE_SHARE"

# Package and deploy function code
echo ""
echo -e "${YELLOW}Packaging function code...${NC}"

# Create temporary directory
TEMP_DIR=$(mktemp -d)
PACKAGE_DIR="$TEMP_DIR/package"

# Copy source files
cp -r src/* "$PACKAGE_DIR/" 2>/dev/null || {
    echo -e "${RED}Error: src/ directory not found${NC}"
    echo "Make sure you're running this script from the repository root"
    exit 1
}

# Create deployment package
cd "$PACKAGE_DIR"
zip -r "$TEMP_DIR/deployment.zip" . -q

# Deploy to Function App
echo -e "${YELLOW}Deploying function code...${NC}"
az functionapp deployment source config-zip \
    --resource-group "$RESOURCE_GROUP" \
    --name "$FUNCTION_APP_NAME" \
    --src "$TEMP_DIR/deployment.zip" \
    --output none

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Function code deployment failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Function code deployed successfully${NC}"

# Wait for function to be ready
echo -e "${YELLOW}Waiting for function to initialize...${NC}"
sleep 30

# Get function key
echo -e "${YELLOW}Retrieving function key...${NC}"
FUNCTION_KEY=$(az functionapp function keys list \
    --resource-group "$RESOURCE_GROUP" \
    --name "$FUNCTION_APP_NAME" \
    --function-name "businessinsightbot_function" \
    --query "default" -o tsv 2>/dev/null)

# Clean up
rm -rf "$TEMP_DIR"

# Display success message
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║               🎉 Deployment Successful! 🎉                   ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Your AI Chatbot is ready!${NC}"
echo ""
echo -e "${YELLOW}Function URL:${NC}"
echo "$FUNCTION_URL"
echo ""
echo -e "${YELLOW}Function Key:${NC}"
echo "${FUNCTION_KEY:-'(Retrieving key... check Azure Portal if not shown)'}"
echo ""
echo -e "${BLUE}Test your chatbot:${NC}"
echo "curl -X POST \"$FUNCTION_URL?code=$FUNCTION_KEY\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"user_input\": \"Hello!\", \"conversation_history\": []}'"
echo ""
echo -e "${BLUE}Azure Portal:${NC}"
echo "https://portal.azure.com/#@/resource/subscriptions/$CURRENT_SUB_ID/resourceGroups/$RESOURCE_GROUP/overview"
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "- Test the API endpoint with the curl command above"
echo "- Check Application Insights for logs and metrics"
echo "- Review the API documentation in docs/API.md"
echo "- Deploy the web client from examples/web-client/"
echo ""
echo -e "${YELLOW}Resource Group: $RESOURCE_GROUP${NC}"
echo -e "${YELLOW}To delete all resources: az group delete --name $RESOURCE_GROUP${NC}"