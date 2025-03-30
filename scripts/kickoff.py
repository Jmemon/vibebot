#!/usr/bin/env python3
import sys
import os
import yaml
import logging
import argparse
from pathlib import Path
import threading
import time
import json
import webbrowser
from urllib.parse import urlparse, parse_qs

from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.vibebot import VibeBot
from src.config import VibeBotConfig
from src.data.jump_start import generate_jump_start_dataset, jump_start_training
from src.x_interactor import XInteractor

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
    # Wait for the first interval before starting
    logger.info(f"PPO loop initialized. Waiting {interval_minutes} minutes before first run.")
    time.sleep(interval_minutes * 60)
    
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

def setup_x_interactor():
    """Set up and authenticate the X interactor."""
    load_dotenv()

    try:
        # Get OAuth credentials from environment
        client_id = os.environ.get("X_OAUTH2_CLIENT_ID")
        client_secret = os.environ.get("X_OAUTH2_CLIENT_SECRET")
        
        # Check if we have a saved token
        token_file = Path.home() / ".x_oauth_token.json"
        token = None
        if token_file.exists():
            try:
                with open(token_file, 'r') as f:
                    token = json.load(f)
                logger.info("Loaded existing OAuth token")
            except Exception as e:
                logger.error(f"Error loading token file: {e}")
        
        # Initialize XInteractor
        x_interactor = XInteractor(
            client_id=client_id,
            client_secret=client_secret,
            user_id=token.get('user_id') if token else None
        )
        
        # Set tokens if we have them
        if token:
            x_interactor.access_token = token.get('access_token')
            x_interactor.refresh_token = token.get('refresh_token')
            x_interactor.token_expiry = token.get('expires_at')
        
        # If we don't have a valid token or it's expired, start OAuth flow
        if not x_interactor.access_token or (x_interactor.token_expiry and time.time() > x_interactor.token_expiry):
            logger.info("Starting OAuth 2.0 Authorization Flow")
            
            # Generate authorization URL
            auth_url = x_interactor.get_authorization_url()
            logger.info(f"Authorization URL generated: {auth_url}")
            
            # Open the browser for the user to authorize
            logger.info("Opening browser for authorization...")
            webbrowser.open(auth_url)
            
            # Get the redirect URL from user input
            print("\nAfter authorizing, you'll be redirected to your redirect URI.")
            print("Please copy and paste the full redirect URL here:")
            redirect_url = input("> ")
            
            # Parse the redirect URL to get the code and state
            parsed_url = urlparse(redirect_url)
            query_params = parse_qs(parsed_url.query)
            
            if 'code' not in query_params or 'state' not in query_params:
                logger.error("The redirect URL doesn't contain the required parameters.")
                return None
            
            code = query_params['code'][0]
            state = query_params['state'][0]
            
            # Exchange the code for tokens
            logger.info("Exchanging code for tokens...")
            success = x_interactor.handle_callback(code, state)
            
            if success:
                logger.info("Token exchange successful!")
                
                # Create token dict to save
                token = {
                    'access_token': x_interactor.access_token,
                    'refresh_token': x_interactor.refresh_token,
                    'expires_at': x_interactor.token_expiry,
                    'user_id': x_interactor.user_id
                }
                
                # Save the token for future use
                with open(token_file, 'w') as f:
                    json.dump(token, f)
                logger.info(f"Token saved to {token_file}")
            else:
                logger.error("Token exchange failed!")
                return None
        
        logger.info(f"Authenticated with X as user ID: {x_interactor.user_id}")
        return x_interactor
        
    except Exception as e:
        logger.error(f"Error setting up X interactor: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Start the VibeBot")
    parser.add_argument("--config", type=str, default="configs/demo.yml", help="Path to config file")
    parser.add_argument("--skip-sft", action="store_true", help="Skip the initial SFT training")
    parser.add_argument("--skip-x-auth", action="store_true", help="Skip X authentication (use for testing)")
    args = parser.parse_args()

    # Load configuration
    logger.info(f"Loading configuration from {args.config}")
    config = load_config(args.config)
    
    # Set up X interactor if not skipped
    x_interactor = None
    if not args.skip_x_auth:
        logger.info("Setting up X interactor...")
        x_interactor = setup_x_interactor()
        if not x_interactor:
            logger.error("Failed to set up X interactor. Exiting.")
            return
    
    # Initialize the bot
    logger.info("Initializing VibeBot...")
    vibebot = VibeBot(config)
    
    # Set the X interactor in the VibeBot if available
    if x_interactor:
        # This assumes VibeBot has a method to set the X interactor
        # You may need to modify the VibeBot class to accept an external X interactor
        if hasattr(vibebot, 'set_x_interactor'):
            vibebot.set_x_interactor(x_interactor)
    
    # Generate jump start dataset and train the model with SFT if not skipped
    if not args.skip_sft:
        try:
            logger.info("Starting initial SFT training...")
            jump_start_training(vibebot)
        except FileNotFoundError:
            logger.info("Jump start dataset not found. Generating it...")
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
