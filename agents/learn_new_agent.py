import os
import logging
from agents.basic_agent import BasicAgent
from azure.storage.file import FileService

class AzureFileStorageManager:
    def __init__(self):
        storage_connection = os.environ.get('AzureWebJobsStorage', '')
        if not storage_connection:
            raise ValueError("AzureWebJobsStorage connection string is required")
        
        connection_parts = dict(part.split('=', 1) for part in storage_connection.split(';'))
        
        self.account_name = connection_parts.get('AccountName')
        self.account_key = connection_parts.get('AccountKey')
        self.share_name = os.environ.get('AZURE_FILES_SHARE_NAME', 'azfbusinessbot3c92ab')
        
        if not all([self.account_name, self.account_key]):
            raise ValueError("Invalid storage connection string")
        
        self.file_service = FileService(
            account_name=self.account_name,
            account_key=self.account_key
        )
        self._initialize_storage()

    def _initialize_storage(self):
        try:
            self.file_service.create_share(self.share_name, fail_on_exist=True)
        except:
            pass

        try:
            self.file_service.create_directory(
                self.share_name,
                'agents',
                fail_on_exist=True
            )
        except Exception as e:
            logging.error(f"Error creating agents directory: {str(e)}")

    def write_agent_file(self, agent_name, content):
        try:
            file_name = f"{agent_name}_agent.py"
            self.file_service.create_file_from_text(
                self.share_name,
                'agents',
                file_name,
                content
            )
            return True
        except Exception as e:
            logging.error(f"Error writing agent file: {str(e)}")
            return False

class LearnNewAgentAgent(BasicAgent):
    def __init__(self):
        self.name = "LearnNewAgent"
        self.metadata = {
            "name": self.name,
            "description": "Creates a New Python File For a Specified Agent and Allows The GPT Model to Perform That Agent",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "The Name of the New Agent"
                    },
                    "python_implementation": {
                        "type": "string",
                        "description": """The Python Code That is Behind The New Agent. The code should follow the following template:
                            [[[
                            from agents.basic_agent import BasicAgent
                            {import any other libraries}
                            class {name of the new agent}Agent (BasicAgent):
                            def __init__(self):
                                self.name = {AgentName (no spaces)}
                                self.metadata = {
                                    \"name\": self.name,
                                    \"description\": \"{a description of the agent that describes when it should be used and what it does}\",
                                    \"parameters\": {
                                        \"type\": \"object\",
                                        \"properties\": {
                                        \"{parameter 1 name}\": {
                                            \"type\": \"{parameter type, i.e: string}\",
                                            \"description\": \"{description of what the parameter is used for}\"              
                                        },
                                        \"{parameter 2 name}\": {
                                            \"type\": \"{parameter type, i.e: string}\",
                                            \"description\": \"{description of what the parameter is used for}\"
                                        },
                                        },
                                        \"required\": [\"{name of required parameter}\", \"{name of required parameter}\"]
                                    }
                                }
                                super().__init__(name=self.name, metadata=self.metadata)

                            def perform(self, {parameter_1}, {parameter_2}):
                                {agent functionality}
                                return {A STRING that describes the result of the function, NOT A DICTIONARY. Output a STRING}
                            ]]]
                    """
                    }
                },
                "required": ["agent_name", "python_implementation"]
            }
        }
        self.storage_manager = AzureFileStorageManager()
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        """
        Creates a new agent file in the Azure File Storage.
        
        Args:
            agent_name (str): Name of the new agent
            python_implementation (str): Python code for the agent implementation
            
        Returns:
            str: Status message indicating success or failure
        """
        agent_name = kwargs.get('agent_name')
        python_implementation = kwargs.get('python_implementation')
        
        if not agent_name or not python_implementation:
            return "Error: Both agent_name and python_implementation are required"

        # Sanitize agent name
        agent_name = ''.join(c for c in agent_name if c.isalnum())
        
        # Write the agent file to Azure File Storage
        success = self.storage_manager.write_agent_file(agent_name, python_implementation)
        
        if success:
            return f"Successfully created new agent: {agent_name}"
        else:
            return f"Failed to create agent: {agent_name}"