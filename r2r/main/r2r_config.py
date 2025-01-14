import json
import logging
import os
from typing import Any

from ..core.abstractions.document import DocumentType
from ..core.pipes.pipe_logging import LoggingConfig
from ..core.providers.embedding_provider import EmbeddingConfig
from ..core.providers.eval_provider import EvalConfig
from ..core.providers.llm_provider import LLMConfig
from ..core.providers.prompt_provider import PromptConfig
from ..core.providers.vector_db_provider import VectorDBConfig

logger = logging.getLogger(__name__)


class R2RConfig:
    REQUIRED_KEYS: dict[str, list] = {
        "app": [
            "max_file_size_in_mb",
        ],
        "embedding": [
            "provider",
            "search_model",
            "search_dimension",
            "batch_size",
            "text_splitter",
        ],
        "eval": [
            "llm",
            "sampling_fraction",
        ],
        "ingestion": ["selected_parsers"],
        "completions": ["provider"],
        "logging": ["provider", "log_table"],
        "prompt": ["provider"],
        "vector_database": ["provider", "collection_name"],
    }
    app: dict[str, Any]
    embedding: EmbeddingConfig
    completions: LLMConfig
    logging: LoggingConfig
    prompt: PromptConfig
    vector_database: VectorDBConfig

    def __init__(self, config_data: dict[str, Any]):
        # Load the default configuration
        default_config = self.load_default_config()

        # Override the default configuration with the passed configuration
        for key in config_data:
            if key in default_config:
                default_config[key].update(config_data[key])
            else:
                default_config[key] = config_data[key]

        # Validate and set the configuration
        for section, keys in R2RConfig.REQUIRED_KEYS.items():
            self._validate_config_section(default_config, section, keys)
            setattr(self, section, default_config[section])

        self.app = self.app  # for type hinting
        self.ingestion = self.ingestion  # for type hinting
        self.ingestion["selected_parsers"] = {
            DocumentType(k): v
            for k, v in self.ingestion["selected_parsers"].items()
        }
        self.embedding = EmbeddingConfig.create(**self.embedding)
        eval_llm = self.eval.pop("llm")
        self.eval = EvalConfig.create(
            **self.eval, llm=LLMConfig.create(**eval_llm)
        )
        self.completions = LLMConfig.create(**self.completions)
        self.logging = LoggingConfig.create(**self.logging)
        self.prompt = PromptConfig.create(**self.prompt)
        self.vector_database = VectorDBConfig.create(**self.vector_database)

    def _validate_config_section(
        self, config_data: dict[str, Any], section: str, keys: list
    ):
        if section not in config_data:
            raise ValueError(f"Missing '{section}' section in config")
        if not all(key in config_data[section] for key in keys):
            raise ValueError(f"Missing required keys in '{section}' config")

    @classmethod
    def from_json(cls, config_path: str = None) -> "R2RConfig":
        if config_path is None:
            # Get the root directory of the project
            file_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(file_dir, "..", "..", "config.json")

        logger.info(f"Loading configuration from {config_path}")

        # Load configuration from JSON file
        with open(config_path) as f:
            config_data = json.load(f)

        return cls(config_data)

    # TODO - How to type 'redis.Redis' without introducing dependency on 'redis' package?
    def save_to_redis(self, redis_client: Any, key: str):
        config_data = {
            section: getattr(self, section)
            for section in R2RConfig.REQUIRED_KEYS.keys()
        }
        redis_client.set(f"R2RConfig:{key}", json.dumps(config_data))

    @classmethod
    def load_from_redis(cls, redis_client: Any, key: str) -> "R2RConfig":
        config_data = redis_client.get(f"R2RConfig:{key}")
        if config_data is None:
            raise ValueError(
                f"Configuration not found in Redis with key '{key}'"
            )
        return cls(json.loads(config_data))

    @classmethod
    def load_default_config(cls) -> dict:
        # Get the root directory of the project
        file_dir = os.path.dirname(os.path.abspath(__file__))
        default_config_path = os.path.join(file_dir, "..", "..", "config.json")
        # Load default configuration from JSON file
        with open(default_config_path) as f:
            return json.load(f)
