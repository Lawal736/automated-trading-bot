from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .... import models, schemas
from ....api import deps
from ....services import report_service

router = APIRouter()

@router.get("/", response_model=schemas.report.Report)
def read_report(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Retrieve a full performance report for the current user.
    """
    report = report_service.get_full_report(db=db, user_id=current_user.id)
    return report 