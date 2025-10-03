import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
import subprocess
import time
from dataclasses import dataclass
from typing import Optional, Any
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)







@dataclass
class AWSConfig:
    """Configuration class for AWS settings"""
    account: str
    region: str


@dataclass
class ModelConfig:
    """Configuration class for model parameters"""
    model_id: str
    max_tokens: int = 32000
    temperature: float = 0.5
    top_p: float = 0.9


class BedrockBase(ABC):
    """Base class for Bedrock interactions with automatic credential refresh"""

    def __init__(self,
                 aws_config: AWSConfig,
                 model_config: Optional[ModelConfig] = None):
        self.aws_config = aws_config
        self.model_config = model_config
        self.last_refresh_time = 0
        self.refresh_interval = 3600  # Refresh every hour (3600 seconds)
        
        self.client = self._initialize_client()

    def _refresh_credentials(self) -> float:
        """Refresh AWS credentials and return current timestamp"""
        cmd = f"ada credentials update --once --account={self.aws_config.account} --provider=conduit --role=IibsAdminAccess-DO-NOT-DELETE".split(
        )
        subprocess.run(cmd)
        current_time = time.time()
        self.last_refresh_time = current_time
        return current_time

    def _initialize_client(self):
        """Initialize the Bedrock client with fresh credentials"""
        self._refresh_credentials()
        config = Config(read_timeout=1000)
        session = boto3.session.Session()
        return session.client(service_name="bedrock-runtime",
                              region_name=self.aws_config.region,
                              config=config)

    def _check_credentials(self):
        """Check if credentials need refreshing"""
        current_time = time.time()
        # Refresh if more than refresh_interval has passed
        if current_time - self.last_refresh_time > self.refresh_interval:
            print("AWS credentials expired. Refreshing...")
            self._refresh_credentials()
            # Recreate the client with fresh credentials
            self.client = self._initialize_client()
            print("AWS credentials refreshed successfully")

    def _get_response(self, prompt: str, max_retries: int = 3) -> str:
        """Base method to get model response with retry logic"""
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Check and refresh credentials if needed
                self._check_credentials()

                # Make the API call
                response = self.client.converse(
                    modelId=self.model_config.model_id,
                    messages=[{
                        "role": "user",
                        "content": [{
                            "text": prompt
                        }],
                    }],
                    inferenceConfig={
                        "maxTokens": self.model_config.max_tokens,
                        "temperature": self.model_config.temperature,
                        "topP": self.model_config.top_p
                    },
                )
                return response["output"]["message"]["content"][0]["text"]

            except ClientError as e:
                error_code = getattr(e, 'response',
                                     {}).get('Error', {}).get('Code', '')
                error_msg = str(e)

                # If token expired error, refresh credentials and retry
                if 'ExpiredToken' in error_code or (
                        'security token' in error_msg.lower()
                        and 'expired' in error_msg.lower()):
                    logger.warning(
                        f"Security token expired. Refreshing credentials (retry {retry_count+1}/{max_retries})..."
                    )
                # If token expired error, refresh credentials and retry
                if 'ExpiredToken' in error_code or 'security token' in error_msg.lower(
                ) and 'expired' in error_msg.lower():
                    print(
                        f"Security token expired. Refreshing credentials (retry {retry_count+1}/{max_retries})..."
                    )
                    self._refresh_credentials()
                    # Recreate the client with fresh credentials
                    self.client = self._initialize_client()
                    retry_count += 1
                else:
                    # Other AWS error, raise immediately with context
                    model_id = self.model_config.model_id
                    logger.error(
                        f"AWS Bedrock error with model {model_id}: {error_code} - {error_msg}"
                    )
                    raise Exception(
                        f"AWS Bedrock error with model {model_id}: {error_code} - {error_msg}"
                    )

            except Exception as e:
                # Non-AWS error, raise immediately
                raise Exception(f"Generation failed: {str(e)}")

        # If we've exhausted all retries
        raise Exception(
            f"Failed to generate response after {max_retries} retries due to credential issues"
        )
    def _get_response_chat(self, msgs: str, max_retries: int = 3) -> str:
        """Base method to get model response with retry logic"""
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Check and refresh credentials if needed
                self._check_credentials()

                # Make the API call
                response = self.client.converse(
                    modelId=self.model_config.model_id,
                    messages=[{
                        "role": "user",
                        "content": [{
                            "text": msgs
                        }]
                    }],
                    inferenceConfig={
                        "maxTokens": self.model_config.max_tokens,
                        "temperature": self.model_config.temperature,
                        "topP": self.model_config.top_p
                    },
                )
                return response["output"]["message"]["content"][0]["text"]

            except ClientError as e:
                error_code = getattr(e, 'response',
                                     {}).get('Error', {}).get('Code', '')
                error_msg = str(e)

                # If token expired error, refresh credentials and retry
                if 'ExpiredToken' in error_code or (
                        'security token' in error_msg.lower()
                        and 'expired' in error_msg.lower()):
                    logger.warning(
                        f"Security token expired. Refreshing credentials (retry {retry_count+1}/{max_retries})..."
                    )
                # If token expired error, refresh credentials and retry
                if 'ExpiredToken' in error_code or 'security token' in error_msg.lower(
                ) and 'expired' in error_msg.lower():
                    print(
                        f"Security token expired. Refreshing credentials (retry {retry_count+1}/{max_retries})..."
                    )
                    self._refresh_credentials()
                    # Recreate the client with fresh credentials
                    self.client = self._initialize_client()
                    retry_count += 1
                else:
                    # Other AWS error, raise immediately with context
                    model_id = self.model_config.model_id
                    logger.error(
                        f"AWS Bedrock error with model {model_id}: {error_code} - {error_msg}"
                    )
                    raise Exception(
                        f"AWS Bedrock error with model {model_id}: {error_code} - {error_msg}"
                    )

            except Exception as e:
                # Non-AWS error, raise immediately
                raise Exception(f"Generation failed: {str(e)}")

        # If we've exhausted all retries
        raise Exception(
            f"Failed to generate response after {max_retries} retries due to credential issues"
        )
    
    @abstractmethod
    def process_response(self, response: str) -> Any:
        """Abstract method for processing model response"""
        pass


