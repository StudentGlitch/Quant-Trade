from loguru import logger
import os
import uuid
from datetime import datetime
from ..data.duckdb_repo import DuckDBRepo

class QLoRATrainer:
    """
    Phase 27.2: Unsloth QLoRA & DPO Training Engine.
    Trains proprietary adapters on historical DPO datasets using 4-bit quantization.
    """
    def __init__(self, repo: DuckDBRepo, base_model: str = "NousResearch/Hermes-2-Pro-Mistral-7B"):
        self.repo = repo
        self.base_model = base_model
        
    def train_dpo_adapter(self, adapter_name: str = None):
        """Execute the DPO training pipeline."""
        logger.info(f"Starting QLoRA DPO Training for model: {self.base_model}")
        
        if adapter_name is None:
            adapter_name = f"darwin-finllm-v{datetime.now().strftime('%Y%m%d')}"
            
        run_id = str(uuid.uuid4())
        
        # 1. Fetch DPO Dataset
        dataset_df = self.repo.con.execute("SELECT prompt, chosen_response, rejected_response FROM dpo_preference_dataset").df()
        
        if dataset_df.empty or len(dataset_df) < 10:
            logger.error("Insufficient DPO preference pairs for training. Aborting.")
            return False
            
        logger.info(f"Loaded {len(dataset_df)} DPO pairs.")
        
        # Log training start
        self.repo.con.execute("""
            INSERT INTO llm_finetuning_runs 
            (run_id, start_time, base_model, adapter_name, dataset_size, status)
            VALUES (?, ?, ?, ?, ?, 'TRAINING')
        """, [run_id, datetime.now(), self.base_model, adapter_name, len(dataset_df)])

        try:
            # 2. Lazy Import Heavy ML Dependencies
            # We import these here to prevent the whole system from requiring GPUs if not training
            try:
                from unsloth import FastLanguageModel
                from trl import DPOTrainer
                from transformers import TrainingArguments
                from datasets import Dataset
            except ImportError as e:
                logger.error(f"Unsloth/TRL dependencies not found. Ensure running in GPU pod. Error: {e}")
                self._update_status(run_id, "FAILED")
                return False

            # 3. Initialize Unsloth 4-bit Model
            max_seq_length = 2048
            model, tokenizer = FastLanguageModel.from_pretrained(
                model_name = self.base_model,
                max_seq_length = max_seq_length,
                dtype = None,
                load_in_4bit = True,
            )

            # 4. Configure LoRA parameters
            model = FastLanguageModel.get_peft_model(
                model,
                r = 16, # Low-Rank
                target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
                lora_alpha = 16,
                lora_dropout = 0, # Optimization for unsloth
                bias = "none",
                use_gradient_checkpointing = "unsloth",
                random_state = 3407,
                use_rslora = False,
                loftq_config = None,
            )

            # 5. Format HuggingFace Dataset
            hf_dataset = Dataset.from_pandas(dataset_df.rename(columns={
                'chosen_response': 'chosen', 
                'rejected_response': 'rejected'
            }))

            # 6. Configure DPO Trainer
            training_args = TrainingArguments(
                per_device_train_batch_size = 2,
                gradient_accumulation_steps = 4,
                warmup_steps = 5,
                max_steps = 60, # Small step count for continuous mini-updates
                learning_rate = 2e-4,
                fp16 = not FastLanguageModel.is_bfloat16_supported(),
                bf16 = FastLanguageModel.is_bfloat16_supported(),
                logging_steps = 1,
                optim = "adamw_8bit",
                weight_decay = 0.01,
                lr_scheduler_type = "linear",
                seed = 3407,
                output_dir = "outputs",
            )

            dpo_trainer = DPOTrainer(
                model = model,
                ref_model = None, # Unsloth optimizes this so we don't need a separate ref_model in memory
                args = training_args,
                beta = 0.1, # DPO temperature
                train_dataset = hf_dataset,
                tokenizer = tokenizer,
                max_length = max_seq_length,
                max_prompt_length = 1024,
            )

            # 7. Train
            logger.info("Executing DPO Training...")
            train_result = dpo_trainer.train()
            final_loss = train_result.metrics.get('train_loss', 0.0)

            # 8. Save Adapter
            save_path = f"storage/artifacts/adapters/{adapter_name}"
            model.save_pretrained(save_path)
            tokenizer.save_pretrained(save_path)
            
            logger.success(f"DPO Training complete. Adapter saved to {save_path}. Loss: {final_loss:.4f}")
            
            # 9. Update DB
            self.repo.con.execute("""
                UPDATE llm_finetuning_runs 
                SET end_time = ?, final_loss = ?, status = 'COMPLETED'
                WHERE run_id = ?
            """, [datetime.now(), float(final_loss), run_id])
            
            return True

        except Exception as e:
            logger.error(f"QLoRA Training failed: {e}")
            self._update_status(run_id, "FAILED")
            return False

    def _update_status(self, run_id: str, status: str):
        self.repo.con.execute("UPDATE llm_finetuning_runs SET end_time = ?, status = ? WHERE run_id = ?", 
                              [datetime.now(), status, run_id])
