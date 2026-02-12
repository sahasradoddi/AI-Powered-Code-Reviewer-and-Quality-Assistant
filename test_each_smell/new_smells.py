# Example module to trigger multiple smells:
# - exception_swallowing
# - unreachable_code
# - feature_envy
# - many_local_variables

class Order:
    def __init__(self, items, user, status):
        self.items = items
        self.user = user
        self.status = status


class OrderProcessor:
    def __init__(self, order: Order):
        self.order = order
        self.log = []

    def process_order(self, discount_code, tax_rate, shipping_cost, region, priority_flag,
                      extra_option_1, extra_option_2, extra_option_3, extra_option_4):
        """
        Intentionally messy function to trigger:
        - many_local_variables
        - unreachable_code (inside nested blocks)
        - exception_swallowing in a helper method
        - feature_envy via heavy use of self.order.*
        """

        # MANY LOCAL VARIABLES (more than 8)
        total_price = 0
        taxable_amount = 0
        shipping_fee = shipping_cost
        discount_value = 0
        final_amount = 0
        currency = "USD"
        message = ""
        audit_entry = {}
        retry_count = 0
        max_retries = 3

        # FEATURE ENVY: mostly touching self.order, not self
        if self.order.status == "NEW":
            for item in self.order.items:
                taxable_amount += item.get("price", 0) * item.get("qty", 1)

            if discount_code and self.order.user and self.order.user.get("is_vip"):
                discount_value = taxable_amount * 0.15
            elif discount_code:
                discount_value = taxable_amount * 0.05

            total_price = taxable_amount - discount_value
            total_price += shipping_fee

            # Unnecessary complexity to keep locals in use
            if region == "EU":
                tax_rate = 0.21
            elif region == "IN":
                tax_rate = 0.18
            else:
                tax_rate = tax_rate or 0.20

            tax_amount = total_price * tax_rate
            final_amount = total_price + tax_amount

        else:
            message = f"Order status '{self.order.status}' not supported"
            final_amount = 0

        # UNREACHABLE CODE example inside a loop block
        for _ in range(2):
            if final_amount > 0:
                return final_amount  # terminates the loop block

            # This line is unreachable in that block (after return)
            message = "This assignment is unreachable"

        # More UNREACHABLE CODE directly in function body
        return final_amount
        message = "This line is also unreachable"
        audit_entry["note"] = "Will never be set"

    def _unsafe_log_error(self):
        """
        Helper method to demonstrate exception_swallowing with
        bare except and no meaningful handling.
        """
        try:
            # Simulate some logging action that may fail
            raise ValueError("Simulated logging failure")
        except:
            # EXCEPTION SWALLOWING: bare except with no handling
            pass

    def run(self):
        try:
            amount = self.process_order(
                discount_code="WELCOME",
                tax_rate=0.2,
                shipping_cost=10.0,
                region="EU",
                priority_flag=True,
                extra_option_1=True,
                extra_option_2=False,
                extra_option_3=None,
                extra_option_4="EXTRA",
            )
            self.log.append(f"Order processed for {self.order.user['name']}, total={amount}")
        except Exception:
            # Swallow again in a broad way (depending on your rules this may also be flagged)
            self._unsafe_log_error()
