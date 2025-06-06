import json
import os
import logging
import re
from azure.storage.file import FileService

def safe_json_loads(json_str):
    """
    Safely loads JSON string, handling potential errors.
    """
    if not json_str:
        return {}
    try:
        if isinstance(json_str, (dict, list)):
            return json_str
        return json.loads(json_str)
    except json.JSONDecodeError:
        return {"error": f"Invalid JSON: {json_str}"}

class AzureFileStorageManager:
    def __init__(self):
        storage_connection = os.environ.get('AzureWebJobsStorage', '')
        if not storage_connection:
            raise ValueError("AzureWebJobsStorage connection string is required")
        
        connection_parts = dict(part.split('=', 1) for part in storage_connection.split(';'))
        
        self.account_name = connection_parts.get('AccountName')
        self.account_key = connection_parts.get('AccountKey')
        self.share_name = os.environ.get('AZURE_FILES_SHARE_NAME', 'azfbusinessbot3c92ab')
        self.shared_memory_path = "shared_memories"  # Default shared memories path
        self.default_file_name = 'memory.json'
        self.current_guid = None
        self.current_memory_path = self.shared_memory_path  # Initialize to shared memory path
        
        # List of accepted default GUIDs that bypass validation
        self.default_guids = [
            "c0p110t0-aaaa-bbbb-cccc-123456789abc",  # Original default from function_app.py
            "d3fau1t0-c0p1-10t0-b0t0-111111111111"   # Additional default seen in logs
        ]
        
        if not all([self.account_name, self.account_key]):
            raise ValueError("Invalid storage connection string")
        
        self.file_service = FileService(
            account_name=self.account_name,
            account_key=self.account_key
        )
        self._ensure_share_exists()

    def _ensure_share_exists(self):
        try:
            self.file_service.create_share(self.share_name, fail_on_exist=False)
            
            # Only ensure shared memories directory and file exist
            self.ensure_directory_exists(self.shared_memory_path)
            try:
                self.file_service.get_file_properties(
                    self.share_name,
                    self.shared_memory_path,
                    self.default_file_name
                )
            except Exception:
                self.file_service.create_file_from_text(
                    self.share_name,
                    self.shared_memory_path,
                    self.default_file_name,
                    '{}'  # Empty JSON object
                )
                logging.info(f"Created new {self.default_file_name} in shared memories directory")
        except Exception as e:
            logging.error(f"Error ensuring share exists: {str(e)}")
            raise

    def set_memory_context(self, guid=None):
        """Set the memory context - only create new directories if valid GUID is provided"""
        if not guid:
            self.current_guid = None
            self.current_memory_path = self.shared_memory_path
            return True
        
        # Accept any default GUID without validation
        if guid in self.default_guids:
            self.current_guid = guid
            user_dir = f"memory/{guid}"
            self.current_memory_path = user_dir
            
            # Check if directory exists, if not create it
            try:
                self.ensure_directory_exists(user_dir)
                # Check if the user memory file exists
                try:
                    self.file_service.get_file_properties(
                        self.share_name,
                        user_dir,
                        "user_memory.json"
                    )
                except Exception:
                    # Create the file if it doesn't exist
                    self.file_service.create_file_from_text(
                        self.share_name,
                        user_dir,
                        "user_memory.json",
                        '{}'  # Empty JSON object
                    )
                    logging.info(f"Created new memory file for default GUID: {guid}")
                return True
            except Exception as e:
                logging.error(f"Error setting up default GUID memory: {str(e)}")
                self.current_guid = None
                self.current_memory_path = self.shared_memory_path
                return False
        
        # For other GUIDs, validate the format
        guid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
        if not guid_pattern.match(guid):
            logging.warning(f"Invalid GUID format: {guid}. Using shared memory.")
            self.current_guid = None
            self.current_memory_path = self.shared_memory_path
            return False
        
        try:
            # Only proceed with GUID-specific setup if GUID is valid
            guid_dir = f"memory/{guid}"
            guid_file = "user_memory.json"
            
            # Check if GUID directory already exists before creating
            try:
                self.file_service.get_file_properties(
                    self.share_name,
                    guid_dir,
                    guid_file
                )
                # If we get here, the file exists
                self.current_guid = guid
                self.current_memory_path = guid_dir
                return True
            except Exception:
                # Create new GUID directory and file
                self.ensure_directory_exists(guid_dir)
                self.file_service.create_file_from_text(
                    self.share_name,
                    guid_dir,
                    guid_file,
                    '{}'  # Empty JSON object
                )
                logging.info(f"Created new memory file for GUID: {guid}")
                self.current_guid = guid
                self.current_memory_path = guid_dir
                return True
            
        except Exception as e:
            logging.error(f"Error setting memory context for GUID {guid}: {str(e)}")
            self.current_guid = None
            self.current_memory_path = self.shared_memory_path
            return False

    def clear_user_memory(self, guid):
        """
        Clear memory for a specific user GUID. Does NOT clear shared memory.
        
        Args:
            guid (str): The user GUID to clear memory for. Required.
                                 
        Returns:
            tuple: (success, message)
                - success (bool): True if cleared successfully, False otherwise.
                - message (str): Status message describing what was cleared or errors.
        """
        if not guid:
            return False, "A user GUID must be provided. Shared memory cannot be cleared for safety reasons."
        
        # Save current context to restore later
        previous_guid = self.current_guid
        previous_path = self.current_memory_path
        
        try:
            # If it's a default GUID, handle it specifically
            if guid in self.default_guids:
                self.current_guid = guid
                self.current_memory_path = f"memory/{guid}"
                
                try:
                    # Check if the directory exists first
                    try:
                        self.file_service.get_file_properties(
                            self.share_name,
                            self.current_memory_path,
                            "user_memory.json"
                        )
                    except Exception:
                        # Create directory and empty file if it doesn't exist
                        self.ensure_directory_exists(self.current_memory_path)
                        # Use legacy format for empty memory (just an empty object)
                        self.write_json({})
                        return True, f"Created empty memory for default GUID: {guid}"
                    
                    # If the file exists, clear its contents (to empty object)
                    self.write_json({})
                    return True, f"Memory for default GUID '{guid}' has been cleared successfully."
                except Exception as e:
                    return False, f"Error clearing memory for default GUID '{guid}': {str(e)}"
            
            # For other GUIDs, validate the format
            guid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
            if not guid_pattern.match(guid):
                return False, f"Invalid GUID format: {guid}. Cannot clear memory."
            
            # Handle regular GUIDs
            self.current_guid = guid
            self.current_memory_path = f"memory/{guid}"
            
            try:
                # Check if the directory exists first
                try:
                    self.file_service.get_file_properties(
                        self.share_name, 
                        self.current_memory_path,
                        "user_memory.json"
                    )
                except Exception:
                    return False, f"No memory found for GUID '{guid}'."
                
                # Clear the memory by writing an empty JSON object
                self.write_json({})
                return True, f"Memory for GUID '{guid}' has been cleared successfully."
            except Exception as e:
                return False, f"Error clearing memory for GUID '{guid}': {str(e)}"
                
        finally:
            # Restore original context
            self.current_guid = previous_guid
            self.current_memory_path = previous_path

    def read_json(self):
        """Read from either GUID-specific memory or shared memories"""
        if self.current_guid and self.current_memory_path != self.shared_memory_path:
            try:
                return self._read_guid_memory()
            except Exception:
                # Fall back to shared memory on any error
                self.current_guid = None
                self.current_memory_path = self.shared_memory_path
                return self._read_shared_memory()
        else:
            return self._read_shared_memory()

    def _read_shared_memory(self):
        try:
            file_content = self.file_service.get_file_to_text(
                self.share_name,
                self.shared_memory_path,
                self.default_file_name
            )
            return safe_json_loads(file_content.content)
        except Exception as e:
            logging.error(f"Error reading from shared memory: {str(e)}")
            if "ResourceNotFound" in str(e):
                self._ensure_share_exists()
            return {}

    def _read_guid_memory(self):
        try:
            file_content = self.file_service.get_file_to_text(
                self.share_name,
                self.current_memory_path,
                "user_memory.json"
            )
            return safe_json_loads(file_content.content)
        except Exception as e:
            logging.error(f"Error reading from GUID memory: {str(e)}")
            raise  # Let read_json handle the fallback

    def write_json(self, data):
        """Write to either GUID-specific memory or shared memories"""
        if self.current_guid and self.current_memory_path != self.shared_memory_path:
            try:
                self._write_guid_memory(data)
            except Exception:
                # Fall back to shared memory on any error
                self.current_guid = None
                self.current_memory_path = self.shared_memory_path
                self._write_shared_memory(data)
        else:
            self._write_shared_memory(data)

    def _write_shared_memory(self, data):
        try:
            json_content = json.dumps(data, indent=4)
            self.file_service.create_file_from_text(
                self.share_name,
                self.shared_memory_path,
                self.default_file_name,
                json_content
            )
        except Exception as e:
            logging.error(f"Error writing to shared memory: {str(e)}")
            if "ResourceNotFound" in str(e):
                self._ensure_share_exists()
                self._write_shared_memory(data)

    def _write_guid_memory(self, data):
        try:
            json_content = json.dumps(data, indent=4)
            self.file_service.create_file_from_text(
                self.share_name,
                self.current_memory_path,
                "user_memory.json",
                json_content
            )
        except Exception as e:
            logging.error(f"Error writing to GUID memory: {str(e)}")
            raise  # Let write_json handle the fallback

    def ensure_directory_exists(self, directory_name):
        """Only creates directories that are explicitly needed"""
        try:
            if not directory_name:
                return False
                
            self.file_service.create_share(self.share_name, fail_on_exist=False)
            
            # Handle nested directories
            parts = directory_name.split('/')
            current_path = ""
            
            for part in parts:
                if part:
                    if current_path:
                        current_path = f"{current_path}/{part}"
                    else:
                        current_path = part
                        
                    self.file_service.create_directory(
                        self.share_name,
                        current_path,
                        fail_on_exist=False
                    )
            return True
        except Exception as e:
            logging.error(f"Error ensuring directory exists: {str(e)}")
            return False

    def write_file(self, directory_name, file_name, content):
        try:
            self.ensure_directory_exists(directory_name)
            self.file_service.create_file_from_text(
                self.share_name,
                directory_name,
                file_name,
                str(content)  # Ensure content is string
            )
            return True
        except Exception as e:
            logging.error(f"Error writing file: {str(e)}")
            return False

    def read_file(self, directory_name, file_name):
        try:
            file_content = self.file_service.get_file_to_text(
                self.share_name,
                directory_name,
                file_name
            )
            return file_content.content
        except Exception as e:
            logging.error(f"Error reading file: {str(e)}")
            return None

    def list_files(self, directory_name):
        try:
            return self.file_service.list_directories_and_files(
                self.share_name,
                directory_name
            )
        except Exception as e:
            logging.error(f"Error listing files: {str(e)}")
            return []
            
    def list_directories(self, parent_directory=None):
        """List all directories under a parent directory"""
        try:
            return self.file_service.list_directories_and_files(
                self.share_name,
                parent_directory
            )
        except Exception as e:
            logging.error(f"Error listing directories: {str(e)}")
            return []
    
    def delete_directory(self, directory_path):
        """Delete a directory and all its contents"""
        try:
            # List all files and subdirectories
            items = self.file_service.list_directories_and_files(
                self.share_name,
                directory_path
            )
            
            # Delete all files
            for item in items:
                if not item.is_directory:
                    self.file_service.delete_file(
                        self.share_name,
                        directory_path,
                        item.name
                    )
                else:
                    # Recursively delete subdirectories
                    self.delete_directory(f"{directory_path}/{item.name}")
            
            # Delete the directory itself
            self.file_service.delete_directory(
                self.share_name,
                directory_path
            )
            
            return True
        except Exception as e:
            logging.error(f"Error deleting directory {directory_path}: {str(e)}")
            return False