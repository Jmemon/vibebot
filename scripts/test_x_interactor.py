#!/usr/bin/env python3

import os
import sys
import logging
import webbrowser
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import json

# Add the src directory to the path so we can import modules
sys.path.append(str(Path(__file__).parent.parent))

from src.x_interactor import XInteractor

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """
    Test script to instantiate XInteractor and test its functionality.
    """
    try:
        # Get OAuth credentials from environment or config
        client_id = os.environ.get("X_CLIENT_ID")
        client_secret = os.environ.get("X_CLIENT_SECRET")
        redirect_uri = os.environ.get("X_REDIRECT_URI", "https://localhost:3000/callback")
        
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
            redirect_uri=redirect_uri,
            token=token
        )
        
        # If we don't have a valid token, start OAuth flow
        if not token:
            print("\n=== Starting OAuth 2.0 Authorization Flow ===")
            
            # Generate authorization URL
            auth_url = x_interactor.authenticate()
            print(f"\nAuthorization URL generated: {auth_url}")
            
            # Open the browser for the user to authorize
            print("\nOpening browser for authorization...")
            webbrowser.open(auth_url)
            
            # Get the redirect URL from user input
            print("\nAfter authorizing, you'll be redirected to your redirect URI.")
            print("Please copy and paste the full redirect URL here:")
            redirect_url = input("> ")
            
            # Exchange the code for tokens
            print("\nExchanging code for tokens...")
            token = x_interactor.fetch_token(redirect_url)
            
            print("Token exchange successful!")
            
            # Save the token for future use
            with open(token_file, 'w') as f:
                json.dump(token, f)
            print(f"Token saved to {token_file}")
        
        # Print user ID
        print(f"\nAuthenticated user ID: {x_interactor.user_id}")
        
        # Test get_user_by_username for a specific account
        username = "garrytan"
        logger.info(f"Looking up user: {username}")
        
        user_data = x_interactor.get_user_by_username(username)
        
        # Print the return value
        print(f"\nUser data for {username}:")
        print(user_data)
        
        if user_data and 'id' in user_data:
            target_user_id = user_data['id']
            
            print(f"\nWould you like to unfollow and then follow {username}? (y/n)")
            choice = input("> ").strip().lower()
            if choice == 'y':
                # Unfollow the user
                logger.info(f"Unfollowing user: {username} (ID: {target_user_id})")
                unfollow_result = x_interactor.unfollow_user(target_user_id)
                print(f"Unfollow result: {unfollow_result}")
                
                # Follow the user again
                logger.info(f"Following user: {username} (ID: {target_user_id})")
                follow_result = x_interactor.follow_user(target_user_id)
                print(f"Follow result: {follow_result}")
        else:
            logger.warning(f"Could not find user ID for {username}")
        
        # Test timeline retrieval
        print("\nWould you like to retrieve your timeline? (y/n)")
        choice = input("> ").strip().lower()
        if choice == 'y':
            print("\nRetrieving timeline...")
            timeline = x_interactor.get_timeline(max_tweets=10)
            print(f"Retrieved {len(timeline)} tweets")
            for tweet in timeline:
                print(f"Tweet ID: {tweet.id}")
                print(f"Author ID: {tweet.author_id}")
                print(f"Created at: {tweet.created_at}")
                print(f"Text: {tweet.text[:100]}...")
                print("---")
        
        # Test posting a tweet
        print("\nWould you like to post a test tweet? (y/n)")
        choice = input("> ").strip().lower()
        if choice == 'y':
            tweet_text = input("Enter your tweet text: ")
            tweet_id = x_interactor.post_tweet(tweet_text)
            if tweet_id:
                print(f"Tweet posted successfully! ID: {tweet_id}")
            else:
                print("Failed to post tweet.")
        
        # Test refreshing the token
        print("\nWould you like to test refreshing the OAuth token? (y/n)")
        choice = input("> ").strip().lower()
        if choice == 'y':
            print("Refreshing token...")
            refreshed_token = x_interactor.refresh_token()
            if refreshed_token:
                print("Token refreshed successfully!")
                # Save the refreshed token
                with open(token_file, 'w') as f:
                    json.dump(refreshed_token, f)
                print(f"Refreshed token saved to {token_file}")
            else:
                print("Failed to refresh token.")
        
    except Exception as e:
        logger.error(f"Error in test script: {e}")
        raise

if __name__ == "__main__":
    main()
