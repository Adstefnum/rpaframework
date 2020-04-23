from functools import wraps
import itertools
import logging
import os
from netsuitesdk import NetSuiteConnection
from netsuitesdk.internal.client import NetSuiteClient
from netsuitesdk.internal.utils import PaginatedSearch
from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError
from RPA.core.utils import required_env
from RPA.RobotLogListener import RobotLogListener


try:
    BuiltIn().import_library("RPA.RobotLogListener")
except RobotNotRunningError:
    pass


def ns_instance_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if args[0].client is None:
            raise NetsuiteAuthenticationError("Authentication is not completed")
        return f(*args, **kwargs)

    return wrapper


class NetsuiteAuthenticationError(Exception):
    "Error when authenticated Netsuite instance does not exist."


class Netsuite:
    """Library for accessing Netsuite.
    """

    def __init__(self):
        self.client = None
        self.account = None
        self.logger = logging.getLogger(__name__)
        listener = RobotLogListener()
        listener.register_protected_keywords(
            ["RPA.Netsuite.connect", "RPA.Netsuite.login"]
        )

    def connect(
        self,
        account=None,
        consumer_key=None,
        consumer_secret=None,
        token_key=None,
        token_secret=None,
    ):
        """ Connect to Netsuite with credentials from environment
        variables.
        """
        if account is None:
            self.account = required_env("NS_ACCOUNT")
        else:
            self.account = account

        NS_CONSUMER_KEY = required_env("NS_CONSUMER_KEY", consumer_key)
        NS_CONSUMER_SECRET = required_env("NS_CONSUMER_SECRET", consumer_secret)
        NS_TOKEN_KEY = required_env("NS_TOKEN_KEY", token_key)
        NS_TOKEN_SECRET = required_env("NS_TOKEN_SECRET", token_secret)
        self.client = NetSuiteConnection(
            account=self.account,
            consumer_key=NS_CONSUMER_KEY,
            consumer_secret=NS_CONSUMER_SECRET,
            token_key=NS_TOKEN_KEY,
            token_secret=NS_TOKEN_SECRET,
        )

    def login(self, account=None):
        if account is None:
            account = required_env("NS_ACCOUNT", self.account)
        if account is None:
            raise NetsuiteAuthenticationError("Authentication is not completed")
        NS_EMAIL = os.getenv("NS_EMAIL")
        NS_PASSWORD = os.getenv("NS_PASSWORD")
        NS_ROLE = os.getenv("NS_ROLE")
        NS_APPID = os.getenv("NS_APPID")

        if self.client is None:
            self.client = NetSuiteClient(account=account)
        self.client.login(
            email=NS_EMAIL, password=NS_PASSWORD, role=NS_ROLE, application_id=NS_APPID,
        )

    @ns_instance_required
    def netsuite_get(self, record_type=None, internal_id=None, external_id=None):
        """Get all records of given type and internalId and/or externalId.

        :param record_type: type of Netsuite record to get
        :param internal_id: internalId of the type, default None
        :param external_id: external_id of the type, default None
        :raises ValueError: if record_type is not given
        :return: [description]
        """
        if record_type is None:
            raise ValueError("Parameter 'record_type' is required for kw: netsuite_get")
        if internal_id is None and external_id is None:
            raise ValueError(
                "Parameter 'internal_id' or 'external_id' "
                " is required for kw: netsuite_get"
            )
        kwargs = {"recordType": record_type}
        if internal_id is not None:
            kwargs["internalId"] = internal_id
        if external_id is not None:
            kwargs["externalId"] = external_id

        return self.client.get(**kwargs)

    @ns_instance_required
    def netsuite_get_all(self, record_type):
        """Get all records of given type.

        :param record_type: type of Netsuite record to get
        :raises ValueError: if record_type is not given
        :return: [description]
        """
        if record_type is None:
            raise ValueError(
                "Parameter 'record_type' is required for kw: netsuite_get_all"
            )
        return self.client.getAll(recordType=record_type)

    def netsuite_search(
        self, type_name, search_value, operator="contains", page_size=5
    ):
        """Search Netsuite for value from a type. Default operator is
        `contains`.

        :param type_name: search target type name
        :param search_value: what to search for within type
        :param operator: name of the operation, defaults to "contains"
        :param page_size: result items within one page, defaults to 5
        :return: paginated search object
        """
        # pylint: disable=E1101
        record_type_search_field = self.client.SearchStringField(
            searchValue=search_value, operator=operator
        )
        basic_search = self.client.basic_search_factory(
            type_name, recordType=record_type_search_field
        )
        paginated_search = PaginatedSearch(
            client=self.client,
            type_name=type_name,
            basic_search=basic_search,
            pageSize=page_size,
        )
        return paginated_search

    def netsuite_search_all(self, type_name, page_size=20):
        """Search Netsuite for a type results.

        :param type_name: search target type name
        :param page_size: result items within one page, defaults to 5
        :return: paginated search object
        """
        paginated_search = PaginatedSearch(
            client=self.client, type_name=type_name, pageSize=page_size
        )
        return paginated_search

    @ns_instance_required
    def get_accounts(self, count=100, account_type=None):
        """Get Accounts of any type or specified type.

        :param count: number of Accounts to return, defaults to 100
        :param account_type: if None returns all account types, example. "_expense",
            defaults to None
        :return: accounts
        """
        all_accounts = list(
            itertools.islice(self.client.accounts.get_all_generator(), count)
        )
        if account_type is None:
            return all_accounts
        return [a for a in all_accounts if a["acctType"] == account_type]

    @ns_instance_required
    def get_currency(self, currency_id):
        """Get all a Netsuite Currency by its ID

        :param currency_id: ID of the currency to get
        :return: currency
        """
        return self.client.currencies.get(internalId=currency_id)

    @ns_instance_required
    def get_currencies(self):
        """Get all Netsuite Currencies

        :return: currencies
        """
        return self.client.currencies.get_all()

    @ns_instance_required
    def get_locations(self):
        """Get all Netsuite Locations

        :return: locations
        """
        return self.client.locations.get_all()

    @ns_instance_required
    def get_departments(self):
        """Get all Netsuite Departments

        :return: departments
        """
        return self.client.departments.get_all()

    @ns_instance_required
    def get_classifications(self):
        """Get all Netsuite Classifications

        :return: classifications
        """
        return self.client.classifications.get_all()

    @ns_instance_required
    def get_vendors(self, count=10):
        """Get list of vendors

        :param count: number of vendors to return, defaults to 10
        :return: list of vendors
        """
        return list(itertools.islice(self.client.vendors.get_all_generator(), count))

    @ns_instance_required
    def get_vendor_bills(self, count=10):
        """Get list of vendor bills

        :param count: number of vendor bills to return, defaults to 10
        :return: list of vendor bills
        """
        return list(
            itertools.islice(self.client.vendor_bills.get_all_generator(), count)
        )
