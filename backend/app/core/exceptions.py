"""Domain exceptions."""


class JDAnalysisError(Exception):
    """Raised when JD extraction cannot produce a valid structured result."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors) if errors else "JD analysis failed")


class LLMConfigurationError(Exception):
    """Raised when the configured LLM provider cannot be constructed."""
