from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import asyncio

async def test():
    model = ChatOpenAI(
        base_url="http://localhost:1234/v1",
        api_key="lm-studio",
        model="local-model",
        max_retries=0,
        timeout=10.0
    )
    try:
        print("Sending request to LM Studio...")
        res = await model.ainvoke([HumanMessage(content="Hello! Respond with one word.")])
        print("Response:", res.content)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(test())
