

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