from fastapi import FastAPI
from routers import routers
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()




from fastapi.middleware.cors import CORSMiddleware

# Debug: Print the frontend URL being used for CORS
frontend_url = os.getenv("FRONTEND_URL")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url] if frontend_url else ["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)






@app.get("/")
def read_root():
    return{"message":"welcome"}

for router in routers:
    app.include_router(router)