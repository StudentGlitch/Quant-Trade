import asyncio
from loguru import logger
import os

try:
    from vllm import AsyncLLMEngine, AsyncEngineArgs
    from vllm.lora.request import LoRARequest
except ImportError:
    AsyncLLMEngine = None
    LoRARequest = None

class VLLMEngine:
    """
    Phase 27.3: High-throughput vLLM inference engine.
    Supports dynamic LoRA hot-swapping for fine-tuned personas.
    """
    _instance = None

    def __new__(cls, model_name: str = "NousResearch/Hermes-2-Pro-Mistral-7B"):
        if cls._instance is None:
            cls._instance = super(VLLMEngine, cls).__new__(cls)
            cls._instance.model_name = model_name
            cls._instance.engine = None
            cls._instance._initialize_engine()
        return cls._instance

    def _initialize_engine(self):
        if not AsyncLLMEngine:
            logger.warning("vLLM not installed. Falling back to mock engine.")
            return

        logger.info(f"Initializing vLLM Engine with base model: {self.model_name}")
        
        # Configure engine args to enable LoRA
        engine_args = AsyncEngineArgs(
            model=self.model_name,
            enable_lora=True,
            max_loras=4,
            max_lora_rank=16,
            gpu_memory_utilization=0.85
        )
        
        try:
            self.engine = AsyncLLMEngine.from_engine_args(engine_args)
            logger.success("vLLM Engine initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize vLLM: {e}")
            self.engine = None

    async def generate_response(self, prompt: str, adapter_name: str = None, adapter_path: str = None) -> str:
        """
        Generate text. Optionally hot-swaps a LoRA adapter dynamically.
        """
        if not self.engine:
            logger.debug("vLLM Engine offline. Returning mock response.")
            return f"[MOCK vLLM] Received prompt of len {len(prompt)} with adapter {adapter_name}"

        import uuid
        request_id = str(uuid.uuid4())
        
        lora_request = None
        if adapter_name and adapter_path and os.path.exists(adapter_path):
            lora_request = LoRARequest(adapter_name, 1, adapter_path)
            logger.debug(f"Applying LoRA Adapter: {adapter_name}")
            
        from vllm import SamplingParams
        sampling_params = SamplingParams(temperature=0.7, max_tokens=512)

        try:
            results_generator = self.engine.generate(
                prompt, 
                sampling_params, 
                request_id,
                lora_request=lora_request
            )
            
            final_output = ""
            async for request_output in results_generator:
                final_output = request_output.outputs[0].text
                
            return final_output
            
        except Exception as e:
            logger.error(f"vLLM generation failed: {e}")
            return ""
