class NoSourcesFound(Exception):
    """Raised when ingestion has no supported source data to index."""


class RetrievalUnavailable(Exception):
    """Raised when evidence retrieval cannot be completed."""


class AnswerGenerationUnavailable(Exception):
    """Raised when the configured answer model cannot generate a response."""