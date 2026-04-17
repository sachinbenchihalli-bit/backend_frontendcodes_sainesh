import os
import pickle
import logging
from datetime import datetime, timezone
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

def get_oauth_credentials():
    """Get OAuth credentials from token.pickle with automatic refresh"""
    logger.info("=== OAuth Credentials Debug ===")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Files in current directory: {os.listdir('.')}")
    logger.info(f"token.pickle exists: {os.path.exists('token.pickle')}")

    creds = None
    if os.path.exists('token.pickle'):
        logger.info("Loading token.pickle file...")
        try:
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
            logger.info(f"Token loaded successfully. Valid: {creds.valid if creds else 'None'}")
            if creds:
                logger.info(f"Token expired: {creds.expired}")
                logger.info(f"Token scopes: {creds.granted_scopes}")

                # Check refresh token availability
                if hasattr(creds, 'refresh_token') and creds.refresh_token:
                    logger.info("✅ Refresh token available")
                else:
                    logger.warning("❌ No refresh token available - may need re-authentication")

                # Display token expiry information
                if hasattr(creds, 'expiry') and creds.expiry:
                    # Handle timezone-aware vs timezone-naive datetime comparison
                    if creds.expiry.tzinfo is None:
                        now = datetime.now()
                        expiry_time = creds.expiry
                    else:
                        now = datetime.now(timezone.utc)
                        expiry_time = creds.expiry

                    time_remaining = expiry_time - now
                    logger.info(f"Token expires at: {expiry_time}")
                    logger.info(f"Time remaining: {time_remaining}")
                    logger.info(f"Minutes remaining: {time_remaining.total_seconds() / 60:.1f}")

                    # Check if token needs refresh (expired or expires soon)
                    if creds.expired or time_remaining.total_seconds() < 300:  # Less than 5 minutes
                        logger.info("🔄 Token expired or expires soon - attempting refresh...")
                        try:
                            # Attempt to refresh the token
                            creds.refresh(Request())
                            logger.info("✅ Token refreshed successfully!")

                            # Save the refreshed token back to pickle file
                            with open('token.pickle', 'wb') as token:
                                pickle.dump(creds, token)
                            logger.info("💾 Refreshed token saved to token.pickle")

                            # Log new expiry information
                            if hasattr(creds, 'expiry') and creds.expiry:
                                if creds.expiry.tzinfo is None:
                                    new_now = datetime.now()
                                    new_expiry_time = creds.expiry
                                else:
                                    new_now = datetime.now(timezone.utc)
                                    new_expiry_time = creds.expiry

                                new_time_remaining = new_expiry_time - new_now
                                logger.info(f"🆕 New token expires at: {new_expiry_time}")
                                logger.info(f"🆕 New time remaining: {new_time_remaining}")
                                logger.info(f"🆕 New minutes remaining: {new_time_remaining.total_seconds() / 60:.1f}")

                        except Exception as refresh_error:
                            logger.error(f"❌ Failed to refresh token: {refresh_error}")
                            logger.error("This may indicate the refresh token has expired or been revoked")
                            logger.error("You may need to re-authenticate and generate a new token.pickle")
                            return None
                    else:
                        logger.info("✅ Token is valid and not expiring soon")
                else:
                    logger.info("Token expiry information not available")

        except Exception as e:
            logger.error(f"Error loading token.pickle: {e}")
            return None
    else:
        logger.warning("token.pickle file not found")
        return None

    if not creds:
        logger.error("OAuth credentials not found")
        return None

    # Final validation
    if not creds.valid:
        logger.error("❌ Credentials are not valid after processing")
        return None

    logger.info("✅ OAuth credentials loaded and validated successfully")
    return creds
