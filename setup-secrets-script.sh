#!/bin/bash

# Script to set up GitHub secrets for CI/CD pipeline
# This helps users configure their GitHub repository for automated deployment

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}GitHub Secrets Setup for Azure AI Chatbot${NC}"
echo "=========================================="
echo ""

# Check prerequisites
if ! command -v gh &> /dev/null; then
    echo -e "${RED}Error: GitHub CLI (gh) is not installed${NC}"
    echo "Install from: https://cli.github.com/"
    exit 1
fi

if ! command -v az &> /dev/null; then
    echo -e "${RED}Error: Azure CLI is not installed${NC}"
    exit 1
fi

# Check if gh is authenticated
if ! gh auth status &> /dev/null; then
    echo -e "${YELLOW}Authenticating with GitHub...${NC}"
    gh auth login
fi

# Get repository info
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "")
if [ -z "$REPO" ]; then
    echo -e "${RED}Error: Not in a GitHub repository${NC}"
    exit 1
fi

echo -e "${GREEN}Repository: $REPO${NC}"
echo ""

# Get Azure information
echo -e "${YELLOW}Gathering Azure information...${NC}"

# Check Azure login
if ! az account show &> /dev/null; then
    echo -e "${YELLOW}Please login to Azure:${NC}"
    az login
fi

# Get subscription info
SUB_ID=$(az account show --query id -o tsv)
SUB_NAME=$(az account show --query name -o tsv)

echo -e "${GREEN}Azure Subscription: $SUB_NAME${NC}"
echo ""

# Prompt for required information
read -p "Enter your resource group name: " RESOURCE_GROUP
read -p "Enter your project name (3-11 chars): " PROJECT_NAME
read -p "Enter Azure location (e.g., eastus): " LOCATION
read -p "Enter OpenAI location (e.g., eastus): " OPENAI_LOCATION

# Create service principal for GitHub Actions
echo ""
echo -e "${YELLOW}Creating Azure service principal for GitHub Actions...${NC}"

SP_NAME="sp-github-$REPO-$RESOURCE_GROUP"
SP_NAME=${SP_NAME//\//-}  # Replace / with -

# Create service principal
SP_OUTPUT=$(az ad sp create-for-rbac \
    --name "$SP_NAME" \
    --role contributor \
    --scopes "/subscriptions/$SUB_ID/resourceGroups/$RESOURCE_GROUP" \
    --sdk-auth)

if [ $? -ne 0 ]; then
    echo -e "${RED}Error creating service principal${NC}"
    exit 1
fi

# Set GitHub secrets
echo ""
echo -e "${YELLOW}Setting GitHub secrets...${NC}"

# Set AZURE_CREDENTIALS
gh secret set AZURE_CREDENTIALS --body "$SP_OUTPUT"
echo -e "${GREEN}✓ Set AZURE_CREDENTIALS${NC}"

# Set other secrets
gh secret set AZURE_RG --body "$RESOURCE_GROUP"
echo -e "${GREEN}✓ Set AZURE_RG${NC}"

gh secret set PROJECT_NAME --body "$PROJECT_NAME"
echo -e "${GREEN}✓ Set PROJECT_NAME${NC}"

gh secret set AZURE_LOCATION --body "$LOCATION"
echo -e "${GREEN}✓ Set AZURE_LOCATION${NC}"

gh secret set OPENAI_LOCATION --body "$OPENAI_LOCATION"
echo -e "${GREEN}✓ Set OPENAI_LOCATION${NC}"

# Get or create publish profile (optional for faster deployments)
echo ""
echo -e "${YELLOW}Note: AZURE_FUNCTIONAPP_PUBLISH_PROFILE will be set after first deployment${NC}"
echo "You can add it manually later from Azure Portal → Function App → Deployment Center"

# Create environments
echo ""
echo -e "${YELLOW}Creating GitHub environments...${NC}"

# Create production environment
gh api -X PUT "repos/$REPO/environments/production" \
    --field "prevent_self_review=true" \
    --field "deployment_branch_policy[protected_branches]=true" \
    2>/dev/null || echo "Production environment exists"

# Create staging environment
gh api -X PUT "repos/$REPO/environments/staging" \
    2>/dev/null || echo "Staging environment exists"

# Create development environment
gh api -X PUT "repos/$REPO/environments/development" \
    2>/dev/null || echo "Development environment exists"

echo -e "${GREEN}✓ GitHub environments configured${NC}"

# Summary
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                  Setup Complete! ✅                          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}GitHub Secrets Set:${NC}"
echo "- AZURE_CREDENTIALS"
echo "- AZURE_RG: $RESOURCE_GROUP"
echo "- PROJECT_NAME: $PROJECT_NAME"
echo "- AZURE_LOCATION: $LOCATION"
echo "- OPENAI_LOCATION: $OPENAI_LOCATION"
echo ""
echo -e "${BLUE}GitHub Environments Created:${NC}"
echo "- production"
echo "- staging"
echo "- development"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Commit and push your code to trigger deployment"
echo "2. Check Actions tab in GitHub for deployment status"
echo "3. After first deployment, add AZURE_FUNCTIONAPP_PUBLISH_PROFILE secret"
echo ""
echo -e "${GREEN}Service Principal:${NC} $SP_NAME"
echo -e "${YELLOW}To remove access later:${NC} az ad sp delete --id \$(az ad sp list --display-name '$SP_NAME' --query [0].appId -o tsv)"