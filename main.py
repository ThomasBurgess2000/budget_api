from fastapi import FastAPI
import os
from routers import transactions, categories, monthly_budgets
import schemas
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    servers=[
        {"url": os.getenv("BASE_URL"), "description": "Production Server"},
    ]
)

app.include_router(transactions.router)
app.include_router(categories.router)
app.include_router(monthly_budgets.router)

@app.get("/", response_model=schemas.RootResponse)
async def read_root():
    return {"message": "Hello World"}
