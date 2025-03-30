#!/usr/bin/env python3
import os
import yaml
import logging
import argparse
from pathlib import Path

from src.vibebot import VibeBot
from src.config import VibeBotConfig, PersonaConfig, LoopConfig, SFTConfig, PPOConfig, ModelConfig

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

def main():
    parser = argparse.ArgumentParser(description="Test the timeline interface")
    parser.add_argument("--config", type=str, default="configs/demo.yml", help="Path to config file")
    args = parser.parse_args()

    # Check if config file exists, if not create a test config
    config_path = Path(args.config)
    if not config_path.exists():
        logger.info(f"Config file {args.config} not found, creating test config")
        
        # Create test config
        test_config = VibeBotConfig(
            user_id="1234567890",
            accounts_to_follow=["OpenAI", "AndrewYNg", "ylecun"],
            persona=PersonaConfig(
                name="TestBot",
                description="A test bot for exploring X",
                tone="friendly and informative",
                interests=["AI", "machine learning", "technology"],
                adaptive=True
            ),
            loop=LoopConfig(
                tl_retrieval_length=10,
                tl_retrieval_interval=30.0,
                engagement_retrieval_interval=60.0,
                ppo_interval=1440.0
            ),
            sft=SFTConfig(),
            ppo=PPOConfig(),
            model=ModelConfig()
        )
        
        # Create config directory if it doesn't exist
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save test config
        with open(config_path, 'w') as f:
            yaml.dump(test_config.dict(), f)
    
    # Load configuration
    logger.info(f"Loading configuration from {args.config}")
    config = load_config(args.config)
    
    # Initialize the bot
    logger.info("Initializing VibeBot...")
    vibebot = VibeBot(config)
    
    # Run timeline interface without replying
    logger.info("Running timeline interface (without replying)...")
    responded_to, ignored = vibebot.timeline_interface(reply_to_tweets=False)
    
    # Print results
    logger.info(f"Timeline processing complete. Found {len(responded_to)} tweets to respond to and {len(ignored)} to ignore.")
    
    if responded_to:
        logger.info("\nTweets we would respond to:")
        for i, response in enumerate(responded_to, 1):
            logger.info(f"\n{i}. Original tweet: {response['original_tweet'].text}")
            logger.info(f"   Our reply: {response['reply']}")
    
    if ignored:
        logger.info("\nTweets we would ignore:")
        for i, tweet in enumerate(ignored, 1):
            logger.info(f"{i}. {tweet.text}")

if __name__ == "__main__":
    main()
