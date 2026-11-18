from pydantic import BaseModel, Field
class ReviewCreate(BaseModel):
    code: str=Field(min_length=2,max_length=80)
    page_size: int=Field(default=10,ge=1,le=100)
    ttl_seconds: int|None=Field(default=None,ge=10,le=600)
class ReviewPageInput(BaseModel):
    cursor: int=Field(ge=0)
