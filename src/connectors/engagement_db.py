import psycopg2
import uuid
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class EngagementDB:
    def __init__(self, db_config: Dict[str, Any]):
        """Initialize connection to the engagement database.
        
        Args:
            db_config: Dictionary containing database connection parameters
                (host, port, dbname, user, password)
        """
        self.conn = psycopg2.connect(**db_config)
        self.conn.autocommit = True
        
    def add_engagement(self, post_id: str, likes: int, retweets: int, 
                      quotes_filepath: str = None, comments_filepath: str = None) -> None:
        """Add engagement metrics for a post.
        
        Args:
            post_id: Unique identifier for the post
            likes: Number of likes
            retweets: Number of retweets
            quotes_filepath: Path to file containing quotes
            comments_filepath: Path to file containing comments
        """
        try:
            retrieval_time = datetime.now()
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO engagement_db 
                    (post_id, retrieval_time, likes, retweets, quotes_filepath, comments_filepath)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (post_id) DO UPDATE SET
                    retrieval_time = EXCLUDED.retrieval_time,
                    likes = EXCLUDED.likes,
                    retweets = EXCLUDED.retweets,
                    quotes_filepath = EXCLUDED.quotes_filepath,
                    comments_filepath = EXCLUDED.comments_filepath
                    """,
                    (post_id, retrieval_time, likes, retweets, quotes_filepath, comments_filepath)
                )
        except Exception as e:
            logger.error(f"Error adding engagement metrics: {e}")
            raise
    
    def get_engagement(self, post_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve engagement metrics for a post.
        
        Args:
            post_id: Unique identifier for the post
            
        Returns:
            Dictionary containing engagement metrics or None if not found
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT post_id, retrieval_time, likes, retweets, quotes_filepath, comments_filepath
                    FROM engagement_db
                    WHERE post_id = %s
                    """,
                    (post_id,)
                )
                result = cursor.fetchone()
                
                if result:
                    return {
                        "post_id": result[0],
                        "retrieval_time": result[1],
                        "likes": result[2],
                        "retweets": result[3],
                        "quotes_filepath": result[4],
                        "comments_filepath": result[5]
                    }
                return None
        except Exception as e:
            logger.error(f"Error retrieving engagement metrics: {e}")
            raise
    
    def get_all_engagements(self) -> List[Dict[str, Any]]:
        """Retrieve all engagement metrics.
        
        Returns:
            List of dictionaries containing engagement metrics
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT post_id, retrieval_time, likes, retweets, quotes_filepath, comments_filepath
                    FROM engagement_db
                    """
                )
                results = cursor.fetchall()
                
                engagements = []
                for result in results:
                    engagements.append({
                        "post_id": result[0],
                        "retrieval_time": result[1],
                        "likes": result[2],
                        "retweets": result[3],
                        "quotes_filepath": result[4],
                        "comments_filepath": result[5]
                    })
                return engagements
        except Exception as e:
            logger.error(f"Error retrieving all engagement metrics: {e}")
            raise
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
