from fastapi import APIRouter, Depends
from src.config.database import db_session
from src.utils.security import current
from src.schemas.review import ReviewCreate, ReviewPageInput
from src.services import reviews as service
router = APIRouter()
@router.post('/reviews', status_code=201)
def create(data: ReviewCreate, db=Depends(db_session), user=Depends(current)):
    return service.create_session(db, data, user)
@router.post('/reviews/{ident}/pages')
def page(ident: int, data: ReviewPageInput, db=Depends(db_session), user=Depends(current)):
    return service.get_page(db, ident, data.cursor)
@router.get('/reviews/{ident}')
def status(ident: int, db=Depends(db_session), user=Depends(current)):
    return service.get_status(db, ident)
@router.delete('/reviews/{ident}')
def close(ident: int, db=Depends(db_session), user=Depends(current)):
    return service.close(db, ident, user)
