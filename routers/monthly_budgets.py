from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from typing import List

from dependencies import get_authenticated_user
from supabase_init import supabase_client
import schemas

router = APIRouter(
    prefix="/monthly-budgets",
    tags=["monthly-budgets"],
    dependencies=[Depends(get_authenticated_user)], # Assuming all budget routes need auth
    responses={404: {"description": "Not found"}},
)

@router.get(
    "/current-month-id",
    response_model=schemas.CurrentMonthBudgetIDResponse,
    description="""Retrieves the unique identifier (`id`) for the monthly budget
corresponding to the **currently authenticated user** and the **current calendar month**.""",
    operation_id="get_current_month_budget_id",
)
async def get_current_month_budget_id(
    authenticated_user_id: str = Depends(get_authenticated_user)
):
    today = date.today()
    first_day_of_month = today.replace(day=1)
    month_str = first_day_of_month.isoformat()

    try:
        response = (
            supabase_client.table("MonthlyBudgets")
            .select("id")
            .eq("user_id", authenticated_user_id)
            .eq("month", month_str)
            .limit(1)
            .execute()
        )

        if response.data:
            return {"budget_id": response.data[0]["id"]}
        else:
            raise HTTPException(
                status_code=404,
                detail=f"No budget found for the authenticated user for the current month ({month_str})",
            )
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Unexpected database error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/all",
         response_model=List[schemas.MonthlyBudgetBase],
         description="""Retrieves all monthly budgets for the **currently authenticated user**.""",
         operation_id="get_all_budgets",
)
async def get_all_budgets(
    authenticated_user_id: str = Depends(get_authenticated_user)
):
    try:
        response = (
            supabase_client.table("MonthlyBudgets")
            .select("*")
            .eq("user_id", authenticated_user_id)
            .execute()
        )

        if response.data:
            return response.data
        else:
            return []
    except Exception as e:
        print(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") 