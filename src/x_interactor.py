import logging
import time
from typing import Dict, List, Optional, Any
import requests
from requests_oauthlib import OAuth2Session

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
    """Class to interact with the X (Twitter) API using OAuth 2.0."""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str, 
                 token: Optional[Dict[str, Any]] = None):
        """Initialize an OAuth2 session to be used for X API interactions.
        
        Args:
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            redirect_uri: OAuth2 redirect URI
            token: Existing OAuth2 token (if available)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.token = token
        
        # X API endpoints
        self.base_url = "https://api.twitter.com/2"
        
        # Initialize OAuth2 session
        self.session = self._create_oauth_session()
        
        # Store bot's user ID after authentication
        self.user_id = self._get_my_user_id() if self.token else None
        
        logger.info(f"XInteractor initialized with user_id: {self.user_id}")
    
    def _create_oauth_session(self) -> OAuth2Session:
        """Create and return an OAuth2 session."""
        scope = ["tweet.read", "tweet.write", "users.read", "follows.write"]
        
        session = OAuth2Session(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
            scope=scope,
            token=self.token
        )
        
        return session
    
    def authenticate(self) -> str:
        """Start the OAuth2 authentication flow.
        
        Returns:
            The authorization URL to redirect the user to
        """
        auth_url, _ = self.session.authorization_url(
            "https://twitter.com/i/oauth2/authorize",
            code_challenge_method="S256"
        )
        return auth_url
    
    def fetch_token(self, authorization_response: str) -> Dict[str, Any]:
        """Complete the OAuth2 authentication flow.
        
        Args:
            authorization_response: The full callback URL after user authorization
            
        Returns:
            The OAuth2 token
        """
        self.token = self.session.fetch_token(
            "https://api.twitter.com/2/oauth2/token",
            authorization_response=authorization_response,
            client_secret=self.client_secret
        )
        
        # Update user_id after successful authentication
        self.user_id = self._get_my_user_id()
        
        return self.token
    
    def refresh_token(self) -> Dict[str, Any]:
        """Refresh the OAuth2 token.
        
        Returns:
            The refreshed OAuth2 token
        """
        self.token = self.session.refresh_token(
            "https://api.twitter.com/2/oauth2/token",
            client_id=self.client_id,
            client_secret=self.client_secret
        )
        return self.token
    
    def _get_my_user_id(self) -> Optional[str]:
        """Get the authenticated user's ID.
        
        Returns:
            The user ID if successful, None otherwise
        """
        try:
            response = self.session.get(f"{self.base_url}/users/me")
            response.raise_for_status()
            return response.json()["data"]["id"]
        except Exception as e:
            logger.error(f"Failed to get user ID: {e}")
            return None
    
    def get_timeline(self, user_id: str = None, max_tweets: int = 50) -> List[Tweet]:
        """Get the timeline for a user.
        
        Args:
            user_id: The user ID to get the timeline for (defaults to bot's user_id)
            max_tweets: Maximum number of tweets to retrieve
                
        Returns:
            List of Tweet objects
        """
        if not user_id:
            user_id = self.user_id
            
        if not user_id:
            logger.error("No user ID provided and no authenticated user ID available")
            return []
        
        try:
            params = {
                "max_results": min(max_tweets, 100),  # API limit is 100
                "tweet.fields": "created_at,referenced_tweets",
                "expansions": "author_id"
            }
            
            response = self.session.get(
                f"{self.base_url}/users/{user_id}/timelines/reverse_chronological",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            tweets = []
            
            for tweet_data in data.get("data", []):
                tweet = Tweet(
                    tweet_id=tweet_data["id"],
                    author_id=tweet_data["author_id"],
                    text=tweet_data["text"],
                    created_at=tweet_data["created_at"],
                    referenced_tweets=tweet_data.get("referenced_tweets")
                )
                tweets.append(tweet)
            
            return tweets
        
        except Exception as e:
            logger.error(f"Failed to get timeline: {e}")
            return []
    
    def post_tweet(self, tweet: str) -> Optional[str]:
        """Post a tweet.
        
        Args:
            tweet: The content of the tweet
                
        Returns:
            The ID of the posted tweet if successful, None otherwise
        """
        try:
            payload = {"text": tweet}
            response = self.session.post(f"{self.base_url}/tweets", json=payload)
            response.raise_for_status()
            
            tweet_id = response.json()["data"]["id"]
            logger.info(f"Posted tweet with ID: {tweet_id}")
            return tweet_id
        
        except Exception as e:
            logger.error(f"Failed to post tweet: {e}")
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
            payload = {
                "text": reply,
                "reply": {
                    "in_reply_to_tweet_id": tweet_id
                }
            }
            
            response = self.session.post(f"{self.base_url}/tweets", json=payload)
            response.raise_for_status()
            
            reply_id = response.json()["data"]["id"]
            logger.info(f"Posted reply with ID: {reply_id} to tweet: {tweet_id}")
            return reply_id
        
        except Exception as e:
            logger.error(f"Failed to reply to tweet: {e}")
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
            tweet_url = f"https://twitter.com/x/status/{tweet_id}"
            full_quote = f"{quote} {tweet_url}"
            
            payload = {"text": full_quote}
            response = self.session.post(f"{self.base_url}/tweets", json=payload)
            response.raise_for_status()
            
            quote_id = response.json()["data"]["id"]
            logger.info(f"Posted quote with ID: {quote_id} for tweet: {tweet_id}")
            return quote_id
        
        except Exception as e:
            logger.error(f"Failed to quote tweet: {e}")
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
                "tweet.fields": "public_metrics,non_public_metrics,organic_metrics"
            }
            
            response = self.session.get(
                f"{self.base_url}/tweets/{tweet_id}",
                params=params
            )
            response.raise_for_status()
            
            tweet_data = response.json()["data"]
            
            # Extract all available metrics
            metrics = {}
            
            # Public metrics are always available
            if "public_metrics" in tweet_data:
                metrics.update(tweet_data["public_metrics"])
            
            # These metrics are only available to the tweet author
            for metric_type in ["non_public_metrics", "organic_metrics"]:
                if metric_type in tweet_data:
                    metrics.update(tweet_data[metric_type])
            
            return metrics
        
        except Exception as e:
            logger.error(f"Failed to get engagement metrics: {e}")
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
            payload = {"target_user_id": target_user_id}
            response = self.session.post(
                f"{self.base_url}/users/{self.user_id}/following",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()["data"]["following"]
            logger.info(f"Follow user {target_user_id} result: {result}")
            return result
        
        except Exception as e:
            logger.error(f"Failed to follow user: {e}")
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
            response = self.session.delete(
                f"{self.base_url}/users/{self.user_id}/following/{target_user_id}"
            )
            response.raise_for_status()
            
            result = not response.json()["data"]["following"]
            logger.info(f"Unfollow user {target_user_id} result: {result}")
            return result
        
        except Exception as e:
            logger.error(f"Failed to unfollow user: {e}")
            return False
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user information by username.
        
        Args:
            username: The username to look up
                
        Returns:
            Dictionary containing user information if successful, None otherwise
        """
        try:
            # Remove @ symbol if present
            if username.startswith('@'):
                username = username[1:]
                
            params = {
                "user.fields": "id,name,username,description,public_metrics"
            }
            
            response = self.session.get(
                f"{self.base_url}/users/by/username/{username}",
                params=params
            )
            response.raise_for_status()
            
            return response.json()["data"]
        
        except Exception as e:
            logger.error(f"Failed to get user by username: {e}")
            return None
