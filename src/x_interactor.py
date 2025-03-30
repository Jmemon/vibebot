import base64
import json
import logging
import os
import random
import string
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.exceptions import RequestException

from supabase import create_client

logger = logging.getLogger(__name__)

class Tweet:
    def __init__(self, tweet_id: str, author_id: str, text: str, created_at: str, 
                referenced_tweets: Optional[List[Dict[str, str]]] = None):
        self.id = tweet_id
        self.author_id = author_id
        self.text = text
        self.created_at = created_at
        self.referenced_tweets = referenced_tweets or []
    
    def __repr__(self):
        return f"Tweet(id={self.id}, author_id={self.author_id}, text='{self.text[:30]}...')"


class XInteractor:
    """Class to interact with the X (Twitter) API using OAuth 2.0 with Supabase for token storage."""
    
    def __init__(self, 
                 client_id: str, 
                 client_secret: Optional[str] = None,
                 redirect_uri: str = "https://localhost:8000/callback",
                 bearer_token: Optional[str] = None,
                 supabase_url: str = None,
                 supabase_key: str = None,
                 user_id: Optional[str] = None,
                 is_confidential_client: bool = True,
                 scopes: List[str] = None):
        """Initialize the X API interactor with Supabase integration.
        
        Args:
            client_id: OAuth 2.0 client ID
            client_secret: OAuth 2.0 client secret (for confidential clients)
            redirect_uri: OAuth 2.0 redirect URI
            bearer_token: Bearer token for app-only authentication
            supabase_url: URL of your Supabase instance
            supabase_key: API key for your Supabase instance
            user_id: The authenticated user's ID
            is_confidential_client: Whether this is a confidential client
            scopes: List of OAuth 2.0 scopes to request
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.bearer_token = bearer_token
        self.user_id = user_id
        self.is_confidential_client = is_confidential_client
        
        # Initialize Supabase client if credentials are provided
        self.supabase = None
        if supabase_url and supabase_key:
            try:
                self.supabase = create_client(supabase_url, supabase_key)
                logger.info("Supabase client initialized successfully")
            except ImportError:
                logger.error("Failed to import supabase. Install with: pip install supabase")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
        
        # Token-related attributes (will be loaded from Supabase if available)
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = None
        
        # Default scopes needed for the bot
        self.scopes = scopes or [
            "tweet.read", 
            "tweet.write", 
            "users.read", 
            "follows.read", 
            "follows.write", 
            "offline.access"
        ]
        
        # Base URLs
        self.api_base_url = "https://api.x.com/2"
        self.auth_url = "https://x.com/i/oauth2/authorize"
        self.token_url = f"{self.api_base_url}/oauth2/token"
        self.revoke_url = f"{self.api_base_url}/oauth2/revoke"
        
        # For PKCE
        self.code_verifier = self._generate_code_verifier()
        self.code_challenge = self.code_verifier  # Using plain method for simplicity
        
        # Load tokens from Supabase if user_id is provided
        if self.user_id and self.supabase:
            self._load_tokens_from_supabase()
            
            # Check if we need to refresh the token
            if self.access_token and self.token_expiry and time.time() > self.token_expiry:
                self._refresh_access_token()
    
    def _load_tokens_from_supabase(self) -> bool:
        """Load OAuth tokens from Supabase.
        
        Returns:
            True if tokens were loaded successfully, False otherwise
        """
        if not self.supabase or not self.user_id:
            return False
        
        try:
            # Query the oauth_tokens table for this user
            response = self.supabase.table('oauth_tokens').select('*').eq('user_id', self.user_id).execute()
            
            if response.data and len(response.data) > 0:
                token_data = response.data[0]
                self.access_token = token_data.get('access_token')
                self.refresh_token = token_data.get('refresh_token')
                self.token_expiry = token_data.get('token_expiry')
                logger.info(f"Loaded tokens from Supabase for user {self.user_id}")
                return True
            else:
                logger.warning(f"No tokens found in Supabase for user {self.user_id}")
                return False
        except Exception as e:
            logger.error(f"Error loading tokens from Supabase: {e}")
            return False
    
    def _save_tokens_to_supabase(self) -> bool:
        """Save OAuth tokens to Supabase.
        
        Returns:
            True if tokens were saved successfully, False otherwise
        """
        if not self.supabase or not self.user_id:
            return False
        
        try:
            # Prepare token data
            token_data = {
                'user_id': self.user_id,
                'access_token': self.access_token,
                'refresh_token': self.refresh_token,
                'token_expiry': self.token_expiry,
                'updated_at': time.time()
            }
            
            # Upsert the token data (insert if not exists, update if exists)
            response = self.supabase.table('oauth_tokens').upsert(token_data).execute()
            
            if response.data:
                logger.info(f"Saved tokens to Supabase for user {self.user_id}")
                return True
            else:
                logger.error("Failed to save tokens to Supabase")
                return False
        except Exception as e:
            logger.error(f"Error saving tokens to Supabase: {e}")
            return False
    
    def _generate_code_verifier(self, length: int = 43) -> str:
        """Generate a code verifier for PKCE.
        
        Args:
            length: Length of the code verifier
            
        Returns:
            A random string to use as code verifier
        """
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))
    
    def _get_basic_auth_header(self) -> Dict[str, str]:
        """Get the basic auth header for confidential clients.
        
        Returns:
            Authorization header dictionary
        """
        if not self.is_confidential_client or not self.client_secret:
            return {}
        
        auth_string = f"{self.client_id}:{self.client_secret}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        return {"Authorization": f"Basic {encoded_auth}"}
    
    def get_authorization_url(self) -> str:
        """Get the URL for the user to authorize the application.
        
        Returns:
            Authorization URL
        """
        state = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32))
        
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "state": state,
            "code_challenge": self.code_challenge,
            "code_challenge_method": "plain"
        }
        
        # Build the query string
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.auth_url}?{query_string}"
    
    def handle_callback(self, code: str, state: str) -> bool:
        """Handle the callback from the authorization server.
        
        Args:
            code: Authorization code
            state: State parameter (should match the one sent)
            
        Returns:
            True if authentication was successful, False otherwise
        """
        try:
            # Exchange the authorization code for an access token
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            # Add basic auth for confidential clients
            headers.update(self._get_basic_auth_header())
            
            data = {
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": self.redirect_uri,
                "code_verifier": self.code_verifier
            }
            
            # Add client_id for public clients
            if not self.is_confidential_client:
                data["client_id"] = self.client_id
            
            response = requests.post(self.token_url, headers=headers, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data.get("access_token")
            self.refresh_token = token_data.get("refresh_token")
            
            # Calculate token expiry time
            expires_in = token_data.get("expires_in", 7200)  # Default 2 hours
            self.token_expiry = time.time() + expires_in
            
            # Get the user ID
            user_info = self._get_user_info()
            
            # Save tokens to Supabase if we have a user_id and Supabase client
            if self.user_id and self.supabase:
                self._save_tokens_to_supabase()
            
            return True
        except RequestException as e:
            logger.error(f"Error during OAuth callback: {e}")
            return False
    
    def _refresh_access_token(self) -> bool:
        """Refresh the access token using the refresh token.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.refresh_token:
            logger.error("No refresh token available")
            return False
        
        try:
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            # Add basic auth for confidential clients
            headers.update(self._get_basic_auth_header())
            
            data = {
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token"
            }
            
            # Add client_id for public clients
            if not self.is_confidential_client:
                data["client_id"] = self.client_id
            
            response = requests.post(self.token_url, headers=headers, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data.get("access_token")
            
            # Update refresh token if provided
            if "refresh_token" in token_data:
                self.refresh_token = token_data.get("refresh_token")
            
            # Calculate token expiry time
            expires_in = token_data.get("expires_in", 7200)  # Default 2 hours
            self.token_expiry = time.time() + expires_in
            
            # Save updated tokens to Supabase
            if self.user_id and self.supabase:
                self._save_tokens_to_supabase()
            
            return True
        except RequestException as e:
            logger.error(f"Error refreshing access token: {e}")
            return False
    
    def revoke_token(self, token: Optional[str] = None) -> bool:
        """Revoke an access or refresh token.
        
        Args:
            token: The token to revoke (defaults to access_token)
            
        Returns:
            True if successful, False otherwise
        """
        if not token and not self.access_token:
            logger.error("No token to revoke")
            return False
        
        token_to_revoke = token or self.access_token
        
        try:
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            # Add basic auth for confidential clients
            headers.update(self._get_basic_auth_header())
            
            data = {
                "token": token_to_revoke
            }
            
            # Add client_id for public clients
            if not self.is_confidential_client:
                data["client_id"] = self.client_id
            
            response = requests.post(self.revoke_url, headers=headers, data=data)
            response.raise_for_status()
            
            # Clear the revoked token
            if token_to_revoke == self.access_token:
                self.access_token = None
            elif token_to_revoke == self.refresh_token:
                self.refresh_token = None
            
            # Update token storage in Supabase
            if self.user_id and self.supabase:
                self._save_tokens_to_supabase()
            
            return True
        except RequestException as e:
            logger.error(f"Error revoking token: {e}")
            return False
    
    def _get_user_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the authenticated user.
        
        Returns:
            User information dictionary if successful, None otherwise
        """
        try:
            response = self._make_authenticated_request("GET", "/users/me")
            if response and response.status_code == 200:
                user_data = response.json().get("data", {})
                self.user_id = user_data.get("id")
                return user_data
            return None
        except RequestException as e:
            logger.error(f"Error getting user info: {e}")
            return None
    
    def _make_authenticated_request(self, method: str, endpoint: str, params: Dict[str, Any] = None, 
                                   data: Dict[str, Any] = None, json_data: Dict[str, Any] = None) -> Optional[requests.Response]:
        """Make an authenticated request to the X API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (starting with /)
            params: Query parameters
            data: Form data
            json_data: JSON data
            
        Returns:
            Response object if successful, None otherwise
        """
        # Check if we need to refresh the token
        if self.access_token and self.token_expiry and time.time() > self.token_expiry:
            if not self._refresh_access_token():
                return None
        
        # Determine which token to use
        if self.access_token:
            auth_header = {"Authorization": f"Bearer {self.access_token}"}
        elif self.bearer_token:
            auth_header = {"Authorization": f"Bearer {self.bearer_token}"}
        else:
            logger.error("No authentication token available")
            return None
        
        url = f"{self.api_base_url}{endpoint}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=auth_header,
                params=params,
                data=data,
                json=json_data
            )
            
            # Check for rate limiting
            if response.status_code == 429:
                reset_time = int(response.headers.get("x-rate-limit-reset", 0))
                wait_time = max(reset_time - time.time(), 0) + 1
                logger.warning(f"Rate limited. Waiting for {wait_time} seconds.")
                time.sleep(wait_time)
                
                # Retry the request
                return self._make_authenticated_request(method, endpoint, params, data, json_data)
            
            return response
        except RequestException as e:
            logger.error(f"Error making request to {endpoint}: {e}")
            return None
    
    def get_timeline(self, user_id: str = None, max_tweets: int = 50) -> List[Tweet]:
        """Get the timeline for a user.
        
        Args:
            user_id: The user ID to get the timeline for (defaults to bot's user_id)
            max_tweets: Maximum number of tweets to retrieve
            
        Returns:
            List of Tweet objects
        """
        target_user_id = user_id or self.user_id
        if not target_user_id:
            logger.error("No user ID provided and no authenticated user")
            return []
        
        try:
            params = {
                "max_results": min(max_tweets, 100),  # API limit is 100
                "tweet.fields": "created_at,referenced_tweets,author_id"
            }
            
            endpoint = f"/users/{target_user_id}/timelines/reverse_chronological"
            response = self._make_authenticated_request("GET", endpoint, params=params)
            
            if not response or response.status_code != 200:
                logger.error(f"Failed to get timeline: {response.status_code if response else 'No response'}")
                return []
            
            data = response.json()
            tweets_data = data.get("data", [])
            
            tweets = []
            for tweet_data in tweets_data:
                tweet = Tweet(
                    tweet_id=tweet_data.get("id"),
                    author_id=tweet_data.get("author_id"),
                    text=tweet_data.get("text", ""),
                    created_at=tweet_data.get("created_at", ""),
                    referenced_tweets=tweet_data.get("referenced_tweets", [])
                )
                tweets.append(tweet)
            
            return tweets
        except Exception as e:
            logger.error(f"Error getting timeline: {e}")
            return []
    
    def post_tweet(self, tweet: str) -> Optional[str]:
        """Post a tweet.
        
        Args:
            tweet: The content of the tweet
            
        Returns:
            The ID of the posted tweet if successful, None otherwise
        """
        try:
            json_data = {
                "text": tweet
            }
            
            response = self._make_authenticated_request("POST", "/tweets", json_data=json_data)
            
            if not response or response.status_code != 201:
                logger.error(f"Failed to post tweet: {response.status_code if response else 'No response'}")
                return None
            
            data = response.json()
            return data.get("data", {}).get("id")
        except Exception as e:
            logger.error(f"Error posting tweet: {e}")
            return None
    
    def reply_to_tweet(self, tweet_id: str, reply: str) -> Optional[str]:
        """Reply to a tweet.
        
        Args:
            tweet_id: The ID of the tweet to reply to
            reply: The content of the reply
            
        Returns:
            The ID of the reply tweet if successful, None otherwise
        """
        try:
            json_data = {
                "text": reply,
                "reply": {
                    "in_reply_to_tweet_id": tweet_id
                }
            }
            
            response = self._make_authenticated_request("POST", "/tweets", json_data=json_data)
            
            if not response or response.status_code != 201:
                logger.error(f"Failed to reply to tweet: {response.status_code if response else 'No response'}")
                return None
            
            data = response.json()
            return data.get("data", {}).get("id")
        except Exception as e:
            logger.error(f"Error replying to tweet: {e}")
            return None
    
    def quote_tweet(self, tweet_id: str, quote: str) -> Optional[str]:
        """Quote a tweet.
        
        Args:
            tweet_id: The ID of the tweet to quote
            quote: The content of the quote
            
        Returns:
            The ID of the quote tweet if successful, None otherwise
        """
        try:
            # For quoting, we need to include the tweet URL in the text
            tweet_url = f"https://x.com/i/web/status/{tweet_id}"
            json_data = {
                "text": f"{quote} {tweet_url}"
            }
            
            response = self._make_authenticated_request("POST", "/tweets", json_data=json_data)
            
            if not response or response.status_code != 201:
                logger.error(f"Failed to quote tweet: {response.status_code if response else 'No response'}")
                return None
            
            data = response.json()
            return data.get("data", {}).get("id")
        except Exception as e:
            logger.error(f"Error quoting tweet: {e}")
            return None
    
    def get_engagement_metrics(self, tweet_id: str) -> Dict[str, Any]:
        """Get engagement metrics for a tweet.
        
        Args:
            tweet_id: The ID of the tweet to get metrics for
            
        Returns:
            Dictionary containing engagement metrics
        """
        try:
            params = {
                "ids": tweet_id,
                "tweet.fields": "public_metrics,non_public_metrics,organic_metrics"
            }
            
            response = self._make_authenticated_request("GET", "/tweets", params=params)
            
            if not response or response.status_code != 200:
                logger.error(f"Failed to get engagement metrics: {response.status_code if response else 'No response'}")
                return {}
            
            data = response.json()
            tweet_data = data.get("data", [])
            
            if not tweet_data:
                return {}
            
            # Extract all metrics
            metrics = {}
            
            # Public metrics (available to all)
            public_metrics = tweet_data[0].get("public_metrics", {})
            metrics.update(public_metrics)
            
            # Non-public metrics (available to tweet author)
            non_public_metrics = tweet_data[0].get("non_public_metrics", {})
            metrics.update(non_public_metrics)
            
            # Organic metrics (available to tweet author)
            organic_metrics = tweet_data[0].get("organic_metrics", {})
            metrics.update(organic_metrics)
            
            return metrics
        except Exception as e:
            logger.error(f"Error getting engagement metrics: {e}")
            return {}
    
    def follow_user(self, target_user_id: str) -> bool:
        """Follow a user using OAuth 2.0.
        
        Args:
            target_user_id: The ID of the user to follow
            
        Returns:
            True if successful, False otherwise
        """
        if not self.user_id:
            logger.error("No authenticated user ID available")
            return False
        
        try:
            json_data = {
                "target_user_id": target_user_id
            }
            
            response = self._make_authenticated_request(
                "POST", 
                f"/users/{self.user_id}/following", 
                json_data=json_data
            )
            
            if not response or response.status_code != 200:
                logger.error(f"Failed to follow user: {response.status_code if response else 'No response'}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error following user: {e}")
            return False
    
    def unfollow_user(self, target_user_id: str) -> bool:
        """Unfollow a user using OAuth 2.0.
        
        Args:
            target_user_id: The ID of the user to unfollow
            
        Returns:
            True if successful, False otherwise
        """
        if not self.user_id:
            logger.error("No authenticated user ID available")
            return False
        
        try:
            response = self._make_authenticated_request(
                "DELETE", 
                f"/users/{self.user_id}/following/{target_user_id}"
            )
            
            if not response or response.status_code != 200:
                logger.error(f"Failed to unfollow user: {response.status_code if response else 'No response'}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error unfollowing user: {e}")
            return False
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user information by username.
        
        Args:
            username: The username to look up
            
        Returns:
            Dictionary containing user information if successful, None otherwise
        """
        try:
            # Remove @ if present
            if username.startswith('@'):
                username = username[1:]
            
            params = {
                "usernames": username,
                "user.fields": "id,name,username,created_at,description,public_metrics"
            }
            
            response = self._make_authenticated_request("GET", "/users/by", params=params)
            
            if not response or response.status_code != 200:
                logger.error(f"Failed to get user by username: {response.status_code if response else 'No response'}")
                return None
            
            data = response.json()
            users_data = data.get("data", [])
            
            if not users_data:
                return None
            
            return users_data[0]
        except Exception as e:
            logger.error(f"Error getting user by username: {e}")
            return None
