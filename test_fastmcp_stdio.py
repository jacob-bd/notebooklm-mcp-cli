import sys
from fastmcp import FastMCP

with open("stdout.log", "w") as f_out, open("stderr.log", "w") as f_err:
    sys.stdout = f_out
    sys.stderr = f_err
    mcp = FastMCP("test")
    
    import asyncio
    async def run():
        # run_stdio_async is the internal method for stdio
        await mcp.run_stdio_async(show_banner=False)
    
    # We just want to see the startup logs, we can cancel it after 1 sec
    async def main():
        task = asyncio.create_task(run())
        await asyncio.sleep(1)
        task.cancel()
        
    asyncio.run(main())

