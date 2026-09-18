"""Client for the Northwind payments API."""

from payments.client import PaymentsClient
from payments.resources.charges import Charges
from payments.resources.customers import Customers
from payments.resources.disputes import Disputes
from payments.resources.invoices import Invoices
from payments.resources.payouts import Payouts
from payments.resources.refunds import Refunds

__version__ = "0.1.0"


class Northwind:
    """Facade exposing every resource off one configured client."""

    def __init__(self, api_key, **kwargs):
        self.client = PaymentsClient(api_key, **kwargs)
        self.charges = Charges(self.client)
        self.refunds = Refunds(self.client)
        self.customers = Customers(self.client)
        self.payouts = Payouts(self.client)
        self.disputes = Disputes(self.client)
        self.invoices = Invoices(self.client)
