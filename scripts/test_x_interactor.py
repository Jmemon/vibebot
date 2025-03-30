#!/usr/bin/env python3

import os
import sys
import logging
import webbrowser
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Add the src directory to the path so we can import modules
sys.path.append(str(Path(__file__).parent.parent))

from src.x_interactor import XInteractor

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_oauth2_flow(x_interactor):
    """Test the OAuth 2.0 Authorization Code Flow with PKCE"""
    print("\n=== Testing OAuth 2.0 Authorization Code Flow with PKCE ===")
    
    # Check if we already have valid OAuth 2.0 credentials
    auth_status = x_interactor.check_auth_status()
    if auth_status['oauth2_valid']:
        print("OAuth 2.0 is already valid. Skipping authorization flow.")
        return True
    
    # Generate authorization URL
    try:
        scopes = ["tweet.read", "users.read", "follows.write", "offline.access"]
        auth_info = x_interactor.get_authorization_url(scopes=scopes)
        
        auth_url = auth_info['authorization_url']
        code_verifier = auth_info['code_verifier']
        state = auth_info['state']
        
        print(f"\nAuthorization URL generated with scopes: {', '.join(scopes)}")
        print(f"State: {state}")
        print(f"Code Verifier: {code_verifier[:10]}...{code_verifier[-10:]}")
        
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
        
        if 'error' in query_params:
            print(f"Authorization failed: {query_params['error'][0]}")
            return False
        
        if 'state' not in query_params or query_params['state'][0] != state:
            print("State mismatch! Possible CSRF attack.")
            return False
        
        if 'code' not in query_params:
            print("No authorization code received.")
            return False
        
        code = query_params['code'][0]
        print(f"Authorization code received: {code[:5]}...{code[-5:]}")
        
        # Exchange the code for tokens
        print("\nExchanging code for tokens...")
        token_data = x_interactor.exchange_code_for_token(code, code_verifier)
        
        print("Token exchange successful!")
        print(f"Access Token: {token_data['access_token'][:10]}...{token_data['access_token'][-10:]}")
        if 'refresh_token' in token_data:
            print(f"Refresh Token: {token_data['refresh_token'][:10]}...{token_data['refresh_token'][-10:]}")
        
        # Verify the token works
        print("\nVerifying token...")
        auth_status = x_interactor.check_auth_status()
        print(f"OAuth 2.0 Valid: {auth_status['oauth2_valid']}")
        
        return auth_status['oauth2_valid']
    
    except Exception as e:
        logger.error(f"Error in OAuth 2.0 flow: {e}")
        return False

def test_token_refresh(x_interactor):
    """Test refreshing the OAuth 2.0 token"""
    print("\n=== Testing OAuth 2.0 Token Refresh ===")
    
    if not x_interactor.oauth2_refresh_token:
        print("No refresh token available. Skipping token refresh test.")
        return False
    
    try:
        print("Refreshing OAuth 2.0 token...")
        refresh_result = x_interactor.refresh_oauth2_token()
        
        if refresh_result:
            print("Token refresh successful!")
            print(f"New Access Token: {x_interactor.oauth2_access_token[:10]}...{x_interactor.oauth2_access_token[-10:]}")
            return True
        else:
            print("Token refresh failed.")
            return False
    
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        return False

def main():
    """
    Test script to instantiate XInteractor and test get_user_by_username method,
    then unfollow and follow a specific account.
    """
    try:
        # Instantiate XInteractor with specific user_id
        x_interactor = XInteractor(user_id="1490171550")
        
        # First check authentication status
        logger.info("Checking authentication status...")
        auth_status = x_interactor.check_auth_status()
        print("Authentication Status:")
        print(f"  Bearer Token Valid: {auth_status['bearer_token_valid']}")
        print(f"  OAuth Valid: {auth_status['oauth_valid']}")
        print(f"  OAuth 1.0a Valid: {auth_status['oauth1_valid']}")
        print(f"  OAuth 2.0 Valid: {auth_status['oauth2_valid']}")
        print(f"  User ID Matches: {auth_status['user_id_matches']}")
        
        # Test OAuth 2.0 flow if needed
        if not auth_status['oauth2_valid']:
            print("\nOAuth 2.0 is not valid. Would you like to test the OAuth 2.0 flow? (y/n)")
            choice = input("> ").strip().lower()
            if choice == 'y':
                oauth2_success = test_oauth2_flow(x_interactor)
                if oauth2_success:
                    # Update auth status after successful OAuth 2.0 flow
                    auth_status = x_interactor.check_auth_status()
        
        # Test token refresh if we have a refresh token
        if x_interactor.oauth2_refresh_token:
            print("\nWould you like to test refreshing the OAuth 2.0 token? (y/n)")
            choice = input("> ").strip().lower()
            if choice == 'y':
                test_token_refresh(x_interactor)
        
        if not auth_status['oauth_valid']:
            logger.error("OAuth authentication is not valid. Follow/unfollow operations will fail.")
            print("Please check your OAuth credentials in the .env file.")
            return
        
        # Test get_user_by_username for garrytan
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
        
    except Exception as e:
        logger.error(f"Error in test script: {e}")
        raise

if __name__ == "__main__":
    main()
