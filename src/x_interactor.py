import os
import requests
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class Tweet:
    def __init__(self, tweet_id: str, author_id: str, text: str, created_at: str, 
                 referenced_tweets: Optional[List[Dict[str, str]]] = None):
        self.id = tweet_id
        self.author_id = author_id
        self.text = text
        self.created_at = created_at
        self.referenced_tweets = referenced_tweets or []

class XInteractor:
    def __init__(self, user_id: str):
        """Initialize the X API interactor.
        
        Args:
            user_id: The user ID of the bot account
        """
        # Load API keys from .env file
        load_dotenv()
        self.api_key = os.getenv("X_API_KEY")
        self.api_key_secret = os.getenv("X_API_KEY_SECRET")
        self.access_token = os.getenv("X_ACCESS_TOKEN")
        self.access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")
        self.bearer_token = os.getenv("X_BEARER_TOKEN")
        
        if not all([self.api_key, self.api_key_secret, self.access_token, 
                   self.access_token_secret, self.bearer_token]):
            raise ValueError("Missing X API credentials in .env file")
        
        self.user_id = user_id
        self.base_url = "https://api.twitter.com/2"
        
    def _get_headers(self) -> Dict[str, str]:
        """Get the authorization headers for X API requests."""
        return {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json"
        }
    
    def get_timeline(self, user_id: str = None, max_tweets: int = 50) -> List[Tweet]:
        """Get the timeline for a user.
        
        Args:
            user_id: The user ID to get the timeline for (defaults to bot's user_id)
            max_tweets: Maximum number of tweets to retrieve
            
        Returns:
            List of Tweet objects
        """
        if user_id is None:
            user_id = self.user_id
            
        url = f"{self.base_url}/users/{user_id}/timelines/reverse_chronological"
        params = {
            "max_results": max_tweets,
            "tweet.fields": "created_at,author_id,referenced_tweets",
            "expansions": "referenced_tweets.id"
        }
        
        try:
            response = requests.get(url, headers=self._get_headers(), params=params)
            response.raise_for_status()
            data = response.json()
            
            tweets = []
            if "data" in data:
                for tweet_data in data["data"]:
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
            logger.error(f"Error getting timeline: {e}")
            return []
    
    def post_tweet(self, tweet: str) -> Optional[str]:
        """Post a tweet.
        
        Args:
            tweet: The content of the tweet
            
        Returns:
            The ID of the posted tweet if successful, None otherwise
        """
        url = f"{self.base_url}/tweets"
        payload = {
            "text": tweet
        }
        
        try:
            response = requests.post(url, headers=self._get_headers(), json=payload)
            response.raise_for_status()
            data = response.json()
            return data["data"]["id"]
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
        url = f"{self.base_url}/tweets"
        payload = {
            "text": reply,
            "reply": {
                "in_reply_to_tweet_id": tweet_id
            }
        }
        
        try:
            response = requests.post(url, headers=self._get_headers(), json=payload)
            response.raise_for_status()
            data = response.json()
            return data["data"]["id"]
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
        url = f"{self.base_url}/tweets"
        payload = {
            "text": quote,
            "quote_tweet_id": tweet_id
        }
        
        try:
            response = requests.post(url, headers=self._get_headers(), json=payload)
            response.raise_for_status()
            data = response.json()
            return data["data"]["id"]
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
        metrics = {
            "likes": 0,
            "retweets": 0,
            "quotes": [],
            "comments": []
        }
        
        # Get likes
        try:
            likes_url = f"{self.base_url}/tweets/{tweet_id}/liking_users"
            likes_response = requests.get(likes_url, headers=self._get_headers())
            likes_response.raise_for_status()
            likes_data = likes_response.json()
            metrics["likes"] = len(likes_data.get("data", []))
        except Exception as e:
            logger.error(f"Error getting likes: {e}")
        
        # Get retweets
        try:
            retweets_url = f"{self.base_url}/tweets/{tweet_id}/retweeted_by"
            retweets_response = requests.get(retweets_url, headers=self._get_headers())
            retweets_response.raise_for_status()
            retweets_data = retweets_response.json()
            metrics["retweets"] = len(retweets_data.get("data", []))
        except Exception as e:
            logger.error(f"Error getting retweets: {e}")
        
        # Get quotes
        try:
            quotes_url = f"{self.base_url}/tweets/search/recent"
            quotes_params = {
                "query": f"url:{tweet_id}",
                "tweet.fields": "author_id,created_at,text"
            }
            quotes_response = requests.get(quotes_url, headers=self._get_headers(), params=quotes_params)
            quotes_response.raise_for_status()
            quotes_data = quotes_response.json()
            metrics["quotes"] = quotes_data.get("data", [])
        except Exception as e:
            logger.error(f"Error getting quotes: {e}")
        
        # Get comments (replies)
        try:
            comments_url = f"{self.base_url}/tweets/search/recent"
            comments_params = {
                "query": f"conversation_id:{tweet_id}",
                "tweet.fields": "author_id,created_at,text,in_reply_to_user_id"
            }
            comments_response = requests.get(comments_url, headers=self._get_headers(), params=comments_params)
            comments_response.raise_for_status()
            comments_data = comments_response.json()
            
            # Filter to only include direct replies to the tweet
            metrics["comments"] = [
                comment for comment in comments_data.get("data", [])
                if comment.get("in_reply_to_user_id") == self.user_id
            ]
        except Exception as e:
            logger.error(f"Error getting comments: {e}")
        
        return metrics
    
    def follow_user(self, target_user_id: str) -> bool:
        """Follow a user.
        
        Args:
            target_user_id: The ID of the user to follow
            
        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/users/{self.user_id}/following"
        payload = {
            "target_user_id": target_user_id
        }
        
        try:
            response = requests.post(url, headers=self._get_headers(), json=payload)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Error following user: {e}")
            return False
    
    def unfollow_user(self, target_user_id: str) -> bool:
        """Unfollow a user.
        
        Args:
            target_user_id: The ID of the user to unfollow
            
        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/users/{self.user_id}/following/{target_user_id}"
        
        try:
            response = requests.delete(url, headers=self._get_headers())
            response.raise_for_status()
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
        url = f"{self.base_url}/users/by/username/{username}"
        params = {
            "user.fields": "id,name,username,description,location,public_metrics"
        }
        
        try:
            response = requests.get(url, headers=self._get_headers(), params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("data")
        except Exception as e:
            logger.error(f"Error getting user by username: {e}")
            return None
