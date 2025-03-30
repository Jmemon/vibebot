import os
import json
import logging
import uuid
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from src.config import VibeBotConfig
from src.x_interactor import XInteractor, Tweet
from src.connectors.bot_db import BotDB
from src.connectors.engagement_db import EngagementDB
from src.connectors.community_db import CommunityDB
from src.connectors.quote_comment_db import QuotesCommentsDB

logger = logging.getLogger(__name__)

class VibeBot:
    def __init__(self, config: VibeBotConfig):
        """Initialize the VibeBot.
        
        Args:
            config: Configuration for the bot
        """
        self.config = config
        self._persona = config.persona
        self.max_generation_length = 1000  # Maximum generation length in tokens
        
        # Initialize X interactor
        self.x_interactor = XInteractor(
            client_id=os.environ.get("X_OAUTH2_CLIENT_ID"),
            client_secret=os.environ.get("X_OAUTH2_CLIENT_SECRET"),
            user_id=config.user_id
        )
        
        # Initialize database connections
        db_config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": os.getenv("DB_PORT", "5432"),
            "user": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASSWORD", "postgres"),
            "dbname": os.getenv("DB_NAME", "vibebot")
        }
        
        self.bot_db = BotDB(db_config)
        self.engagement_db = EngagementDB(db_config)
        self.community_db = CommunityDB(db_config)
        self.quotes_comments_db = QuotesCommentsDB(db_config)
        
        # Initialize LLM
        self._initialize_llm()
        
        # Follow accounts specified in config
        self._follow_accounts()
    
    def _initialize_llm(self):
        """Initialize the language model."""
        try:
            logger.info(f"Loading model from {self.config.model.hf_repo_id}")
            
            # Check if we have a checkpoint
            checkpoint_dir = Path(self.config.model.checkpoint_dir)
            if checkpoint_dir.exists() and any(checkpoint_dir.iterdir()):
                logger.info(f"Loading model from checkpoint: {checkpoint_dir}")
                self.llm = AutoModelForCausalLM.from_pretrained(
                    checkpoint_dir,
                    device_map="auto",
                    torch_dtype=torch.float16
                )
            else:
                logger.info(f"Loading model from HuggingFace: {self.config.model.hf_repo_id}")
                self.llm = AutoModelForCausalLM.from_pretrained(
                    self.config.model.hf_repo_id,
                    device_map="auto",
                    torch_dtype=torch.float16
                )
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.config.model.hf_repo_id,
                padding_side="left"
            )
            
            # Ensure the tokenizer has a pad token
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Error initializing LLM: {e}")
            raise
    
    def _follow_accounts(self):
        """Follow the accounts specified in the config."""
        for handle in self.config.accounts_to_follow:
            try:
                # Get user info
                user_info = self.x_interactor.get_user_by_username(handle)
                if user_info:
                    # Follow the user
                    success = self.x_interactor.follow_user(user_info["id"])
                    if success:
                        logger.info(f"Successfully followed user: {handle}")
                    
                    # Add to community DB
                    self.community_db.add_user(
                        user_id=user_info["id"],
                        handle=user_info["username"],
                        followers=user_info["public_metrics"]["followers_count"],
                        following=user_info["public_metrics"]["following_count"],
                        bio=user_info.get("description", ""),
                        location=user_info.get("location", ""),
                        account_summary=f"User {user_info['username']} with {user_info['public_metrics']['followers_count']} followers"
                    )
                    logger.info(f"Added user {handle} to community DB")
                else:
                    logger.warning(f"Could not find user: {handle}")
            except Exception as e:
                logger.error(f"Error following account {handle}: {e}")
    
    @property
    def persona(self) -> Dict[str, Any]:
        """Get the bot's persona."""
        return self._persona
    
    @persona.setter
    def persona(self, persona: Dict[str, Any]) -> None:
        """Set the bot's persona."""
        self._persona = persona
    
    def set_x_interactor(self, x_interactor: XInteractor) -> None:
        """Set the X interactor instance.
        
        Args:
            x_interactor: The XInteractor instance to use
        """
        self.x_interactor = x_interactor
    
    def _generate_text(self, prompt: str, max_length: int = 100) -> str:
        """Generate text using the LLM.
        
        Args:
            prompt: The prompt to generate text from
            max_length: Maximum length of the generated text
            
        Returns:
            The generated text
        """
        try:
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.llm.device)
            
            with torch.no_grad():
                outputs = self.llm.generate(
                    **inputs,
                    max_length=self.max_generation_length,
                    do_sample=True,
                    temperature=0.7,
                    top_p=0.9
                )
            
            generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            # Remove the prompt from the generated text
            if generated_text.startswith(prompt):
                generated_text = generated_text[len(prompt):].strip()
            
            return generated_text
        except Exception as e:
            logger.error(f"Error generating text: {e}")
            return ""
    
    def _should_reply_to_tweet(self, tweet: Tweet) -> bool:
        """Determine if the bot should reply to a tweet.
        
        Args:
            tweet: The tweet to evaluate
            
        Returns:
            True if the bot should reply, False otherwise
        """
        # Skip tweets from the bot itself
        if tweet.author_id == self.config.user_id:
            return False
        
        # Create a prompt to ask the LLM if we should reply
        prompt = f"""
        You are an AI assistant helping to determine if a tweet is worth replying to.
        A good tweet to reply to should:
        1. Touch on newsworthy topics
        2. Introduce substantive ideas that can be expanded upon
        3. Be relevant to the interests of {self.persona.name}, who is interested in {', '.join(self.persona.interests)}
        
        Tweet: "{tweet.text}"
        
        Should we reply to this tweet? Answer with YES or NO and a brief explanation.
        """
        
        response = self._generate_text(prompt, max_length=200)
        
        # Check if the response indicates we should reply
        return response.strip().upper().startswith("YES")
    
    def _generate_reply(self, tweet: Tweet) -> str:
        """Generate a reply to a tweet.
        
        Args:
            tweet: The tweet to reply to
            
        Returns:
            The generated reply
        """
        # Create a prompt for the reply
        prompt = f"""
        You are {self.persona.name}, {self.persona.description}
        
        Your tone is: {self.persona.tone}
        Your interests include: {', '.join(self.persona.interests)}
        
        Someone tweeted: "{tweet.text}"
        
        Write a thoughtful reply to this tweet. Your reply should be engaging, relevant, and reflect your persona.
        Keep your reply concise (under 280 characters) and make sure it adds value to the conversation.
        
        Your reply:
        """
        
        reply = self._generate_text(prompt, max_length=300)
        
        # Ensure the reply is under 280 characters
        if len(reply) > 280:
            reply = reply[:277] + "..."
        
        return reply
    
    def timeline_interface(self, reply_to_tweets: bool = True) -> Tuple[List[Dict[str, Any]], List[Tweet]]:
        """Process the timeline and optionally reply to tweets.
        
        Args:
            reply_to_tweets: Whether to actually post replies or just simulate
            
        Returns:
            Tuple containing:
            - List of tweets we responded to (or would have responded to) and our replies
            - List of tweets we decided to ignore
        """
        logger.info("Processing timeline...")
        
        # Get timeline
        timeline = self.x_interactor.get_timeline(max_tweets=self.config.loop.tl_retrieval_length)
        logger.info(f"Retrieved {len(timeline)} tweets from timeline")
        
        responded_to = []
        ignored = []
        
        for tweet in timeline:
            if self._should_reply_to_tweet(tweet):
                reply_text = self._generate_reply(tweet)
                
                if reply_to_tweets:
                    # Actually post the reply
                    reply_id = self.x_interactor.reply_to_tweet(tweet.id, reply_text)
                    
                    if reply_id:
                        logger.info(f"Posted reply to tweet {tweet.id}: {reply_text}")
                        
                        # Store in bot_db
                        prompt = f"Reply to tweet: {tweet.text}"
                        self.bot_db.add_post(
                            post_id=reply_id,
                            content_gen_prompt=prompt,
                            content=reply_text,
                            is_reply=True
                        )
                        
                        responded_to.append({
                            "original_tweet": tweet,
                            "reply": reply_text,
                            "reply_id": reply_id
                        })
                    else:
                        logger.error(f"Failed to post reply to tweet {tweet.id}")
                else:
                    # Just simulate the reply
                    logger.info(f"Would reply to tweet {tweet.id} with: {reply_text}")
                    responded_to.append({
                        "original_tweet": tweet,
                        "reply": reply_text,
                        "reply_id": None
                    })
            else:
                ignored.append(tweet)
        
        logger.info(f"Processed {len(timeline)} tweets: {len(responded_to)} responses, {len(ignored)} ignored")
        return responded_to, ignored
    
    def get_engagement_metrics(self) -> None:
        """Collect engagement metrics for all posts in the bot_db."""
        logger.info("Collecting engagement metrics...")
        
        # Get all posts from bot_db
        posts = self.bot_db.get_all_posts()
        logger.info(f"Found {len(posts)} posts to check for engagement")
        
        for post in posts:
            post_id = post["post_id"]
            
            try:
                # Get engagement metrics from X API
                metrics = self.x_interactor.get_engagement_metrics(post_id)
                
                # Save quotes and comments to files if they exist
                quotes_filepath = None
                comments_filepath = None
                
                if metrics["quotes"]:
                    quotes_dir = Path("data/quotes")
                    quotes_dir.mkdir(parents=True, exist_ok=True)
                    quotes_filepath = str(quotes_dir / f"{post_id}.json")
                    
                    with open(quotes_filepath, 'w') as f:
                        json.dump(metrics["quotes"], f)
                
                if metrics["comments"]:
                    comments_dir = Path("data/comments")
                    comments_dir.mkdir(parents=True, exist_ok=True)
                    comments_filepath = str(comments_dir / f"{post_id}.json")
                    
                    with open(comments_filepath, 'w') as f:
                        json.dump(metrics["comments"], f)
                
                # Store engagement metrics in engagement_db
                self.engagement_db.add_engagement(
                    post_id=post_id,
                    likes=metrics["likes"],
                    retweets=metrics["retweets"],
                    quotes_filepath=quotes_filepath,
                    comments_filepath=comments_filepath
                )
                
                logger.info(f"Collected engagement metrics for post {post_id}: {metrics['likes']} likes, {metrics['retweets']} retweets")
            except Exception as e:
                logger.error(f"Error collecting engagement metrics for post {post_id}: {e}")
        
        logger.info("Engagement metrics collection completed")
