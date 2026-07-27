try:
    from app.connectors.salesforce import SalesforceConnector
    from app.connectors.sansan import SansanConnector
    from app.connectors.internal import InternalProjectConnector
except ModuleNotFoundError:
    from connectors.salesforce import SalesforceConnector
    from connectors.sansan import SansanConnector
    from connectors.internal import InternalProjectConnector


class Orchestrator:
    def __init__(self) -> None:
        self.salesforce = SalesforceConnector()
        self.sansan = SansanConnector()
        self.internal = InternalProjectConnector()

    def handle(self, question: str) -> dict:
        # This is a stub PoC. In production, use LLM intent routing.
        # For now, the demo routes by keyword heuristics.
        lowered = question.lower()

        if "salesforce" in lowered or "khách hàng" in lowered or "contact" in lowered:
            data = self.salesforce.fetch_demo_data()
            source = "Salesforce"
        elif "sansan" in lowered or "đối tác" in lowered or "company" in lowered:
            data = self.sansan.fetch_demo_data()
            source = "Sansan"
        elif "dự án" in lowered or "project" in lowered:
            data = self.internal.fetch_demo_data()
            source = "Internal Project System"
        else:
            data = {
                "answer": "Câu hỏi chưa rõ intent. Vui lòng cung cấp thêm context hoặc tên hệ thống dữ liệu cần truy vấn.",
                "source": "router",
            }
            source = "Router"

        return {
            "question": question,
            "source": source,
            "answer": data.get("answer") or data,
            "details": data,
        }
