"""Google Ads API Client service."""

import logging
from datetime import datetime, timedelta, UTC
from typing import Any

from google.ads.googleads.client import GoogleAdsClient as GoogleAdsAPIClient
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from app.core.config import settings

logger = logging.getLogger(__name__)


class GoogleAdsClient:
    """Client for interacting with Google Ads API."""

    def __init__(self):
        """Initialize Google Ads client."""
        self.developer_token = settings.google_ads_developer_token
        self.client_id = settings.google_client_id
        self.client_secret = settings.google_client_secret
        self.login_customer_id = settings.google_ads_login_customer_id

    async def exchange_code_for_tokens(
        self, code: str, redirect_uri: str
    ) -> dict[str, Any]:
        """
        Exchange OAuth authorization code for access and refresh tokens.

        Args:
            code: OAuth authorization code from callback
            redirect_uri: Redirect URI used in OAuth flow

        Returns:
            Dictionary containing:
                - access_token: Access token for API calls
                - refresh_token: Refresh token for getting new access tokens
                - expires_at: DateTime when access token expires
        """
        try:
            # Create OAuth flow
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [redirect_uri],
                    }
                },
                scopes=["https://www.googleapis.com/auth/adwords"],
            )
            flow.redirect_uri = redirect_uri

            # Exchange code for tokens
            flow.fetch_token(code=code)
            credentials = flow.credentials

            # Get expiration time from credentials
            # Google OAuth access tokens expire in 1 hour, but since we have a refresh token,
            # we set a longer expiration time (60 days) to avoid unnecessary warnings
            # The system will automatically refresh the access token when needed
            if credentials.refresh_token:
                # Set expiration to 60 days from now since we have a refresh token
                expires_at = datetime.now(UTC) + timedelta(days=60)
            elif credentials.expiry:
                expires_at = credentials.expiry
            else:
                # Fallback to 1 hour from now if no refresh token and no expiry
                expires_at = datetime.now(UTC) + timedelta(seconds=3600)

            return {
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "expires_at": expires_at,
            }

        except Exception as e:
            logger.error(f"Failed to exchange OAuth code: {str(e)}")
            raise ValueError(f"OAuth token exchange failed: {str(e)}")

    async def get_accessible_accounts(
        self, access_token: str, refresh_token: str
    ) -> list[dict[str, Any]]:
        """
        Get list of Google Ads accounts accessible by the user.

        Args:
            access_token: OAuth access token
            refresh_token: OAuth refresh token

        Returns:
            List of account dictionaries with id and name
        """
        try:
            # Create credentials
            credentials = Credentials(
                token=access_token,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=["https://www.googleapis.com/auth/adwords"],
            )

            # Initialize Google Ads API client without login_customer_id
            # We'll query each account directly without a manager context first
            client = GoogleAdsAPIClient(
                credentials=credentials,
                developer_token=self.developer_token,
                login_customer_id=None,  # Don't set a fixed login_customer_id
            )

            # Get CustomerService
            customer_service = client.get_service("CustomerService")

            # List accessible customers
            accessible_customers = customer_service.list_accessible_customers()

            if not accessible_customers.resource_names:
                return []

            # Format response
            accounts = []
            ga_service = client.get_service("GoogleAdsService")

            for resource_name in accessible_customers.resource_names:
                # Extract customer ID from resource name (format: customers/1234567890)
                customer_id = resource_name.split("/")[-1]

                try:
                    # Query customer details
                    query = f"""
                        SELECT
                            customer.id,
                            customer.descriptive_name,
                            customer.currency_code,
                            customer.time_zone,
                            customer.manager
                        FROM customer
                        WHERE customer.id = {customer_id}
                    """

                    response = ga_service.search(customer_id=customer_id, query=query)

                    for row in response:
                        account_info = {
                            "id": str(row.customer.id),
                            "name": row.customer.descriptive_name or f"Account {row.customer.id}",
                            "currency": row.customer.currency_code,
                            "timezone": row.customer.time_zone,
                            "is_manager": row.customer.manager,
                        }
                        accounts.append(account_info)

                        # If this is a manager account, also fetch its client accounts
                        if row.customer.manager:
                            try:
                                client_accounts = await self._get_client_accounts(
                                    client, customer_id, credentials
                                )
                                accounts.extend(client_accounts)
                            except Exception as client_error:
                                logger.warning(
                                    f"Failed to get client accounts for manager {customer_id}: {str(client_error)}"
                                )
                except Exception as account_error:
                    logger.warning(f"Failed to get details for customer {customer_id}: {str(account_error)}")
                    # Add basic info even if detailed query fails
                    accounts.append({
                        "id": customer_id,
                        "name": f"Account {customer_id}",
                        "currency": "USD",
                        "timezone": "UTC",
                        "is_manager": False,
                    })

            return accounts

        except Exception as e:
            logger.error(f"Failed to get Google Ads accounts: {str(e)}")
            raise ValueError(f"Failed to fetch Google Ads accounts: {str(e)}")

    async def _get_client_accounts(
        self, client: GoogleAdsAPIClient, manager_customer_id: str, credentials: Credentials
    ) -> list[dict[str, Any]]:
        """
        Get client accounts managed by a manager account.

        Args:
            client: Initialized Google Ads API client
            manager_customer_id: Manager account ID
            credentials: OAuth credentials

        Returns:
            List of client account dictionaries
        """
        client_accounts = []

        try:
            ga_service = client.get_service("GoogleAdsService")

            # Query for client accounts under this manager
            query = """
                SELECT
                    customer_client.id,
                    customer_client.descriptive_name,
                    customer_client.currency_code,
                    customer_client.time_zone,
                    customer_client.manager,
                    customer_client.status
                FROM customer_client
                WHERE customer_client.status = 'ENABLED'
            """

            response = ga_service.search(customer_id=manager_customer_id, query=query)

            for row in response:
                # Only include enabled non-manager client accounts
                if not row.customer_client.manager:
                    client_accounts.append({
                        "id": str(row.customer_client.id),
                        "name": row.customer_client.descriptive_name or f"Account {row.customer_client.id}",
                        "currency": row.customer_client.currency_code,
                        "timezone": row.customer_client.time_zone,
                        "is_manager": False,
                        "manager_id": manager_customer_id,
                    })

        except Exception as e:
            logger.error(f"Failed to get client accounts for manager {manager_customer_id}: {str(e)}")

        return client_accounts

    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """
        Refresh an expired access token.

        Args:
            refresh_token: OAuth refresh token

        Returns:
            Dictionary containing new access_token and expires_at
        """
        try:
            credentials = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=["https://www.googleapis.com/auth/adwords"],
            )

            # Refresh the token
            credentials.refresh(Request())

            # Calculate expiration time
            expires_at = datetime.now(UTC) + timedelta(
                seconds=credentials.expiry_delta or 3600
            )

            return {
                "access_token": credentials.token,
                "expires_at": expires_at,
            }

        except Exception as e:
            logger.error(f"Failed to refresh access token: {str(e)}")
            raise ValueError(f"Token refresh failed: {str(e)}")


# Singleton instance
_google_ads_client: GoogleAdsClient | None = None


def get_google_ads_client() -> GoogleAdsClient:
    """Get or create Google Ads client instance."""
    global _google_ads_client
    if _google_ads_client is None:
        _google_ads_client = GoogleAdsClient()
    return _google_ads_client
