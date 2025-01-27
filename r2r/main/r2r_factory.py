import logging
from typing import Any, Optional

from r2r.core import (
    EmbeddingConfig,
    EmbeddingProvider,
    EvalPipeline,
    EvalProvider,
    IngestionPipeline,
    LLMConfig,
    LLMProvider,
    PipeLoggingConnectionSingleton,
    PromptProvider,
    RAGPipeline,
    SearchPipeline,
    VectorDBConfig,
    VectorDBProvider,
)

from .r2r_abstractions import R2RPipelines, R2RPipes, R2RProviders
from .r2r_config import R2RConfig

logger = logging.getLogger(__name__)


class R2RProviderFactory:
    def __init__(self, config: R2RConfig):
        self.config = config

    def create_vector_db_provider(
        self, vector_db_config: VectorDBConfig, *args, **kwargs
    ) -> VectorDBProvider:
        vector_db_provider: Optional[VectorDBProvider] = None
        if vector_db_config.provider == "qdrant":
            from r2r.vector_dbs import QdrantDB

            vector_db_provider = QdrantDB(vector_db_config)
        elif vector_db_config.provider == "pgvector":
            from r2r.vector_dbs import PGVectorDB

            vector_db_provider = PGVectorDB(vector_db_config)
        elif vector_db_config.provider == "local":
            from r2r.vector_dbs import R2RLocalVectorDB

            vector_db_provider = R2RLocalVectorDB(vector_db_config)
        else:
            raise ValueError(
                f"Vector database provider {vector_db_config.provider} not supported"
            )
        if not vector_db_provider:
            raise ValueError("Vector database provider not found")

        if not self.config.embedding.search_dimension:
            raise ValueError("Search dimension not found in embedding config")

        vector_db_provider.initialize_collection(
            self.config.embedding.search_dimension
        )
        return vector_db_provider

    def create_embedding_provider(
        self, embedding: EmbeddingConfig, *args, **kwargs
    ) -> EmbeddingProvider:
        embedding_provider: Optional[EmbeddingProvider] = None

        if embedding.provider == "openai":
            from r2r.embeddings import OpenAIEmbeddingProvider

            embedding_provider = OpenAIEmbeddingProvider(embedding)
        elif embedding.provider == "sentence-transformers":
            from r2r.embeddings import SentenceTransformerEmbeddingProvider

            embedding_provider = SentenceTransformerEmbeddingProvider(
                embedding
            )
        elif embedding.provider == "dummy":
            from r2r.embeddings import DummyEmbeddingProvider

            embedding_provider = DummyEmbeddingProvider(embedding)
        else:
            raise ValueError(
                f"Embedding provider {embedding.provider} not supported"
            )
        if not embedding_provider:
            raise ValueError("Embedding provider not found")

        return embedding_provider

    def create_eval_provider(
        self, eval_config, prompt_provider, *args, **kwargs
    ) -> EvalProvider:
        if eval_config.provider == "local":
            from r2r.eval import LLMEvalProvider

            llm_provider = self.create_llm_provider(eval_config.llm)
            eval_provider = LLMEvalProvider(
                eval_config,
                llm_provider=llm_provider,
                prompt_provider=prompt_provider,
            )
        else:
            raise ValueError(
                f"Eval provider {eval_config.provider} not supported."
            )

        return eval_provider

    def create_llm_provider(
        self, llm_config: LLMConfig, *args, **kwargs
    ) -> LLMProvider:
        llm_provider: Optional[LLMProvider] = None
        if llm_config.provider == "openai":
            from r2r.llms import OpenAILLM

            llm_provider = OpenAILLM(llm_config)
        elif llm_config.provider == "litellm":
            from r2r.llms import LiteLLM

            llm_provider = LiteLLM(llm_config)
        elif llm_config.provider == "llama-cpp":
            from r2r.llms import LlamaCPP, LlamaCppConfig

            config_dict = llm_config.dict()
            extra_args = config_dict.pop("extra_args")

            llm_provider = LlamaCPP(
                LlamaCppConfig(**{**config_dict, **extra_args})
            )
        else:
            raise ValueError(
                f"Language model provider {llm_config.provider} not supported"
            )
        if not llm_provider:
            raise ValueError("Language model provider not found")
        return llm_provider

    def create_prompt_provider(
        self, prompt_config, *args, **kwargs
    ) -> PromptProvider:
        prompt_provider = None
        if prompt_config.provider == "local":
            from r2r.prompts import R2RPromptProvider

            prompt_provider = R2RPromptProvider()
        else:
            raise ValueError(
                f"Prompt provider {prompt_config.provider} not supported"
            )
        return prompt_provider

    def create_providers(self) -> R2RProviders:
        llm_provider = self.create_llm_provider(self.config.completions)
        prompt_provider = self.create_prompt_provider(self.config.prompt)
        return R2RProviders(
            vector_db=self.create_vector_db_provider(
                self.config.vector_database
            ),
            embedding=self.create_embedding_provider(self.config.embedding),
            eval=self.create_eval_provider(
                self.config.eval, prompt_provider=prompt_provider
            ),
            llm=llm_provider,
            prompt=prompt_provider,
        )


