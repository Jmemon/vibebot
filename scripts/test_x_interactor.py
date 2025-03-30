#!/usr/bin/env python3

import os
import sys
import logging
from pathlib import Path

# Add the src directory to the path so we can import modules
sys.path.append(str(Path(__file__).parent.parent))

from src.x_interactor import XInteractor

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """
    Test script to instantiate XInteractor and test get_user_by_username method.
    """
    try:
        # Instantiate XInteractor with specific user_id
        x_interactor = XInteractor(user_id="1490171550")
        
        # Test get_user_by_username
        username = "john_memon"
        logger.info(f"Looking up user: {username}")
        
        user_data = x_interactor.get_user_by_username(username)
        
        # Print the return value
        print(f"\nUser data for {username}:")
        print(user_data)
        
    except Exception as e:
        logger.error(f"Error in test script: {e}")
        raise

if __name__ == "__main__":
    main()
