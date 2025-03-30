import psycopg2
import uuid
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class QuotesCommentsDB:
    def __init__(self, db_config: Dict[str, Any]):
        """Initialize connection to the quotes and comments database.
        
        Args:
            db_config: Dictionary containing database connection parameters
                (host, port, dbname, user, password)
        """
        self.conn = psycopg2.connect(**db_config)
        self.conn.autocommit = True
        
    def add_reply(self, post_id: str, reply_id: str, is_comment: bool = True) -> None:
        """Add a reply (comment or quote) to the database.
        
        Args:
            post_id: Unique identifier for the original post
            reply_id: Unique identifier for the reply
            is_comment: True if the reply is a comment, False if it's a quote
        """
        try:
            time_of_reply = datetime.now()
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO quotes_comments_db 
                    (post_id, reply_id, comment, time_of_reply)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (post_id, reply_id, is_comment, time_of_reply)
                )
        except Exception as e:
            logger.error(f"Error adding reply to quotes_comments DB: {e}")
            raise
    
    def get_replies_for_post(self, post_id: str) -> List[Dict[str, Any]]:
        """Retrieve all replies for a specific post.
        
        Args:
            post_id: Unique identifier for the original post
            
        Returns:
            List of dictionaries containing reply information
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT post_id, reply_id, comment, time_of_reply
                    FROM quotes_comments_db
                    WHERE post_id = %s
                    """,
                    (post_id,)
                )
                results = cursor.fetchall()
                
                replies = []
                for result in results:
                    replies.append({
                        "post_id": result[0],
                        "reply_id": result[1],
                        "is_comment": result[2],
                        "time_of_reply": result[3]
                    })
                return replies
        except Exception as e:
            logger.error(f"Error retrieving replies from quotes_comments DB: {e}")
            raise
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
