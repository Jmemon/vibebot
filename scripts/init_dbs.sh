#!/bin/bash
set -e

# Database connection parameters
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_USER=${DB_USER:-postgres}
DB_PASSWORD=${DB_PASSWORD:-postgres}
DB_NAME=${DB_NAME:-vibebot}

# Create the database if it doesn't exist
echo "Creating database $DB_NAME if it doesn't exist..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1 || PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -c "CREATE DATABASE $DB_NAME"

# Create bot_db table
echo "Creating bot_db table..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
CREATE TABLE IF NOT EXISTS bot_db (
    post_id UUID PRIMARY KEY,
    content_gen_prompt TEXT,
    content TEXT,
    is_reply BOOLEAN,
    post_time TIMESTAMP
);"

# Create engagement_db table
echo "Creating engagement_db table..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
CREATE TABLE IF NOT EXISTS engagement_db (
    post_id UUID PRIMARY KEY,
    retrieval_time TIMESTAMP,
    likes INTEGER,
    retweets INTEGER,
    quotes_filepath TEXT,
    comments_filepath TEXT
);"

# Create community_db table
echo "Creating community_db table..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
CREATE TABLE IF NOT EXISTS community_db (
    user_id UUID PRIMARY KEY,
    handle TEXT,
    followers INTEGER,
    following INTEGER,
    bio TEXT,
    location TEXT,
    account_summary TEXT
);"

# Create quotes_comments_db table
echo "Creating quotes_comments_db table..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
CREATE TABLE IF NOT EXISTS quotes_comments_db (
    post_id UUID PRIMARY KEY,
    reply_id UUID,
    comment BOOLEAN,
    time_of_reply TIMESTAMP
);"

echo "Database initialization complete!"
