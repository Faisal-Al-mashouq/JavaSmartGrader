import asyncio


async def greet():
    asyncio.timeout(2)
    print("Hello, World!")


async def meet():
    print("Nice to meet you!")


if __name__ == "__main__":
    asyncio.run(greet())
    asyncio.run(meet())
