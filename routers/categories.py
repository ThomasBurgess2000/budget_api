from fastapi import APIRouter, Depends, HTTPException
from typing import List
import uuid

from dependencies import get_authenticated_user
from supabase_init import supabase_client
import schemas # Import schemas

router = APIRouter(
    prefix="/categories",
    tags=["categories"],
    dependencies=[Depends(get_authenticated_user)],
    responses={404: {"description": "Not found"}},
)

@router.get(
    "/monthly-budget/{monthly_budget_id}",
    response_model=List[schemas.CategoryBase],
    description="""Retrieves all categories for the **currently authenticated user**
    associated with the given **monthly budget ID**.""",
    operation_id="get_categories_for_month",
)
async def get_categories_for_month(
    monthly_budget_id: uuid.UUID,
    authenticated_user_id: str = Depends(get_authenticated_user),
):
    try:
        # Fetch Categories linked to this Monthly Budget ID for the authenticated user
        categories_response = (
            supabase_client.table("Categories")
            .select("*")
            .eq("monthly_budget", str(monthly_budget_id))
            .eq("user_id", authenticated_user_id)
            .execute()
        )

        if categories_response.data:
            return categories_response.data
        else:
            # It's valid to have no categories for a budget, return empty list
            return []

    except Exception as e:
        print(f"Database or processing error in get_categories_for_month: {e}")
        # Consider logging the error properly in a real application
        raise HTTPException(status_code=500, detail="Internal server error retrieving categories.")

# Helper function to get category details (avoids duplicate code)
async def _get_category_or_404(category_id: uuid.UUID, user_id: str):
    try:
        response = (
            supabase_client.table("Categories")
            .select("id, amount_budgeted") # Select only needed fields
            .eq("id", str(category_id))
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Category not found or does not belong to the user.")
        return response.data[0]
    except Exception as e:
        print(f"Error fetching category {category_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error fetching category details.")


@router.get(
    "/{category_id}/budgeted",
    response_model=schemas.CategoryAmountResponse,
    description="Retrieves the budgeted amount for a specific category.",
    operation_id="get_category_budgeted_amount",
)
async def get_category_budgeted_amount(
    category_id: uuid.UUID,
    authenticated_user_id: str = Depends(get_authenticated_user),
):
    category_data = await _get_category_or_404(category_id, authenticated_user_id)
    return schemas.CategoryAmountResponse(amount=category_data.get("amount_budgeted", 0.0))


@router.get(
    "/{category_id}/spent",
    response_model=schemas.CategoryAmountResponse,
    description="Retrieves the total amount spent (sum of positive transactions) for a specific category.",
    operation_id="get_category_spent_amount",
)
async def get_category_spent_amount(
    category_id: uuid.UUID,
    authenticated_user_id: str = Depends(get_authenticated_user),
):
    # First verify category exists for the user (implicitly done by fetching)
    await _get_category_or_404(category_id, authenticated_user_id)

    try:
        transactions_response = (
            supabase_client.table("Transactions")
            .select("amount")
            .eq("category", str(category_id))
            .eq("user_id", authenticated_user_id)
            .execute()
        )

        total_spent = 0.0
        if transactions_response.data:
            # Sum only positive amounts (debits/spent)
            # Negative amounts are credits/income
            total_spent = sum(t['amount'] for t in transactions_response.data if t['amount'] > 0)

        return schemas.CategoryAmountResponse(amount=total_spent)

    except Exception as e:
        print(f"Error calculating spent amount for category {category_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error calculating spent amount.")


@router.get(
    "/{category_id}/remaining",
    response_model=schemas.CategoryAmountResponse,
    description="Retrieves the remaining amount (budgeted - spent) for a specific category.",
    operation_id="get_category_remaining_amount",
)
async def get_category_remaining_amount(
    category_id: uuid.UUID,
    authenticated_user_id: str = Depends(get_authenticated_user),
):
    # Get budgeted amount
    category_data = await _get_category_or_404(category_id, authenticated_user_id)
    budgeted_amount = category_data.get("amount_budgeted", 0.0)
    print(f"Budgeted amount: {budgeted_amount}")
    # Get net spending/income by summing all transaction amounts for the category
    try:
        transactions_response = (
            supabase_client.table("Transactions")
            .select("amount")
            .eq("category", str(category_id))
            .eq("user_id", authenticated_user_id)
            .execute()
        )
        print(f"Transactions response: {transactions_response.data}")
        net_transaction_amount = 0.0
        if transactions_response.data:
            # Sum all amounts: positive are expenses (decrease remaining),
            # negative are income (increase remaining)
            net_transaction_amount = sum(t['amount'] for t in transactions_response.data)
        print(f"Net transaction amount: {net_transaction_amount}")
        # Remaining = Budgeted - Net Transaction Amount
        # e.g., Budgeted 100, Spent 30 (+30), Received 10 (-10) -> Net = 20
        # Remaining = 100 - 20 = 80
        remaining_amount = budgeted_amount - net_transaction_amount
        print(f"Remaining amount: {remaining_amount}")
        return schemas.CategoryAmountResponse(amount=remaining_amount)

    except Exception as e:
        print(f"Error calculating remaining amount for category {category_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error calculating remaining amount.")


# Placeholder for category endpoints 