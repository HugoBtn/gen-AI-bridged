class InternalProjectConnector:
    def fetch_demo_data(self) -> dict:
        return {
            "answer": "Internal Project System trả về tiến độ dự án, milestones và assignee.",
            "records": [
                {"project": "Bridge AI Pilot", "status": "In Progress", "milestone": "PoC review"}
            ],
        }
