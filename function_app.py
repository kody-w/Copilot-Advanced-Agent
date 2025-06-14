import azure.functions as func
import logging
import json
import os
import importlib
import importlib.util
import inspect
import sys
import re
from agents.basic_agent import BasicAgent
import uuid
from openai import AzureOpenAI
from datetime import datetime
import time
from utils.azure_file_storage import AzureFileStorageManager, safe_json_loads

# Default GUID to use when no specific user GUID is provided
# Memorable pattern related to "copilot" that follows UUID format rules
DEFAULT_USER_GUID = "c0p110t0-aaaa-bbbb-cccc-123456789abc"

def ensure_string_content(message):
    """
    Ensures message content is converted to a string regardless of input type.
    """
    if not isinstance(message, dict):
        return {"role": "user", "content": str(message)}
        
    message = message.copy()
    if 'content' not in message:
        message['content'] = ''
    elif message['content'] is None:
        message['content'] = ''
    else:
        message['content'] = str(message['content'])
    return message

def ensure_string_function_args(function_call):
    """
    Ensures function call arguments are properly stringified.
    """
    if not function_call:
        return None
        
    if isinstance(function_call.arguments, (dict, list)):
        return json.dumps(function_call.arguments)
    return str(function_call.arguments)

def build_cors_response(origin):
    return {
        "Access-Control-Allow-Origin": str(origin or "*"),
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Max-Age": "86400",
    }

def load_agents_from_folder():
    agents_directory = os.path.join(os.path.dirname(__file__), "agents")
    files_in_agents_directory = os.listdir(agents_directory)
    agent_files = [f for f in files_in_agents_directory if f.endswith(".py") and f not in ["__init__.py", "basic_agent.py"]]

    declared_agents = {}
    for file in agent_files:
        try:
            module_name = file[:-3]
            module = importlib.import_module(f'agents.{module_name}')
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, BasicAgent) and obj is not BasicAgent:
                    agent_instance = obj()
                    declared_agents[agent_instance.name] = agent_instance
        except Exception as e:
            logging.error(f"Error loading agent {file}: {str(e)}")
            continue

    storage_manager = AzureFileStorageManager()
    try:
        agent_files = storage_manager.list_files('agents')
        
        for file in agent_files:
            if not file.name.endswith('_agent.py'):
                continue

            try:
                file_content = storage_manager.read_file('agents', file.name)
                if file_content is None:
                    continue

                temp_dir = "/tmp/agents"
                os.makedirs(temp_dir, exist_ok=True)
                temp_file = f"{temp_dir}/{file.name}"

                with open(temp_file, 'w') as f:
                    f.write(file_content)

                if temp_dir not in sys.path:
                    sys.path.append(temp_dir)

                module_name = file.name[:-3]
                spec = importlib.util.spec_from_file_location(module_name, temp_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and
                        issubclass(obj, BasicAgent) and
                        obj is not BasicAgent):
                        agent_instance = obj()
                        declared_agents[agent_instance.name] = agent_instance

                os.remove(temp_file)

            except Exception as e:
                logging.error(f"Error loading agent {file.name} from Azure File Share: {str(e)}")
                continue

    except Exception as e:
        logging.error(f"Error loading agents from Azure File Share: {str(e)}")

    return declared_agents

