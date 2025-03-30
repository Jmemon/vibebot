#!/usr/bin/env python3
import os
import yaml
import logging
import argparse
from pathlib import Path
import threading
import time

from src.vibebot import VibeBot
from src.config import VibeBotConfig
from src.data.jump_start import generate_jump_start_dataset, jump_start_training

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

def timeline_loop(vibebot, interval_minutes):
    """Run the timeline interface loop at specified intervals."""
    while True:
        try:
            logger.info("Running timeline interface...")
            vibebot.timeline_interface(reply_to_tweets=True)
            logger.info(f"Timeline interface completed. Sleeping for {interval_minutes} minutes.")
            time.sleep(interval_minutes * 60)
        except Exception as e:
            logger.error(f"Error in timeline loop: {e}")
            time.sleep(60)  # Wait a minute before retrying

def engagement_loop(vibebot, interval_minutes):
    """Run the engagement metrics collection loop at specified intervals."""
    while True:
        try:
            logger.info("Collecting engagement metrics...")
            vibebot.get_engagement_metrics()
            logger.info(f"Engagement metrics collected. Sleeping for {interval_minutes} minutes.")
            time.sleep(interval_minutes * 60)
        except Exception as e:
            logger.error(f"Error in engagement loop: {e}")
            time.sleep(60)  # Wait a minute before retrying

def ppo_loop(vibebot, interval_minutes):
    """Run the PPO training loop at specified intervals."""
    while True:
        try:
            logger.info("Starting PPO training...")
            # This would be implemented in the VibeBot class
            # vibebot.run_ppo_training()
            logger.info(f"PPO training completed. Sleeping for {interval_minutes} minutes.")
            time.sleep(interval_minutes * 60)
        except Exception as e:
            logger.error(f"Error in PPO loop: {e}")
            time.sleep(60)  # Wait a minute before retrying

def main():
    parser = argparse.ArgumentParser(description="Start the VibeBot")
    parser.add_argument("--config", type=str, default="configs/demo.yml", help="Path to config file")
    parser.add_argument("--skip-sft", action="store_true", help="Skip the initial SFT training")
    args = parser.parse_args()

    # Load configuration
    logger.info(f"Loading configuration from {args.config}")
    config = load_config(args.config)
    
    # Initialize the bot
    logger.info("Initializing VibeBot...")
    vibebot = VibeBot(config)
    
    # Generate jump start dataset and train the model with SFT if not skipped
    if not args.skip_sft:
        logger.info("Generating jump start dataset...")
        generate_jump_start_dataset(vibebot)
        
        logger.info("Starting initial SFT training...")
        jump_start_training(vibebot)
    
    # Start the loops in separate threads
    logger.info("Starting main loops...")
    
    tl_thread = threading.Thread(
        target=timeline_loop,
        args=(vibebot, config.loop.tl_retrieval_interval),
        daemon=True
    )
    
    engagement_thread = threading.Thread(
        target=engagement_loop,
        args=(vibebot, config.loop.engagement_retrieval_interval),
        daemon=True
    )
    
    ppo_thread = threading.Thread(
        target=ppo_loop,
        args=(vibebot, config.loop.ppo_interval),
        daemon=True
    )
    
    # Start the threads
    tl_thread.start()
    engagement_thread.start()
    ppo_thread.start()
    
    # Keep the main thread alive
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt. Shutting down...")

if __name__ == "__main__":
    main()
