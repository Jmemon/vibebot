#!/usr/bin/env python3

import os
import sys
import logging
import webbrowser
import time
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
            user_id=token.get('user_id') if token else None
        )
        
        # Set tokens if we have them
        if token:
            x_interactor.access_token = token.get('access_token')
            x_interactor.refresh_token = token.get('refresh_token')
            x_interactor.token_expiry = token.get('expires_at')
        
        # If we don't have a valid token or it's expired, start OAuth flow
        if not x_interactor.access_token or (x_interactor.token_expiry and time.time() > x_interactor.token_expiry):
            print("\n=== Starting OAuth 2.0 Authorization Flow ===")
            
            # Generate authorization URL
            auth_url = x_interactor.get_authorization_url()
            print(f"\nAuthorization URL generated: {auth_url}")
            
            # Open the browser for the user to authorize
            print("\nOpening browser for authorization...")
            webbrowser.open(auth_url)
            
            # Get the redirect URL from user input
            print("\nAfter authorizing, you'll be redirected to your redirect URI.")
            print("Please copy and paste the full redirect URL here:")
            redirect_url = input("> ")
            
            # Parse the redirect URL to get the code and state
            parsed_url = urlparse(redirect_url)
            query_params = parse_qs(parsed_url.query)
            
            if 'code' not in query_params or 'state' not in query_params:
                print("Error: The redirect URL doesn't contain the required parameters.")
                return
            
            code = query_params['code'][0]
            state = query_params['state'][0]
            
            # Exchange the code for tokens
            print("\nExchanging code for tokens...")
            success = x_interactor.handle_callback(code, state)
            
            if success:
                print("Token exchange successful!")
                
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
                print(f"Token saved to {token_file}")
            else:
                print("Token exchange failed!")
                return
        
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
            success = x_interactor._refresh_access_token()
            if success:
                print("Token refreshed successfully!")
                
                # Create updated token dict to save
                updated_token = {
                    'access_token': x_interactor.access_token,
                    'refresh_token': x_interactor.refresh_token,
                    'expires_at': x_interactor.token_expiry,
                    'user_id': x_interactor.user_id
                }
                
                # Save the refreshed token
                with open(token_file, 'w') as f:
                    json.dump(updated_token, f)
                print(f"Refreshed token saved to {token_file}")
            else:
                print("Failed to refresh token.")
        
    except Exception as e:
        logger.error(f"Error in test script: {e}")
        raise

if __name__ == "__main__":
    main()
