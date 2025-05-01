from fastapi import FastAPI

from routers import transactions, categories, monthly_budgets
import schemas

app = FastAPI(
    servers=[
        {"url": "https://be49-75-8-100-149.ngrok-free.app", "description": "Production Server"},
    ]
)

app.include_router(transactions.router)
app.include_router(categories.router)
app.include_router(monthly_budgets.router)

@app.get("/", response_model=schemas.RootResponse)
async def read_root():
    return {"message": "Hello World"}
