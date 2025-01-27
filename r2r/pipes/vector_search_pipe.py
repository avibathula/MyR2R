import json
import logging
from typing import Any, AsyncGenerator, Optional

from r2r.core import (
    AsyncPipe,
    AsyncState,
    EmbeddingProvider,
    PipeType,
    SearchResult,
    VectorDBProvider,
)

from .abstractions.search_pipe import SearchPipe

logger = logging.getLogger(__name__)


class R2RVectorSearchPipe(SearchPipe):
    def __init__(
        self,
        vector_db_provider: VectorDBProvider,
        embedding_provider: EmbeddingProvider,
        type: PipeType = PipeType.SEARCH,
        config: Optional[SearchPipe.SearchConfig] = None,
        *args,
        **kwargs,
    ):
        super().__init__(
            vector_db_provider=vector_db_provider,
            type=type,
            config=config or SearchPipe.SearchConfig(),
            *args,
            **kwargs,
        )
        self.embedding_provider = embedding_provider

    async def search(
        self,
        message: str,
        *args: Any,
        **kwargs: Any,
    ) -> AsyncGenerator[SearchResult, None]:
        search_filters_override = kwargs.get("search_filters", None)
        search_limit_override = kwargs.get("search_limit", None)
        await self.enqueue_log(
            pipe_run_id=self.run_info.run_id, key="search_query", value=message
        )
        results = []
        for result in self.vector_db_provider.search(
            query_vector=self.embedding_provider.get_embedding(
                message,
            ),
            filters=search_filters_override or self.config.search_filters,
            limit=search_limit_override or self.config.search_limit,
        ):
            result.metadata["query"] = message
            results.append(result)
            yield result

        await self.enqueue_log(
            pipe_run_id=self.run_info.run_id,
            key="search_results",
            value=json.dumps([ele.json() for ele in results]),
        )

    async def _run_logic(
        self,
        input: AsyncPipe.Input,
        state: AsyncState,
        *args: Any,
        **kwargs: Any,
    ) -> AsyncGenerator[SearchResult, None]:
        search_queries = []
        search_results = []
        async for search_request in input.message:
            search_queries.append(search_request)
            async for result in self.search(
                message=search_request, *args, **kwargs
            ):
                search_results.append(result)
                yield result

        await state.update(
            self.config.name, {"output": {"search_results": search_results}}
        )

        await state.update(
            self.config.name,
            {
                "output": {
                    "search_queries": search_queries,
                    "search_results": search_results,
                }
            },
        )
