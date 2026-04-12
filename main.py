import uvicorn
from core.config import config

if __name__ == "__main__":
    uvicorn.run(
        "api.server:app",
        host=config.HOST,
        port=config.PORT,
        reload=False,
    )
