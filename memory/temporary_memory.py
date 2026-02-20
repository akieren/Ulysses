class TemporaryMemory:
    def __init__(self, max_history: int = 5):
        self.max_history = max_history
        self.reset()

    def reset(self):
        self.pending_intent = None
        self.parameters = {}
        self.conversation_history = []

    def add_to_history(self, role: str, text: str):
        self.conversation_history.append({"role": role, "text": text})
        if len(self.conversation_history) > self.max_history:
            self.conversation_history.pop(0)

    def get_history_for_prompt(self) -> str:
        return "\n".join(
            [
                f"{m['role'].capitalize()}: {m['text']}"
                for m in self.conversation_history
            ]
        )

    def update_parameters(self, new_params: dict):
        if isinstance(new_params, dict):
            self.parameters.update(new_params)
