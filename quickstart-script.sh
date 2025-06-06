#!/bin/bash

# Quick Start Script for Azure AI Chatbot
# This script helps users get started in under 5 minutes

set -e

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

clear

echo -e "${BLUE}"
cat << "EOF"
    _    ___    ____ _           _   _           _   
   / \  |_ _|  / ___| |__   __ _| |_| |__   ___ | |_ 
  / _ \  | |  | |   | '_ \ / _` | __| '_ \ / _ \| __|
 / ___ \ | |  | |___| | | | (_| | |_| |_) | (_) | |_ 
/_/   \_\___|  \____|_| |_|\__,_|\__|_.__/ \___/ \__|
                                                      
         Quick Start - Get running in 5 minutes!
EOF
echo -e "${NC}"

# Check if this is the first run
if [ ! -f ".quickstart.lock" ]; then
    echo -e "${YELLOW}Welcome! Let's set up your AI Chatbot.${NC}"
    echo ""
    
    # Check Azure CLI
    if ! command -v az &> /dev/null; then
        echo -e "${YELLOW}Azure CLI not found. Opening installation page...${NC}"
        echo "Please install Azure CLI and run this script again."
        echo ""
        echo "Installation links:"
        echo "- Windows: https://aka.ms/installazurecliwindows"
        echo "- macOS: brew install azure-cli"
        echo "- Linux: curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash"
        exit 1
    fi
    
    # Login to Azure
    echo -e "${YELLOW}Step 1: Azure Login${NC}"
    if ! az account show &> /dev/null; then
        az login
    else
        echo -e "${GREEN}✓ Already logged in${NC}"
    fi
    
    # Quick setup questions
    echo ""
    echo -e "${YELLOW}Step 2: Quick Configuration${NC}"
    echo "Press Enter to use defaults shown in [brackets]"
    echo ""
    
    read -p "Project name [mybot]: " PROJECT_NAME
    PROJECT_NAME=${PROJECT_NAME:-mybot}
    
    read -p "Resource group name [rg-$PROJECT_NAME]: " RESOURCE_GROUP
    RESOURCE_GROUP=${RESOURCE_GROUP:-rg-$PROJECT_NAME}
    
    # Save configuration
    cat > .quickstart.lock << EOL
PROJECT_NAME=$PROJECT_NAME
RESOURCE_GROUP=$RESOURCE_GROUP
DEPLOYMENT_TIME=$(date)
EOL
    
    echo ""
    echo -e "${GREEN}Configuration saved!${NC}"
else
    # Load existing configuration
    source .quickstart.lock
    echo -e "${GREEN}Found existing configuration:${NC}"
    echo "Project: $PROJECT_NAME"
    echo "Resource Group: $RESOURCE_GROUP"
    echo ""
fi

# Menu
echo -e "${YELLOW}What would you like to do?${NC}"
echo "1) Deploy to Azure (first time)"
echo "2) Update deployment"
echo "3) Test the API"
echo "4) View logs"
echo "5) Delete everything"
echo "6) Exit"
echo ""
read -p "Select an option (1-6): " CHOICE

case $CHOICE in
    1)
        echo ""
        echo -e "${YELLOW}Deploying to Azure...${NC}"
        echo "This will take about 5-10 minutes."
        echo ""
        
        # Run the main deployment script
        if [ -f "deploy.sh" ]; then
            chmod +x deploy.sh
            ./deploy.sh -g "$RESOURCE_GROUP" -n "$PROJECT_NAME" -y
        else
            echo -e "${RED}Error: deploy.sh not found${NC}"
            exit 1
        fi
        
        echo ""
        echo -e "${GREEN}Deployment complete!${NC}"
        echo "Run './quickstart.sh' again to test or manage your chatbot."
        ;;
        
    2)
        echo ""
        echo -e "${YELLOW}Updating deployment...${NC}"
        
        # Get function app name
        FUNCTION_APP=$(az functionapp list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv)
        
        if [ -z "$FUNCTION_APP" ]; then
            echo -e "${RED}No function app found. Deploy first!${NC}"
            exit 1
        fi
        
        # Package and deploy
        cd src
        zip -r ../deploy.zip . -q
        cd ..
        
        az functionapp deployment source config-zip \
            --resource-group "$RESOURCE_GROUP" \
            --name "$FUNCTION_APP" \
            --src deploy.zip
        
        rm deploy.zip
        echo -e "${GREEN}✓ Update complete!${NC}"
        ;;
        
    3)
        echo ""
        echo -e "${YELLOW}Testing the API...${NC}"
        
        # Get function details
        FUNCTION_APP=$(az functionapp list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv)
        FUNCTION_URL="https://$FUNCTION_APP.azurewebsites.net/api/businessinsightbot_function"
        FUNCTION_KEY=$(az functionapp function keys list \
            --resource-group "$RESOURCE_GROUP" \
            --name "$FUNCTION_APP" \
            --function-name "businessinsightbot_function" \
            --query "default" -o tsv 2>/dev/null)
        
        echo "Sending test message..."
        response=$(curl -s -X POST "$FUNCTION_URL?code=$FUNCTION_KEY" \
            -H "Content-Type: application/json" \
            -d '{"user_input": "Hello! Tell me about yourself.", "conversation_history": []}')
        
        echo ""
        echo -e "${GREEN}Response:${NC}"
        echo "$response" | jq -r '.assistant_response' 2>/dev/null || echo "$response"
        ;;
        
    4)
        echo ""
        echo -e "${YELLOW}Streaming logs...${NC}"
        echo "Press Ctrl+C to stop"
        echo ""
        
        FUNCTION_APP=$(az functionapp list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv)
        az functionapp log tail --resource-group "$RESOURCE_GROUP" --name "$FUNCTION_APP"
        ;;
        
    5)
        echo ""
        echo -e "${YELLOW}⚠️  WARNING: This will delete all resources!${NC}"
        read -p "Are you sure? Type 'DELETE' to confirm: " CONFIRM
        
        if [ "$CONFIRM" = "DELETE" ]; then
            echo "Deleting resource group..."
            az group delete --name "$RESOURCE_GROUP" --yes --no-wait
            rm -f .quickstart.lock
            echo -e "${GREEN}Deletion initiated. Resources will be removed shortly.${NC}"
        else
            echo "Deletion cancelled."
        fi
        ;;
        
    6)
        echo -e "${GREEN}Goodbye!${NC}"
        exit 0
        ;;
        
    *)
        echo -e "${RED}Invalid option${NC}"
        exit 1
        ;;
esac