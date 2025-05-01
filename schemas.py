from datetime import date, datetime
from pydantic import BaseModel
import uuid
from typing import Literal, List


class RootResponse(BaseModel):
    message: str


class CurrentMonthBudgetIDResponse(BaseModel):
    budget_id: uuid.UUID # Assuming UUID, change if it's int or other type


class MonthlyBudgetBase(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    month: date

    class Config:
        orm_mode = True


class TransactionBase(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: str | None = None
    amount: float
    created_at: datetime
    updated_at: datetime
    category: uuid.UUID | None = None

    class Config:
        orm_mode = True


class TransactionCreate(BaseModel):
    title: str
    amount: float # Positive for debit, negative for credit
    category_id: uuid.UUID
    transaction_date: date
    description: str | None = None


# New model to wrap the list for the request body
class TransactionCreateList(BaseModel):
    transactions: List[TransactionCreate]


class CategoryBase(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str # Changed from name to title
    amount_budgeted: float # Added amount_budgeted
    monthly_budget: uuid.UUID
    type: Literal["expense", "income"]

    class Config:
        orm_mode = True


class CategoryAmountResponse(BaseModel):
    amount: float
