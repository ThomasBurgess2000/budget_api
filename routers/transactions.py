from fastapi import APIRouter, Depends, HTTPException, status, Response
from typing import List
import uuid

from dependencies import get_authenticated_user
from supabase_init import supabase_client
import schemas

router = APIRouter(
    prefix="/transactions",
    tags=["transactions"],
    dependencies=[Depends(get_authenticated_user)],
    responses={404: {"description": "Not found"}},
)

@router.get(
    "/monthly-budget/{monthly_budget_id}",
    response_model=List[schemas.TransactionBase],
    description="""Retrieves all transactions for the **currently authenticated user**
    that fall within the month specified by the given **monthly budget ID**.""",
    operation_id="get_transactions_for_month",
)
async def get_transactions_for_month(
    monthly_budget_id: uuid.UUID,
    authenticated_user_id: str = Depends(get_authenticated_user),
):
    try:
        # 1. Verify the MonthlyBudget ID exists (optional, but good practice)
        budget_response = (
            supabase_client.table("MonthlyBudgets")
            .select("id") # Just need to know it exists
            .eq("id", str(monthly_budget_id))
            .eq("user_id", authenticated_user_id) # Also ensure it belongs to the user
            .limit(1)
            .execute()
        )
        if not budget_response.data:
            raise HTTPException(status_code=404, detail="Monthly budget not found or does not belong to the user.")

        # 2. Fetch Categories linked to this Monthly Budget ID
        categories_response = (
            supabase_client.table("Categories")
            .select("id") # Select only the category IDs
            .eq("monthly_budget", str(monthly_budget_id))
            .eq("user_id", authenticated_user_id) # Ensure categories also belong to the user
            .execute()
        )

        if not categories_response.data:
            # No categories linked to this budget, so no transactions via categories
            return []

        category_ids = [category['id'] for category in categories_response.data]

        # 3. Fetch Transactions linked to these Category IDs for the authenticated user
        transactions_response = (
            supabase_client.table("Transactions")
            .select("*")
            .eq("user_id", authenticated_user_id)
            .in_("category", category_ids) # Filter by the list of category IDs
            .order("created_at", desc=True)
            .execute()
        )

        if transactions_response.data:
            return transactions_response.data
        else:
            return [] # Return empty list if no transactions found for these categories

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Database or processing error in get_transactions_for_month: {e}")
        raise HTTPException(status_code=500, detail="Internal server error retrieving transactions.")

@router.post(
    "/",
    response_model=List[schemas.TransactionBase],
    status_code=status.HTTP_201_CREATED,
    description="""Creates one or more new transactions for the **currently authenticated user**.

    Provide a list of transaction objects in the request body.

    - **Positive `amount`** represents a **debit** (money spent).
    - **Negative `amount`** represents a **credit** (money received).
    """,
    operation_id="create_transactions",
)
async def create_transactions(
    transaction_list_data: schemas.TransactionCreateList,
    authenticated_user_id: str = Depends(get_authenticated_user),
):
    transactions_to_insert = []
    transactions_data = transaction_list_data.transactions
    category_ids_to_verify = {str(t.category_id) for t in transactions_data}

    if not transactions_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction list cannot be empty."
        )

    try:
        # 1. Bulk Verify Category IDs exist and belong to the user
        category_response = (
            supabase_client.table("Categories")
            .select("id")
            .in_("id", list(category_ids_to_verify))
            .eq("user_id", authenticated_user_id)
            .execute()
        )

        # Check if all requested category IDs were found and belong to the user
        found_category_ids = {str(cat['id']) for cat in category_response.data}
        missing_or_unauthorized_ids = category_ids_to_verify - found_category_ids

        if missing_or_unauthorized_ids:
            detail_msg = f"Categories not found or do not belong to the user: {', '.join(missing_or_unauthorized_ids)}"
            # If only one is missing, perhaps a 404 is better, but 400 covers "bad request data"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=detail_msg
            )

        # 2. Prepare transaction data for insertion
        for transaction_data in transactions_data:
            new_transaction_dict = transaction_data.model_dump()
            new_transaction_dict["user_id"] = authenticated_user_id
            # Rename category_id to category AND explicitly convert UUID to string
            category_uuid = new_transaction_dict.pop("category_id")
            new_transaction_dict["category"] = str(category_uuid)
            # Use the provided transaction_date for created_at
            new_transaction_dict["created_at"] = new_transaction_dict.pop("transaction_date").isoformat()
            transactions_to_insert.append(new_transaction_dict)


        # 3. Bulk Insert the new transactions
        insert_response = (
            supabase_client.table("Transactions")
            .insert(transactions_to_insert)
            .execute()
        )

        if not insert_response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create transactions."
            )

        # Supabase returns a list of the created objects
        created_transactions = insert_response.data

        return created_transactions

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        # Explicitly convert the exception to string to avoid serialization issues
        print(f"Database or processing error in create_transactions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error creating transactions."
        )

@router.delete(
    "/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Deletes a specific transaction by its ID for the **currently authenticated user**.",
    operation_id="delete_transaction",
)
async def delete_transaction(
    transaction_id: uuid.UUID,
    authenticated_user_id: str = Depends(get_authenticated_user),
):
    try:
        # Attempt to delete the transaction only if it matches the user_id
        delete_response = (
            supabase_client.table("Transactions")
            .delete()
            .eq("id", str(transaction_id))
            .eq("user_id", authenticated_user_id)
            .execute()
        )

        # Supabase delete doesn't error if no rows match, but returns an empty list in 'data'
        # If the data list is empty, it means no transaction was deleted (either not found or didn't belong to user)
        if not delete_response.data:
            # To be safe, we can double-check if the transaction exists at all
            check_response = (
                supabase_client.table("Transactions")
                .select("id")
                .eq("id", str(transaction_id))
                .limit(1)
                .execute()
            )
            if not check_response.data:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")
            else:
                # Transaction exists but doesn't belong to the user
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not authorized to delete this transaction.")

        # If deletion was successful (delete_response.data is not empty), return No Content
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Database or processing error in delete_transaction: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error deleting transaction."
        ) 