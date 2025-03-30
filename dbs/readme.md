# Database Structure

This directory contains the database schemas for the VibeBot project. Below is a description of each database and its columns.

## Bot Database (bot_db)

This database stores information about posts made by the bot.

| Column | Type | Description |
|--------|------|-------------|
| post_id | uuid | Primary key, unique identifier for the post |
| content_gen_prompt | str | The prompt used to generate the content |
| content | str | The actual content of the post |
| is_reply | bool | Whether the post is a reply to another post |
| post_time | timestamp | When the post was made |

## Engagement Database (engagement_db)

This database stores engagement metrics for each post made by the bot.

| Column | Type | Description |
|--------|------|-------------|
| post_id | uuid | Primary key, unique identifier for the post |
| retrieval_time | timestamp | When the engagement metrics were retrieved |
| likes | int | Number of likes the post received |
| retweets | int | Number of retweets the post received |
| quotes_filepath | str | Path to file containing quotes of the post |
| comments_filepath | str | Path to file containing comments on the post |

## Community Database (community_db)

This database stores information about users in the bot's community of interest.

| Column | Type | Description |
|--------|------|-------------|
| user_id | uuid | Primary key, unique identifier for the user |
| handle | str | The user's handle/username |
| followers | int | Number of followers the user has |
| following | int | Number of accounts the user is following |
| bio | str | The user's biography |
| location | str | The user's location |
| account_summary | str | A summary of the user's account |

## Quotes and Comments Database (quotes_comments_db)

This database stores information about quotes and comments on the bot's posts.

| Column | Type | Description |
|--------|------|-------------|
| post_id | uuid | Primary key, unique identifier for the original post |
| reply_id | uuid | Unique identifier for the reply |
| comment | bool | True if it's a comment, False if it's a quote |
| time_of_reply | timestamp | When the reply was made |
