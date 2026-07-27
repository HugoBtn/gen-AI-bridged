class SalesforceConnector:
    def fetch_demo_data(self) -> dict:
        return {
            "answer": "Salesforce trả về thông tin khách hàng, account, và liên hệ liên quan.",
            "records": [
                {"account": "ABC Corp", "owner": "Alice", "stage": "Negotiation"}
            ],
        }
