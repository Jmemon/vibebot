
# Explorer

## High-Level Overview
Implement an X bot initialized with a list of twitter handles to follow, and will reply and tweet using its engagement metrics to tune its behavior via RL.

## Mid-Level Objectives
- Implement the X interaction class.
- Store a mapping between content-gen prompts, outputs, and periodically updated engagement metric signal.
- Post DB, Engagement DB, Community DB.
- Create a script to initialize the dbs.
- Create a script to kick off the bot.

## Implementation Notes
- DO NOT LEAVE ANYTHING UNIMPLEMENTED FOR ME TO FIGURE OUT.
- Use the X API to interact with X: posting, replying, getting engagement metrics, quote-tweeting, etc.

## Context
### Beginning Context
### Ending Context


## Low-Level Tasks
1. Build the bot config class.
```aider
CREATE src/config.py
    CREATE pydantic PersonaConfig(BaseModel):
        name: str
        description: str
        tone: str
        interests: List[str]
        adaptive: bool

    CREATE pydantic LoopConfig(BaseModel):
        tl_retrieval_length: int  # the number of tweets to retrieve from the TL
        tl_retrieval_interval: float  # the interval in minutes between TL retrievals
        engagement_retrieval_interval: float  # the interval in minutes between engagement metric retrievals
        ppo_interval: float  # the interval in minutes between attempted PPO runs

    CREATE pydantic SFTConfig(BaseModel):
        # in a real implementation, you'd have this training be fully configurable
        approximate_tokens: int = 8_000_000_000  # the approximate number of tokens to pull down from X to train on (8B tokens is approx optimal for a 360M model based on [this paper](https://arxiv.org/pdf/2203.15556))

    CREATE pydantic PPOConfig(BaseModel):
        # in a real implementation, you'd have this training be fully configurable
        pass

    CREATE pydantic ModelConfig(BaseModel):
        hf_repo_id: str = HuggingFaceTB/SmolLM2-360M-Instruct
        checkpoint_dir: str = "checkpoints"  # the directory to store/retrieve the checkpointed model

    CREATE pydantic VibeBotConfig(BaseModel):
        user_id: str  # the user id of the bot's account
        accounts_to_follow: List[str]  # the handles of the accounts to follow to seed community
        persona: PersonaConfig  # the initial persona of the bot
        loop: IntervalConfig  # the intervals between loop iterations
        sft: SFTConfig  # the configuration for the initial SFT training
        ppo: PPOConfig  # the configuration for the contuous PPO training
        model: ModelConfig  # the configuration for the model
```
1. Create initialization script to initialize all the databases with schemas given below.
```aider
CREATE scripts/init_dbs.sh:
    CREATE a psql command to create postgres dbs/bot_db.sql:
        # this table is used to store the content of our posts, and the prompts used to generate them.
        CREATE table bot_db (
            post_id: uuid PRIMARY KEY,
            content_gen_prompt: str,
            content: str,
            is_reply: bool,
            post_time: timestamp
        )

    CREATE a psql command to create postgres dbs/engagement_db.sql:
        # This table is used to store engagement metrics for each of our posts.
        CREATE table engagement_db (
            post_id: uuid PRIMARY KEY,
            retrieval_time: timestamp,
            likes: int,
            retweets: int,
            quotes_filepath: str,
            comments_filepath: str
        )

    CREATE a psql command to create postgres dbs/community_db.sql:
        # This table is used to store user information for each profile that should represent the community of interest.
        CREATE table community_db (
            user_id: uuid PRIMARY KEY,
            handle: str,
            followers: int,
            following: int,
            bio: str,
            location: str,
            account_summary: str
        )

    CREATE a psql command to create postgres dbs/quotes_comments_db.sql:
        # This table is used to store quotes and comments on our posts.
        CREATE table quotes_comments_db (
            post_id: uuid PRIMARY KEY,  # post_id of the original post
            reply_id: uuid,  # post_id of the reply
            comment: bool,  # true if comment, false if quote
            time_of_reply: timestamp
        )
```
1. Create dbs/readme.md.
```aider
CREATE dbs/readme.md:
    ADD structured description of each db with explanation for each column.
```
1. Create db connectors with psycopg2 for each database.
```aider
CREATE src/connectors/bot_db.py:
    CREATE class BotDB that connects to the bot_db postgres db.
    CREATE class EngagementDB that connects to the engagement_db postgres db.
    CREATE class CommunityDB that connects to the community_db postgres db.
    CREATE class QuotesCommentsDB that connects to the quotes_comments_db postgres db.
```
2. Build the X interaction class.
```aider
CREATE src/x_interactor.py:
    CREATE class XInteractor:
        CREATE def __init__(self, user_id: str):
            load api keys from .env
        
        CREATE def get_timeline(self, user_id: str, max_tweets: int = 50) -> List[Tweet]:
            GET timeline from X API with last `max_tweets` tweets (or as many as we haven't already seen)
            User home timeline by user id: https://api.twitter.com/2/users/{id}/timelines/reverse_chronological

        CREATE def post_tweet(self, tweet: str) -> None:
            POST tweet
            Creation of a post: https://api.twitter.com/2/tweets
    
        CREATE def reply_to_tweet(self, tweet_id: str, reply: str) -> None:
            REPLY to tweet with reply
            https://docs.x.com/x-api/posts/creation-of-a-post
            Make sure to fill out the reply field

        CREATE def quote_tweet(self, tweet_id: str, quote: str) -> None:
            QUOTE tweet with quote
            Make sure to use quote_tweet_id in the quote field

        CREATE def get_engagement_metrics(self, tweet_id: str) -> Dict[str, float]:
            GET engagement metrics for tweet from X API
            https://docs.x.com/x-api/users/returns-user-objects-that-have-retweeted-the-provided-post-id
            https://docs.x.com/x-api/posts/retrieve-posts-that-quote-a-post
            https://docs.x.com/x-api/users/returns-user-objects-that-have-liked-the-provided-post-id
```