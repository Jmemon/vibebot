#!/usr/bin/env python3
import os
import yaml
import logging
import argparse
from pathlib import Path
import torch
import json
import random
from datetime import datetime, timedelta
import uuid

from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model
from trl import PPOTrainer, PPOConfig as TRLPPOConfig

from src.vibebot import VibeBot
from src.config import VibeBotConfig

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_config(config_path):
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        config_dict = yaml.safe_load(f)
    return VibeBotConfig(**config_dict)

def generate_fake_dataset():
    """Generate a fake dataset of tweets and engagement metrics."""
    # Generate 20 fake tweets with varying engagement
    tweets = []
    
    for i in range(20):
        tweet_id = str(uuid.uuid4())
        
        # Create tweet with varying engagement levels
        engagement_level = random.choice(["high", "medium", "low"])
        
        if engagement_level == "high":
            likes = random.randint(50, 100)
            retweets = random.randint(10, 30)
        elif engagement_level == "medium":
            likes = random.randint(10, 49)
            retweets = random.randint(3, 9)
        else:  # low
            likes = random.randint(0, 9)
            retweets = random.randint(0, 2)
        
        # Generate fake tweet text based on engagement level
        if engagement_level == "high":
            text = f"This is a highly engaging tweet about AI and technology! #{i}"
        elif engagement_level == "medium":
            text = f"Here's a moderately interesting thought about machine learning. #{i}"
        else:
            text = f"Just a random thought I had today. #{i}"
        
        # Create tweet object
        tweet = {
            "id": tweet_id,
            "text": text,
            "prompt": f"Write a tweet about technology #{i}",
            "engagement": {
                "likes": likes,
                "retweets": retweets
            }
        }
        
        tweets.append(tweet)
    
    return tweets

def run_ppo_training(vibebot, fake_dataset):
    """Run PPO training on the model with a fake dataset."""
    logger.info("Starting PPO training with fake dataset...")
    
    # Create a temporary checkpoint directory for testing
    test_checkpoint_dir = Path("test_checkpoints")
    test_checkpoint_dir.mkdir(exist_ok=True)
    
    # Initialize LoRA config
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )
    
    # Apply LoRA to the model
    peft_model = get_peft_model(vibebot.llm, lora_config)
    
    # Define reward model (in a real implementation, this would be more sophisticated)
    def compute_reward(tweet_text, engagement):
        """Simple reward function based on engagement metrics."""
        # Normalize likes and retweets
        normalized_likes = min(engagement["likes"] / 100, 1.0)
        normalized_retweets = min(engagement["retweets"] / 30, 1.0)
        
        # Combine metrics (weighted sum)
        reward = 0.7 * normalized_likes + 0.3 * normalized_retweets
        
        return torch.tensor([reward])
    
    # Configure PPO
    ppo_config = TRLPPOConfig(
        learning_rate=1e-5,
        batch_size=4,
        mini_batch_size=2,
        gradient_accumulation_steps=1,
        optimize_cuda_cache=True,
        early_stopping=True,
        target_kl=0.1,
        ppo_epochs=4,
        seed=42
    )
    
    # Initialize PPO trainer
    ppo_trainer = PPOTrainer(
        model=peft_model,
        config=ppo_config,
        tokenizer=vibebot.tokenizer
    )
    
    # Run PPO training
    logger.info("Starting PPO iterations...")
    
    for epoch in range(2):  # Just do 2 epochs for testing
        logger.info(f"PPO Epoch {epoch+1}/2")
        
        # Process each tweet in the dataset
        for tweet in fake_dataset:
            # Create prompt
            prompt = f"""
            You are {vibebot.persona.name}, {vibebot.persona.description}
            Your tone is: {vibebot.persona.tone}
            
            Write a tweet about a topic you're interested in.
            """
            
            # Tokenize prompt
            prompt_tokens = vibebot.tokenizer(prompt, return_tensors="pt").to(peft_model.device)
            
            # Generate response
            response = ppo_trainer.generate(prompt_tokens["input_ids"], max_new_tokens=50)
            response_text = vibebot.tokenizer.decode(response[0], skip_special_tokens=True)
            
            # Compute reward
            reward = compute_reward(response_text, tweet["engagement"])
            
            # Run PPO step
            ppo_trainer.step(prompt_tokens["input_ids"], response, reward)
            
            logger.info(f"Processed tweet with reward: {reward.item():.4f}")
    
    # Save the model
    ppo_trainer.save_pretrained(test_checkpoint_dir)
    logger.info(f"Saved test model to {test_checkpoint_dir}")
    
    # Verify the checkpoint exists
    if (test_checkpoint_dir / "adapter_model.bin").exists():
        logger.info("Checkpoint file exists!")
        
        # Try loading the model
        try:
            test_model = AutoModelForCausalLM.from_pretrained(vibebot.config.model.hf_repo_id)
            test_peft_model = get_peft_model(test_model, lora_config)
            test_peft_model.load_adapter(test_checkpoint_dir)
            logger.info("Successfully loaded model from checkpoint!")
            
            # Clean up
            import shutil
            shutil.rmtree(test_checkpoint_dir)
            logger.info("Cleaned up test checkpoint directory")
        except Exception as e:
            logger.error(f"Error loading model from checkpoint: {e}")
    else:
        logger.error("Checkpoint file does not exist!")

def main():
    parser = argparse.ArgumentParser(description="Test PPO training")
    parser.add_argument("--config", type=str, default="configs/demo.yml", help="Path to config file")
    args = parser.parse_args()

    # Load configuration
    logger.info(f"Loading configuration from {args.config}")
    config = load_config(args.config)
    
    # Initialize the bot
    logger.info("Initializing VibeBot...")
    vibebot = VibeBot(config)
    
    # Generate fake dataset
    logger.info("Generating fake dataset...")
    fake_dataset = generate_fake_dataset()
    
    # Run PPO training
    run_ppo_training(vibebot, fake_dataset)
    
    logger.info("PPO test completed successfully!")

if __name__ == "__main__":
    main()
