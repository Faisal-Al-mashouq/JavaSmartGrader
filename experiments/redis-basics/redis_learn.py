import redis.asyncio as redis
import uuid


class RedisSandbox:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis_client = redis.Redis.from_url(redis_url, decode_responses=True)

    async def set_session(self, session_id: str, data: str, ex):
        return await self.redis_client.set(str(session_id), data, ex=ex)

    async def set_opp(self, key: str, value: str):
        return await self.redis_client.set(key, value)

    async def get_opp(self, key: str) -> str:
        return await self.redis_client.get(key)

    async def delete_opp(self, key: str):
        return await self.redis_client.delete(key)

    async def exists_opp(self, key: str) -> bool:
        return await self.redis_client.exists(key) >= 1

    async def flush_db(self):
        return await self.redis_client.flushdb()


async def main():
    rs = RedisSandbox("redis://:mypass@localhost:6379")
    await rs.flush_db()

    process_id = str(uuid.uuid4())
    data = "some data"
    ex = 5

    await rs.set_session(process_id, data, ex)
    print(process_id, await rs.get_opp(process_id))

    await asyncio.sleep(6)
    print(process_id, await rs.get_opp(process_id))
    print(await rs.exists_opp(process_id))
    await rs.flush_db()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
