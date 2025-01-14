import logging

from .core import *
from .eval import *
from .main import *
from .pipes import *
from .prompts import *

logger = logging.getLogger("r2r")
logger.setLevel(logging.INFO)

# Create a console handler and set the level to info
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# Create a formatter and set it for the handler
formatter = logging.Formatter(
    "%(name)s - %(levelname)s - %(message)s - %(asctime)s"
)
ch.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(ch)

# Optional: Prevent propagation to the root logger
logger.propagate = False

__all__ = [
    "LoggingConfig",
    "LocalPipeLoggingProvider",
    "PostgresLoggingConfig",
    "PostgresPipeLoggingProvider",
    "RedisLoggingConfig",
    "RedisPipeLoggingProvider",
    "PipeLoggingConnectionSingleton",
    "VectorEntry",
    "VectorType",
    "Vector",
    "SearchRequest",
    "SearchResult",
    "AsyncPipe",
    "PipeRunInfo",
    "PipeType",
    "AsyncState",
    "Prompt",
    "DataType",
    "DocumentType",
    "Document",
    "Extraction",
    "ExtractionType",
    "Fragment",
    "FragmentType",
    # Parsers
    "AsyncParser",
    "CSVParser",
    "DOCXParser",
    "HTMLParser",
    "JSONParser",
    "MarkdownParser",
    "PDFParser",
    "PPTParser",
    "TextParser",
    "XLSXParser",
    "Pipeline",
    # Providers
    "EmbeddingConfig",
    "EmbeddingProvider",
    "EvalConfig",
    "EvalProvider",
    "LLMEvalProvider",
    "PromptConfig",
    "PromptProvider",
    "GenerationConfig",
    "LLMChatCompletion",
    "LLMChatCompletionChunk",
    "LLMConfig",
    "LLMProvider",
    "VectorDBConfig",
    "VectorDBProvider",
    "R2RConfig",
    "TextSplitter",
    "RecursiveCharacterTextSplitter",
    "generate_run_id",
    "generate_id_from_label",
    "R2RApp",
    # Pipes
    "R2REmbeddingPipe",
    "R2REvalPipe",
    "R2RDocumentParsingPipe",
    "R2RQueryTransformPipe",
    "R2RRAGPipe",
    "R2RStreamingRAGPipe",
    "R2RVectorSearchPipe",
    "R2RVectorStoragePipe",
    "R2RPromptProvider",
]
