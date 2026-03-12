import uvicorn
from config.settings import settings

if __name__ == "__main__":
    print("="*50)
    print(f"🚀 {settings.APP_NAME}")
    print(f"📡 http://localhost:{settings.PORT}")
    print(f"📚 Docs: http://localhost:{settings.PORT}/docs")
    print(f"🤖 Model: {settings.DEFAULT_MODEL}")
    print("="*50)
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )