from __future__ import annotations

import asyncio
import traceback


from lightrag.llm.openai import openai_complete_if_cache, openai_embed




async def main() -> None:
    text = "123"
    texts=[text]
    print(f"[demo] 准备调用 embedding，文本长度={len(text)}")
    success = 0
    try:
        vectors = await openai_embed.func(
            texts,
            model='Qwen3-Embedding-0.6B-4bit-DWQ',
            api_key='pc0824tq',
            base_url='http://localhost:8000/v1'
        )
        vector_count = len(vectors) if isinstance(vectors, list) else -1
        first_dim = len(vectors[0]) if isinstance(vectors, list) and vectors else -1
        success += 1
        print(f"[demo]  调用成功，vector_count={vector_count}, first_vector_dim={first_dim}")
    except Exception as exc:
        print(f"[demo] 调用失败，error_type={exc.__class__.__name__}, error={exc}")
        print(traceback.format_exc())
    await asyncio.sleep(0.5)



if __name__ == "__main__":
    asyncio.run(main())
