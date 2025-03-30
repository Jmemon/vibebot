
# Explorer

## High-Level Overview
Implement an X bot initialized with a list of twitter handles to follow, and will reply and tweet using its engagement metrics to tune its behavior via RL.

## Mid-Level Objectives
- Implement the X interaction class.
- Store a mapping between content-gen prompts, outputs, and periodically updated engagement metric signal.
- Post DB, Engagement DB, Community DB.
- Design and implement a reward function.
- Implement the RL logic.

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
            https://docs.x.com/x-api/posts/user-home-timeline-by-user-id

        CREATE def post_tweet(self, tweet: str) -> None:
            POST tweet
            https://docs.x.com/x-api/posts/creation-of-a-post
    
        CREATE def reply_to_tweet(self, tweet_id: str, reply: str) -> None:
            REPLY to tweet with reply
            https://docs.x.com/x-api/posts/creation-of-a-post
            Make sure to fill out the reply field

        CREATE def quote_tweet(self, tweet_id: str, quote: str) -> None:
            QUOTE tweet with quote
            https://docs.x.com/x-api/posts/creation-of-a-post
            Make sure to use quote_tweet_id in the quote field

        CREATE def get_engagement_metrics(self, tweet_id: str) -> Dict[str, float]:
            GET engagement metrics for tweet from X API
            https://docs.x.com/x-api/users/returns-user-objects-that-have-retweeted-the-provided-post-id
            https://docs.x.com/x-api/posts/retrieve-posts-that-quote-a-post
            https://docs.x.com/x-api/users/returns-user-objects-that-have-liked-the-provided-post-id
            https://docs.x.com/x-api/posts/get-historical-metrics-for-posts
```
1. Create vibe bot class.
```aider
CREATE src/vibebot.py:
    CREATE class VibeBot:
        CREATE def __init__(self, config: VibeBotConfig):
            CREATE var config = config
            CREATE var x_interactor = instantiate XInteractor with user_id
            CREATE var persona = persona
            Load the specified accounts into the community_db.
            Use the X interactor to follow the specified accounts.
            CREATE var llm = instantiate LLM with model config
            instantiate the bot_db, engagement_db, community_db, and quotes_comments_db connectors.

        CREATE @property def persona(self) -> str:
            return self.persona

        CREATE @property.setter def persona(self, persona: str) -> None:
            set self.persona to persona

        CREATE def timeline_interface(self, reply_to_tweets: bool = True) -> List[Dict[str, Any]], List[Tweet]:
            GET timeline with self.x_interactor and find tweets that are good candidates to reply to:
             - they touch on newsworthy topics
             - they introduce substantive ideas that we can add to
            Write a hard-coded prompt to ask self.llm whether each post satisfies the criteria. 
            For each one: 
            If no: Store the post in the list of tweets that we would ignore
            If yes and reply_to_tweets is True: write a prompt that uses the post + explorer persona to generate a reply:
                post the reply with self.x_interactor
                If successfully posted store the reply in bot_db using given row structure
            If yes and reply_to_tweets is False: write a prompt that uses the post + explorer persona to generate a reply:
                Store the post in a list of tweets that we would have responded to

            Return:
             - the list of the tweets we responded to (or would have responded to) and the replies we generated
             - a list of the tweets we decided to ignore

        CREATE def get_engagement_metrics(self) -> None:
            GET engagement metrics for each post in bot_db
            store engagement metrics in engagement_db using given row structure
```
1.  Create a script to run the bot with some tests.
```aider
CREATE scripts/test_tl_interface.py:
    Initialize the bot with a test persona and handles to follow.
    Grab the timeline, don't reply to any tweets, but print out the tweets we should respond to.
    exit.
```
1. Create a function that pulls down a dataset that we can use to jump start the vibebot's model with a LoRA SFT stage. As well as the training kickoff function.
```aider
CREATE src/data/jump_start.py
    CREATE def generate_jump_start_dataset(self, vibe_bot: VibeBot) -> None:
        Download tweets in a round robin fashion amongst accounts vibebot follows until either:
            - you've downloaded approximately vibebot.config.sft.approximate_tokens. Use the estimation 4 characters per token.
            - Or you've used more than 4 Gb of memory.
        Use vibebot.x_interactor to get the tweets.
        Store the dataset in a sequence of json files in the data/jump_start_files directory.
        The first file should be named 0.json, the second 1.json, etc. Once you've downloaded 500Mb of data, write to a file, then start pulling down more for the next file.

    CREATE def jump_start_training(self, vibe_bot: VibeBot) -> None:
        write a function to kick off lora training with the jump start dataset.
        Use the following doc to learn how to do it.
            https://huggingface.co/docs/peft/main/en/developer_guides/lora
        Use q_proj, k_proj, v_proj as the LoRA layers.
        Make sure to save the lora checkpoint in the checkpoints directory.
```
1. Create a script to tune a dummy model with the RL component of the project.
```aider
CREATE scripts/test_ppo.py:
    Initialize the bot with a test persona and handles to follow.
    Generate a small hard-coded fake dataset of tweets and engagement metrics.
    Run PPO on the model with this fake dataset.
    Ensure it runs without errors, including saving the checkpointed model. VERIFY the checkpoint exists and the model can be successfully loaded from it, then delete this test checkpoint.
```
1. Build the initialization script.
```aider
CREATE scripts/kickoff.py:
    Initialize the bot with the given persona and handles to follow by initializing a VibeBot instance using the config.
    From the handles to follow, pull down posts with the X API to build a jump start dataset to train the model with SFT initially.
    Run the model through a LoRA SFT stage with the spin-up dataset. Storing lora weights in checkpoints.
    Kickoff the loops for: TL interface, engagement metrics pull-down, and PPO training.
```
1. Create docker compose file.
```aider
CREATE docker-compose.yml:
    Run the db init script.
    Run the kickoff script using the config.
```