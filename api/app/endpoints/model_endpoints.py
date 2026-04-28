from fastapi import APIRouter, status, Depends, Query

router = APIRouter(prefix="/model", tags=["model"])


#TODO Replace the return 0 by service.get that will be created
@router.get("/", status_code=status.HTTP_200_OK)
async def get_model(
    
):
    return 0 


#TODO add the schema's Train in the function parameters and add the correct return
@router.post("/", status_code=status.HTTP_201_CREATED)
async def train(

):
    return None




