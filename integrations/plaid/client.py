import plaid
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from core.config import PLAID_CLIENT_ID, PLAID_SECRET, PLAID_ENV

_ENV_MAP = {
    "sandbox": plaid.Environment.Sandbox,
    "production": plaid.Environment.Production,
}


def get_client() -> plaid_api.PlaidApi:
    config = plaid.Configuration(
        host=_ENV_MAP.get(PLAID_ENV, plaid.Environment.Production),
        api_key={"clientId": PLAID_CLIENT_ID, "secret": PLAID_SECRET},
    )
    return plaid_api.PlaidApi(plaid.ApiClient(config))


def create_link_token(user_id: str = "personal-assistant-user") -> str:
    client = get_client()
    request = LinkTokenCreateRequest(
        products=[Products("transactions")],
        client_name="Personal Assistant",
        country_codes=[CountryCode("US")],
        language="en",
        user=LinkTokenCreateRequestUser(client_user_id=user_id),
    )
    response = client.link_token_create(request)
    return response["link_token"]


def exchange_public_token(public_token: str) -> tuple[str, str]:
    """Returns (access_token, item_id)."""
    client = get_client()
    request = ItemPublicTokenExchangeRequest(public_token=public_token)
    response = client.item_public_token_exchange(request)
    return response["access_token"], response["item_id"]


def get_institution_name(item_id: str, access_token: str) -> str:
    client = get_client()
    from plaid.model.item_get_request import ItemGetRequest
    from plaid.model.institutions_get_by_id_request import InstitutionsGetByIdRequest

    item_response = client.item_get(ItemGetRequest(access_token=access_token))
    institution_id = item_response["item"]["institution_id"]

    inst_response = client.institutions_get_by_id(
        InstitutionsGetByIdRequest(
            institution_id=institution_id,
            country_codes=[CountryCode("US")],
        )
    )
    return inst_response["institution"]["name"]


def sync_transactions(access_token: str, cursor: str | None = None) -> tuple[list[dict], list[str], str]:
    """
    Returns (added_transactions, removed_transaction_ids, next_cursor).
    Uses /transactions/sync for incremental updates.
    """
    client = get_client()
    added = []
    removed = []

    kwargs = {"access_token": access_token}
    if cursor:
        kwargs["cursor"] = cursor

    while True:
        request = TransactionsSyncRequest(**kwargs)
        response = client.transactions_sync(request)
        added.extend(response["added"])
        removed.extend([t["transaction_id"] for t in response["removed"]])
        kwargs["cursor"] = response["next_cursor"]
        if not response["has_more"]:
            break

    return added, removed, kwargs["cursor"]
