import psycopg2
import uuid
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class BotDB:
    def __init__(self, db_config: Dict[str, Any]):
        """Initialize connection to the bot database.
        
        Args:
            db_config: Dictionary containing database connection parameters
                (host, port, dbname, user, password)
        """
        self.conn = psycopg2.connect(**db_config)
        self.conn.autocommit = True
        
    def add_post(self, post_id: str, content_gen_prompt: str, content: str, 
                is_reply: bool = False) -> None:
        """Add a post to the bot database.
        
        Args:
            post_id: Unique identifier for the post
            content_gen_prompt: Prompt used to generate the content
            content: The content of the post
            is_reply: Whether the post is a reply to another post
        """
        try:
            post_time = datetime.now()
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO bot_db 
                    (post_id, content_gen_prompt, content, is_reply, post_time)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (post_id, content_gen_prompt, content, is_reply, post_time)
                )
        except Exception as e:
            logger.error(f"Error adding post to bot DB: {e}")
            raise
    
    def get_post(self, post_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a post from the bot database.
        
        Args:
            post_id: Unique identifier for the post
            
        Returns:
            Dictionary containing post information or None if not found
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT post_id, content_gen_prompt, content, is_reply, post_time
                    FROM bot_db
                    WHERE post_id = %s
                    """,
                    (post_id,)
                )
                result = cursor.fetchone()
                
                if result:
                    return {
                        "post_id": result[0],
                        "content_gen_prompt": result[1],
                        "content": result[2],
                        "is_reply": result[3],
                        "post_time": result[4]
                    }
                return None
        except Exception as e:
            logger.error(f"Error retrieving post from bot DB: {e}")
            raise
    
    def get_all_posts(self) -> List[Dict[str, Any]]:
        """Retrieve all posts from the bot database.
        
        Returns:
            List of dictionaries containing post information
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT post_id, content_gen_prompt, content, is_reply, post_time
                    FROM bot_db
                    """
                )
                results = cursor.fetchall()
                
                posts = []
                for result in results:
                    posts.append({
                        "post_id": result[0],
                        "content_gen_prompt": result[1],
                        "content": result[2],
                        "is_reply": result[3],
                        "post_time": result[4]
                    })
                return posts
        except Exception as e:
            logger.error(f"Error retrieving all posts from bot DB: {e}")
            raise
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
