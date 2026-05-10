import os
from stable_baselines3 import PPO
from .rl_environment import MarketMicrostructureEnv
from loguru import logger

class RLTrainer:
    """Phase 17.2: Stable-Baselines3 PPO training loop."""

    def __init__(self, model_save_path: str = "storage/artifacts/models/drl_execution.zip"):
        self.model_save_path = model_save_path
        os.makedirs(os.path.dirname(self.model_save_path), exist_ok=True)

    def train(self, total_timesteps: int = 100000):
        logger.info(f"Starting PPO training for {total_timesteps} steps...")
        
        # Initialize env with dummy parent params for training
        env = MarketMicrostructureEnv(total_quantity=1000000, arrival_price=5000.0)
        
        # Initialize PPO Agent
        model = PPO(
            "MlpPolicy", 
            env, 
            verbose=1, 
            learning_rate=0.0003,
            n_steps=2048,
            batch_size=64,
            n_epochs=10,
            gamma=0.99
        )
        
        # Train
        model.learn(total_timesteps=total_timesteps)
        
        # Save
        model.save(self.model_save_path)
        logger.success(f"DRL Model saved to {self.model_save_path}")
        
    def evaluate(self):
        """Run a single episode and log performance."""
        env = MarketMicrostructureEnv(total_quantity=1000000, arrival_price=5000.0)
        model = PPO.load(self.model_save_path)
        
        obs, _ = env.reset()
        done = False
        total_reward = 0
        
        logger.info("Evaluating DRL Agent...")
        while not done:
            action, _states = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            logger.debug(f"Step Reward: {reward:.4f} | IS Bps: {info['is_bps']:.2f}")
            done = terminated or truncated
            
        logger.success(f"Evaluation Complete. Total Reward: {total_reward:.4f}")

if __name__ == "__main__":
    trainer = RLTrainer()
    trainer.train(total_timesteps=1000) # Fast run for MVP
    trainer.evaluate()
