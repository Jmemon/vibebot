import psycopg2
import uuid
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class CommunityDB:
    def __init__(self, db_config: Dict[str, Any]):
        """Initialize connection to the community database.
        
        Args:
            db_config: Dictionary containing database connection parameters
                (host, port, dbname, user, password)
        """
        self.conn = psycopg2.connect(**db_config)
        self.conn.autocommit = True
        
    def add_user(self, user_id: str, handle: str, followers: int, following: int, 
                 bio: str, location: str, account_summary: str) -> None:
        """Add a user to the community database.
        
        Args:
            user_id: Unique identifier for the user
            handle: User's handle/username
            followers: Number of followers
            following: Number of accounts the user is following
            bio: User's biography
            location: User's location
            account_summary: Summary of the user's account
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO community_db 
                    (user_id, handle, followers, following, bio, location, account_summary)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET
                    handle = EXCLUDED.handle,
                    followers = EXCLUDED.followers,
                    following = EXCLUDED.following,
                    bio = EXCLUDED.bio,
                    location = EXCLUDED.location,
                    account_summary = EXCLUDED.account_summary
                    """,
                    (user_id, handle, followers, following, bio, location, account_summary)
                )
        except Exception as e:
            logger.error(f"Error adding user to community DB: {e}")
            raise
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a user from the community database.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            Dictionary containing user information or None if not found
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT user_id, handle, followers, following, bio, location, account_summary
                    FROM community_db
                    WHERE user_id = %s
                    """,
                    (user_id,)
                )
                result = cursor.fetchone()
                
                if result:
                    return {
                        "user_id": result[0],
                        "handle": result[1],
                        "followers": result[2],
                        "following": result[3],
                        "bio": result[4],
                        "location": result[5],
                        "account_summary": result[6]
                    }
                return None
        except Exception as e:
            logger.error(f"Error retrieving user from community DB: {e}")
            raise
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Retrieve all users from the community database.
        
        Returns:
            List of dictionaries containing user information
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT user_id, handle, followers, following, bio, location, account_summary
                    FROM community_db
                    """
                )
                results = cursor.fetchall()
                
                users = []
                for result in results:
                    users.append({
                        "user_id": result[0],
                        "handle": result[1],
                        "followers": result[2],
                        "following": result[3],
                        "bio": result[4],
                        "location": result[5],
                        "account_summary": result[6]
                    })
                return users
        except Exception as e:
            logger.error(f"Error retrieving all users from community DB: {e}")
            raise
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