class SimpleGeneration(BedrockBase):
    """Simple implementation for text generation"""

    def process_response(self, response: str) -> str:
        """Simple pass-through processing"""
        return response

    def generate(self,
                 prompt: str,
                 temperature: Optional[float] = None) -> str:
        """
        Generate text using the model
        
        Args:
            prompt: The prompt to send to the model
            temperature: Optional temperature override
            
        Returns:
            The model's generated text response
        """

        # Create a temporary model config with overridden temperature if provided
        if temperature is not None:
            temp_model_config = ModelConfig(
                model_id=self.model_config.model_id,
                max_tokens=self.model_config.max_tokens,
                temperature=temperature,
                top_p=self.model_config.top_p)
            # Store original config
            original_config = self.model_config

            # Temporarily replace with our modified config
            self.model_config = temp_model_config
            try:
                
                # Get response with the new temperature
                response = self._get_response(prompt)
                result = self.process_response(response)
            finally:
                # Restore original config regardless of success/failure
                self.model_config = original_config

            return result
        else:
            # Use default configuration
            response = self._get_response(prompt)
            return self.process_response(response)


# generate answer via LLM
def llm_generate_answer(account="334317969575 - WenboAWS", region="us-east-2", model_id="arn:aws:bedrock:us-east-2:334317969575:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0",
                        temperature=0.7, max_tokens=2048, prompt=""):
    # Configuration
    aws_config = AWSConfig(
        account=account,  # Replace with your account
        region=region  # Replace with your region
    )
    # Optional: custom model config
    model_config = ModelConfig(model_id=model_id,
                               temperature=temperature,
                               max_tokens=max_tokens)
    # Create generator
    generator = SimpleGeneration(aws_config, model_config)
    # Test generation
    try:
        response = generator.generate(prompt)
    except Exception as e:
        print(f"Error: {e}")
        exit()
    return response



# Example usage
if __name__ == "__main__":
    response = llm_generate_answer(
        account="334317969575 - WenboAWS",
        region="us-east-2", 
        model_id="arn:aws:bedrock:us-east-2:334317969575:inference-profile/us.anthropic.claude-opus-4-20250514-v1:0",
        temperature=0.7,
        max_tokens=2048,
        prompt="How are you"
    )
    
    if response:
        print(f"Generated response: {response}")
    else:
        print("Failed to generate response")