class Assistant:
    _instance = None
    _is_initialized = False
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Assistant, cls).__new__(cls)
        return cls._instance
        
    def __init__(self, declared_agents):
        # Only initialize once
        if Assistant._is_initialized:
            return
            
        self.config = {
            'assistant_name': str(os.environ.get('ASSISTANT_NAME', 'BusinessInsightBot')),
            'characteristic_description': str(os.environ.get('CHARACTERISTIC_DESCRIPTION', 'helpful business assistant'))
        }

        try:
            self.client = AzureOpenAI(
                api_key=os.environ['AZURE_OPENAI_API_KEY'],
                api_version=os.environ['AZURE_OPENAI_API_VERSION'],
                azure_endpoint=os.environ['AZURE_OPENAI_ENDPOINT']
            )
        except TypeError:
            self.client = AzureOpenAI(
                api_key=os.environ['AZURE_OPENAI_API_KEY'],
                azure_endpoint=os.environ['AZURE_OPENAI_ENDPOINT']
            )

        self.known_agents = self.reload_agents(declared_agents)
        
        # Set the default user GUID instead of None
        self.user_guid = DEFAULT_USER_GUID
        
        self.shared_memory = None
        self.user_memory = None
        self.storage_manager = AzureFileStorageManager()
        
        # Initialize with the default user GUID memory
        self._initialize_context_memory(DEFAULT_USER_GUID)
        
        Assistant._is_initialized = True

    def _check_first_message_for_guid(self, conversation_history):
        """Check if the first message contains only a GUID"""
        if not conversation_history or len(conversation_history) == 0:
            return None
            
        first_message = conversation_history[0]
        if first_message.get('role') == 'user':
            content = str(first_message.get('content', '')).strip()
            guid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
            if guid_pattern.match(content):
                return content
        return None

    def _initialize_context_memory(self, user_guid=None):
        """Initialize context memory with separate shared and user-specific memories"""
        try:
            context_memory_agent = self.known_agents.get('ContextMemory')
            if not context_memory_agent:
                self.shared_memory = "No shared context memory available."
                self.user_memory = "No specific context memory available."
                return

            # Always get shared memories with full_recall=True to ensure complete context
            self.storage_manager.set_memory_context(None)  # Reset to shared context
            self.shared_memory = str(context_memory_agent.perform(full_recall=True))
            
            # If user_guid provided, get user-specific memories with full_recall=True
            # If no user_guid is provided, fall back to the default GUID
            if not user_guid:
                user_guid = DEFAULT_USER_GUID
                
            self.storage_manager.set_memory_context(user_guid)
            self.user_memory = str(context_memory_agent.perform(user_guid=user_guid, full_recall=True))
            
        except Exception as e:
            logging.warning(f"Error initializing context memory: {str(e)}")
            self.shared_memory = "Context memory initialization failed."
            self.user_memory = "Context memory initialization failed."
    
    def extract_user_guid(self, text):
        """Try to extract a GUID from user input, but only if it's the entire message"""
        if text is None:
            return None
            
        text_str = str(text).strip()
        
        # Only match if the entire message is just a GUID
        guid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
        match = guid_pattern.match(text_str)
        if match:
            return match.group(0)
        
        # Also allow labeled GUIDs for explicit behavior
        labeled_guid_pattern = re.compile(r'^guid[:=\s]+([0-9a-f-]{36})$', re.IGNORECASE)
        match = labeled_guid_pattern.match(text_str)
        if match:
            return match.group(1)
                
        return None

    def get_agent_metadata(self):
        agents_metadata = []
        for agent in self.known_agents.values():
            if hasattr(agent, 'metadata'):
                agents_metadata.append(agent.metadata)
        return agents_metadata

    def reload_agents(self, agent_objects):
        known_agents = {}
        if isinstance(agent_objects, dict):
            for agent_name, agent in agent_objects.items():
                if hasattr(agent, 'name'):
                    known_agents[agent.name] = agent
                else:
                    known_agents[str(agent_name)] = agent
        elif isinstance(agent_objects, list):
            for agent in agent_objects:
                if hasattr(agent, 'name'):
                    known_agents[agent.name] = agent
        else:
            logging.warning(f"Unexpected agent_objects type: {type(agent_objects)}")
        return known_agents

    def prepare_messages(self, conversation_history):
        if not isinstance(conversation_history, list):
            conversation_history = []
            
        messages = []
        current_datetime = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        
        # System message
        system_message = {
            "role": "system",
            "content": f"""
<identity>
You are a Microsoft Copilot assistant named {str(self.config.get('assistant_name', 'Assistant'))}, operating within Microsoft Teams.
</identity>

<shared_memory_output>
These are memories accessible by all users of the system:
{str(self.shared_memory)}
</shared_memory_output>

<specific_memory_output>
These are memories specific to the current conversation:
{str(self.user_memory)}
</specific_memory_output>

<context_instructions>
- <shared_memory_output> represents common knowledge shared across all conversations
- <specific_memory_output> represents specific context for the current conversation
- Apply specific context with higher precedence than shared context
- Synthesize information from both contexts for comprehensive responses
</context_instructions>

<agent_usage>
IMPORTANT: You must be honest and accurate about agent usage:
- NEVER pretend or imply you've executed an agent when you haven't actually called it
- NEVER say "using my agent" unless you are actually making a function call to that agent
- NEVER fabricate success messages about data operations that haven't occurred
- If you need to perform an action and don't have the necessary agent, say so directly
- When a user requests an action, either:
  1. Call the appropriate agent and report actual results, or
  2. Say "I don't have the capability to do that" and suggest an alternative
  3. If no details are provided besides the request to run an agent, infer the necessary input parameters by "reading between the lines" of the conversation context so far
</agent_usage>

<formatting>
Format your responses using rich formatting that works well in Teams:
- Use **bold** for emphasis
- Use `code blocks` for technical content
- Apply --- for horizontal rules to separate sections
- Utilize > for important quotes or callouts
- Format code with ```language syntax highlighting
- Create numbered lists with proper indentation
- Add personality when appropriate
- Apply # ## ### headings for clear structure
</formatting>
"""
        }
        messages.append(ensure_string_content(system_message))
        
        # Process conversation history - skip first message if it's just a GUID
        guid_only_first_message = self._check_first_message_for_guid(conversation_history)
        start_idx = 1 if guid_only_first_message else 0
        
        for i in range(start_idx, len(conversation_history)):
            messages.append(ensure_string_content(conversation_history[i]))
            
        return messages
    
    def get_openai_api_call(self, messages):
        try:
            response = self.client.chat.completions.create(
                model="gpt-4.1",
                messages=messages,
                functions=self.get_agent_metadata(),
                function_call="auto"
            )
            return response
        except Exception as e:
            logging.error(f"Error in OpenAI API call: {str(e)}")
            raise

    def get_response(self, prompt, conversation_history, max_retries=3, retry_delay=2):
        # Check if this is a first-time initialization with just a GUID
        # or if a GUID is in the conversation history or current prompt
        guid_from_history = self._check_first_message_for_guid(conversation_history)
        guid_from_prompt = self.extract_user_guid(prompt)
        
        target_guid = guid_from_history or guid_from_prompt
        
        # Set or update the memory context if we have a GUID that's different from current
        if target_guid and target_guid != self.user_guid:
            self.user_guid = target_guid
            self._initialize_context_memory(self.user_guid)
            logging.info(f"User GUID updated to: {self.user_guid}")
        elif not self.user_guid:
            # If for some reason we don't have a user_guid, set it to the default
            self.user_guid = DEFAULT_USER_GUID
            self._initialize_context_memory(self.user_guid)
            logging.info(f"Using default User GUID: {self.user_guid}")
        
        # Ensure prompt is string
        prompt = str(prompt) if prompt is not None else ""
        
        # Skip processing if the prompt is just a GUID and we've already set the context
        if guid_from_prompt and prompt.strip() == guid_from_prompt and self.user_guid == guid_from_prompt:
            return "I've successfully loaded your conversation memory. How can I assist you today?", ""
        
        messages = self.prepare_messages(conversation_history)
        messages.append(ensure_string_content({"role": "user", "content": prompt}))

        agent_logs = []
        retry_count = 0
        needs_follow_up = False

        while retry_count < max_retries:
            try:
                response = self.get_openai_api_call(messages)
                assistant_msg = response.choices[0].message
                msg_contents = assistant_msg.content or ""  # Ensure content is never None

                if not assistant_msg.function_call:
                    return str(msg_contents), "\n".join(map(str, agent_logs))

                agent_name = str(assistant_msg.function_call.name)
                agent = self.known_agents.get(agent_name)

                if not agent:
                    return f"Agent '{agent_name}' does not exist", ""

                # Process function call arguments
                json_data = ensure_string_function_args(assistant_msg.function_call)
                logging.info(f"JSON data before parsing: {json_data}")

                try:
                    agent_parameters = safe_json_loads(json_data)
                    
                    # Sanitize parameters - ensure none are undefined or None
                    sanitized_parameters = {}
                    for key, value in agent_parameters.items():
                        if value is None:
                            sanitized_parameters[key] = ""  # Convert None to empty string
                        else:
                            sanitized_parameters[key] = value
                    
                    # Add user_guid to agent parameters if agent accepts it
                    # Always use the current user_guid (which might be the default)
                    if agent_name in ['ManageMemory', 'ContextMemory']:
                        sanitized_parameters['user_guid'] = self.user_guid
                    
                    # Always perform agent call - no caching
                    result = agent.perform(**sanitized_parameters)
                    agent_logs.append(f"Performed {agent_name} and got result: {str(result)}")
                        
                except Exception as e:
                    return f"Error parsing parameters: {str(e)}", ""

                # Add the function result to messages
                messages.append({
                    "role": "function",
                    "name": agent_name,
                    "content": str(result)
                })
                
                # EVALUATION: Check if we need a follow-up function call
                try:
                    result_json = json.loads(str(result))
                    # Look for error indicators or incomplete data flags
                    needs_follow_up = False
                    if isinstance(result_json, dict):
                        # Check for error indicators
                        if result_json.get('error') or result_json.get('status') == 'incomplete':
                            needs_follow_up = True
                        # Check for specific indicators that another action is needed
                        if result_json.get('requires_additional_action') == True:
                            needs_follow_up = True
                except:
                    # If we can't parse the result as JSON, assume no follow-up needed
                    needs_follow_up = False
                
                # If we don't need a follow-up, get the final response and return
                if not needs_follow_up:
                    final_response = self.get_openai_api_call(messages)
                    final_msg = final_response.choices[0].message
                    return str(final_msg.content or ""), "\n".join(map(str, agent_logs))

            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    logging.warning(f"Error occurred: {str(e)}. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logging.error(f"Max retries reached. Error: {str(e)}")
                    return "An error occurred. Please try again.", ""

        return "Service temporarily unavailable. Please try again later.", ""

app = func.FunctionApp()

@app.route(route="businessinsightbot_function", auth_level=func.AuthLevel.FUNCTION)
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    origin = str(req.headers.get('origin', ''))
    cors_headers = build_cors_response(origin)

    if req.method == 'OPTIONS':
        return func.HttpResponse(
            status_code=200,
            headers=cors_headers
        )

    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            "Invalid JSON in request body",
            status_code=400,
            headers=cors_headers
        )

    if not req_body:
        return func.HttpResponse(
            "Missing JSON payload in request body",
            status_code=400,
            headers=cors_headers
        )

    # Ensure user_input is string
    user_input = str(req_body.get('user_input', ''))
    
    # Ensure conversation_history is list and contents are properly formatted
    conversation_history = req_body.get('conversation_history', [])
    if not isinstance(conversation_history, list):
        conversation_history = []
    
    # Extract user_guid if provided in the request
    user_guid = req_body.get('user_guid')
    
    # Skip validation if input is just a GUID to load memory
    is_guid_only = re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', user_input.strip(), re.IGNORECASE)
    
    # Validate user input for non-GUID requests
    if not is_guid_only and not user_input.strip():
        return func.HttpResponse(
            json.dumps({
                "error": "Missing or empty user_input in JSON payload"
            }),
            status_code=400,
            mimetype="application/json",
            headers=cors_headers
        )

    try:
        agents = load_agents_from_folder()
        assistant = Assistant(agents)
        
        # Set user_guid if provided in the request or found in input
        if user_guid:
            assistant.user_guid = user_guid
            assistant._initialize_context_memory(user_guid)
        elif is_guid_only:
            assistant.user_guid = user_input.strip()
            assistant._initialize_context_memory(user_input.strip())
        # Otherwise, the default GUID will be used (already set in __init__)
            
        assistant_response, agent_logs = assistant.get_response(
            user_input, conversation_history)

        # Include GUID in response if available
        response = {
            "assistant_response": str(assistant_response),
            "agent_logs": str(agent_logs),
            "user_guid": assistant.user_guid  # Return the GUID in use (could be default or provided)
        }

        return func.HttpResponse(
            json.dumps(response),
            mimetype="application/json",
            headers=cors_headers
        )
    except Exception as e:
        error_response = {
            "error": "Internal server error",
            "details": str(e)
        }
        return func.HttpResponse(
            json.dumps(error_response),
            status_code=500,
            mimetype="application/json",
            headers=cors_headers
        )