from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from db.database import get_db
from schemas_v2.economics_v2_schema import ScenarioRunIn
from services_v2.simulation.scenario_service import ScenarioService

router = APIRouter(prefix="/api/economics/v2/scenarios", tags=["Simulation v2"])

@router.post("/run", status_code=201)
def run_scenario(payload: ScenarioRunIn, db: Session = Depends(get_db)):
    return ScenarioService().run(payload, db)

@router.get("/{scenario_id}")
def get_scenario(scenario_id: str, db: Session = Depends(get_db)):
    result = ScenarioService().get(scenario_id, db)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router.get("/{scenario_id}/export/csv", response_class=PlainTextResponse)
def export_scenario_csv(scenario_id: str, db: Session = Depends(get_db)):
    csv_data = ScenarioService().export_csv(scenario_id, db)
    if not csv_data:
        raise HTTPException(status_code=404, detail="Scenario not found or has no data.")
    return csv_data
