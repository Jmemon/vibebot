import os
import json
import logging
import math
from pathlib import Path
from typing import List, Dict, Any
import torch
from transformers import Trainer, TrainingArguments
from peft import LoraConfig, get_peft_model

from src.vibebot import VibeBot

logger = logging.getLogger(__name__)

def generate_jump_start_dataset(vibebot: VibeBot) -> None:
    """Generate a dataset for jump-starting the model training.
    
    Args:
        vibebot: The VibeBot instance
    """
    logger.info("Generating jump start dataset...")
    
    # Create directory for dataset
    dataset_dir = Path("src/data/jump_start_files")
    dataset_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all users from community DB
    users = vibebot.community_db.get_all_users()
    if not users:
        logger.warning("No users found in community DB")
        return
    
    logger.info(f"Found {len(users)} users in community DB")
    
    # Calculate approximate tokens needed
    approximate_tokens = vibebot.config.sft.approximate_tokens
    chars_per_token = 4  # Estimation: 4 characters per token
    approximate_chars = approximate_tokens * chars_per_token
    
    # Track total characters downloaded
    total_chars = 0
    file_chars = 0
    file_index = 0
    max_file_size = 500 * 1024 * 1024  # 500MB per file
    
    # Store tweets in a list until we're ready to write to a file
    current_file_tweets = []
    
    # Round-robin through users to get tweets
    user_index = 0
    memory_limit = 4 * 1024 * 1024 * 1024  # 4GB memory limit
    memory_usage = 0
    
    while total_chars < approximate_chars and memory_usage < memory_limit:
        user = users[user_index]
        user_index = (user_index + 1) % len(users)
        
        try:
            # Get specific posts from user's profile
            user_posts = vibebot.x_interactor.get_user_posts(user_id=user["user_id"], max_posts=50)
            
            for tweet in user_posts:
                tweet_data = {
                    "id": tweet.id,
                    "author_id": tweet.author_id,
                    "text": tweet.text,
                    "created_at": tweet.created_at
                }
                
                # Add to current file tweets
                current_file_tweets.append(tweet_data)
                
                # Update character counts
                tweet_chars = len(json.dumps(tweet_data))
                total_chars += tweet_chars
                file_chars += tweet_chars
                
                # Estimate memory usage (rough approximation)
                memory_usage += tweet_chars * 2  # Account for Python object overhead
                
                # Check if we need to write to a file
                if file_chars >= max_file_size:
                    # Write to file
                    output_file = dataset_dir / f"{file_index}.json"
                    with open(output_file, 'w') as f:
                        json.dump(current_file_tweets, f)
                    
                    logger.info(f"Wrote {len(current_file_tweets)} tweets to {output_file} ({file_chars} chars)")
                    
                    # Reset for next file
                    current_file_tweets = []
                    file_chars = 0
                    file_index += 1
                
                # Check if we've reached our limits
                if total_chars >= approximate_chars or memory_usage >= memory_limit:
                    break
            
            logger.info(f"Downloaded {len(user_posts)} posts from user {user['handle']}")
            
            # Check if we've reached our limits
            if total_chars >= approximate_chars or memory_usage >= memory_limit:
                break
                
        except Exception as e:
            logger.error(f"Error downloading tweets for user {user['handle']}: {e}")
    
    # Write any remaining tweets to a file
    if current_file_tweets:
        output_file = dataset_dir / f"{file_index}.json"
        with open(output_file, 'w') as f:
            json.dump(current_file_tweets, f)
        
        logger.info(f"Wrote {len(current_file_tweets)} tweets to {output_file} ({file_chars} chars)")
    
    logger.info(f"Jump start dataset generation complete. Downloaded approximately {total_chars} chars (~{total_chars/chars_per_token} tokens)")

def jump_start_training(vibebot: VibeBot) -> None:
    """Train the model using the jump start dataset.
    
    Args:
        vibebot: The VibeBot instance
    """
    logger.info("Starting jump start training...")
    
    # Check if dataset exists
    dataset_dir = Path("data/jump_start_files")
    if not dataset_dir.exists() or not any(dataset_dir.iterdir()):
        logger.error("Jump start dataset not found. Run generate_jump_start_dataset first.")
        raise FileNotFoundError("Jump start dataset not found. Run generate_jump_start_dataset first.")
    
    # Load dataset
    dataset_files = list(dataset_dir.glob("*.json"))
    logger.info(f"Found {len(dataset_files)} dataset files")
    
    # Prepare training data
    train_data = []
    for file_path in dataset_files:
        try:
            with open(file_path, 'r') as f:
                tweets = json.load(f)
                
                for tweet in tweets:
                    # Format as instruction
                    instruction = f"""
                    You are {vibebot.persona.name}, {vibebot.persona.description}
                    Your tone is: {vibebot.persona.tone}
                    Your interests include: {', '.join(vibebot.persona.interests)}
                    
                    Write a tweet in your own style about a topic you're interested in.
                    """
                    
                    # Use the tweet text as the response
                    response = tweet["text"]
                    
                    train_data.append({
                        "instruction": instruction,
                        "input": "",
                        "output": response
                    })
        except Exception as e:
            logger.error(f"Error loading dataset file {file_path}: {e}")
    
    logger.info(f"Prepared {len(train_data)} training examples")
    
    # Create LoRA configuration
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
    
    # Prepare training arguments
    training_args = TrainingArguments(
        output_dir=vibebot.config.model.checkpoint_dir,
        num_train_epochs=3,
        per_device_train_batch_size=4,
        gradient_accumulation_steps=4,
        warmup_steps=100,
        learning_rate=2e-4,
        fp16=True,
        logging_steps=10,
        save_strategy="epoch",
        evaluation_strategy="no",
        report_to="none"
    )
    
    # Create a simple dataset class
    class SimpleDataset(torch.utils.data.Dataset):
        def __init__(self, data):
            self.data = data
        
        def __len__(self):
            return len(self.data)
        
        def __getitem__(self, idx):
            item = self.data[idx]
            
            # Format as instruction
            text = f"### Instruction:\n{item['instruction']}\n\n"
            if item['input']:
                text += f"### Input:\n{item['input']}\n\n"
            text += f"### Response:\n{item['output']}"
            
            # Tokenize
            encodings = vibebot.tokenizer(text, truncation=True, max_length=512, padding="max_length")
            
            return {
                "input_ids": torch.tensor(encodings["input_ids"]),
                "attention_mask": torch.tensor(encodings["attention_mask"]),
                "labels": torch.tensor(encodings["input_ids"])
            }
    
    # Create dataset
    train_dataset = SimpleDataset(train_data)
    
    # Initialize trainer
    trainer = Trainer(
        model=peft_model,
        args=training_args,
        train_dataset=train_dataset,
        data_collator=lambda data: {
            'input_ids': torch.stack([f['input_ids'] for f in data]),
            'attention_mask': torch.stack([f['attention_mask'] for f in data]),
            'labels': torch.stack([f['labels'] for f in data]),
        }
    )
    
    # Train the model
    logger.info("Starting LoRA training...")
    trainer.train()
    
    # Save the trained model
    peft_model.save_pretrained(vibebot.config.model.checkpoint_dir)
    logger.info(f"Saved trained model to {vibebot.config.model.checkpoint_dir}")