class R2RPipeFactory:
    def __init__(self, config: R2RConfig, providers: R2RProviders):
        self.config = config
        self.providers = providers

    def create_pipes(self) -> R2RPipes:
        return R2RPipes(
            parsing_pipe=self.create_parsing_pipe(
                self.config.ingestion.get("selected_parsers")
            ),
            embedding_pipe=self.create_embedding_pipe(),
            vector_storage_pipe=self.create_vector_storage_pipe(),
            search_pipe=self.create_search_pipe(),
            rag_pipe=self.create_rag_pipe(),
            streaming_rag_pipe=self.create_rag_pipe(streaming=True),
            eval_pipe=self.create_eval_pipe(),
        )

    def create_parsing_pipe(
        self, selected_parsers: Optional[dict] = None
    ) -> Any:
        from r2r.pipes import R2RDocumentParsingPipe

        return R2RDocumentParsingPipe(selected_parsers=selected_parsers or {})

    def create_embedding_pipe(self) -> Any:
        from r2r.core import RecursiveCharacterTextSplitter
        from r2r.pipes import R2REmbeddingPipe

        text_splitter_config = self.config.embedding.extra_fields.get(
            "text_splitter"
        )
        if not text_splitter_config:
            raise ValueError(
                "Text splitter config not found in embedding config"
            )

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=text_splitter_config["chunk_size"],
            chunk_overlap=text_splitter_config["chunk_overlap"],
            length_function=len,
            is_separator_regex=False,
        )
        return R2REmbeddingPipe(
            embedding_provider=self.providers.embedding,
            vector_db_provider=self.providers.vector_db,
            text_splitter=text_splitter,
            embedding_batch_size=self.config.embedding.batch_size,
        )

    def create_vector_storage_pipe(self) -> Any:
        from r2r.pipes import R2RVectorStoragePipe

        return R2RVectorStoragePipe(
            vector_db_provider=self.providers.vector_db
        )

    def create_search_pipe(self) -> Any:
        from r2r.pipes import R2RVectorSearchPipe

        return R2RVectorSearchPipe(
            vector_db_provider=self.providers.vector_db,
            embedding_provider=self.providers.embedding,
        )

    def create_rag_pipe(self, streaming: bool = False) -> Any:
        if streaming:
            from r2r.pipes import R2RStreamingRAGPipe

            return R2RStreamingRAGPipe(
                llm_provider=self.providers.llm,
                prompt_provider=self.providers.prompt,
            )
        else:
            from r2r.pipes import R2RRAGPipe

            return R2RRAGPipe(
                llm_provider=self.providers.llm,
                prompt_provider=self.providers.prompt,
            )

    def create_eval_pipe(self) -> Any:
        from r2r.pipes import R2REvalPipe

        return R2REvalPipe(eval_provider=self.providers.eval)


class R2RPipelineFactory:
    def __init__(self, config: R2RConfig, pipes: R2RPipes):
        self.config = config
        self.pipes = pipes

    def create_ingestion_pipeline(self) -> IngestionPipeline:
        ingestion_pipeline = IngestionPipeline()
        ingestion_pipeline.add_pipe(self.pipes.parsing_pipe)
        ingestion_pipeline.add_pipe(self.pipes.embedding_pipe)
        ingestion_pipeline.add_pipe(self.pipes.vector_storage_pipe)
        return ingestion_pipeline

    def create_search_pipeline(self) -> SearchPipeline:
        search_pipeline = SearchPipeline()
        search_pipeline.add_pipe(self.pipes.search_pipe)
        return search_pipeline

    def create_rag_pipeline(self, streaming: bool = False) -> RAGPipeline:
        search_pipe = self.pipes.search_pipe
        rag_pipe = (
            self.pipes.streaming_rag_pipe if streaming else self.pipes.rag_pipe
        )

        rag_pipeline = RAGPipeline()
        rag_pipeline.add_pipe(search_pipe)
        rag_pipeline.add_pipe(
            rag_pipe,
            add_upstream_outputs=[
                {
                    "prev_pipe_name": search_pipe.config.name,
                    "prev_output_field": "search_results",
                    "input_field": "raw_search_results",
                },
                {
                    "prev_pipe_name": search_pipe.config.name,
                    "prev_output_field": "search_queries",
                    "input_field": "query",
                },
            ],
        )
        return rag_pipeline

    def create_eval_pipeline(self) -> EvalPipeline:
        eval_pipeline = EvalPipeline()
        eval_pipeline.add_pipe(self.pipes.eval_pipe)
        return eval_pipeline

    def create_pipelines(
        self,
        ingestion_pipeline: Optional[IngestionPipeline] = None,
        search_pipeline: Optional[SearchPipeline] = None,
        rag_pipeline: Optional[RAGPipeline] = None,
        streaming_rag_pipeline: Optional[RAGPipeline] = None,
        eval_pipeline: Optional[EvalPipeline] = None,
    ) -> R2RPipelines:
        try:
            self.configure_logging()
        except Exception as e:
            logger.warn(f"Error configuring logging: {e}")

        return R2RPipelines(
            ingestion_pipeline=ingestion_pipeline
            or self.create_ingestion_pipeline(),
            search_pipeline=search_pipeline or self.create_search_pipeline(),
            rag_pipeline=rag_pipeline
            or self.create_rag_pipeline(streaming=False),
            streaming_rag_pipeline=streaming_rag_pipeline
            or self.create_rag_pipeline(streaming=True),
            eval_pipeline=eval_pipeline or self.create_eval_pipeline(),
        )

    def configure_logging(self):
        PipeLoggingConnectionSingleton.configure(self.config.logging)
