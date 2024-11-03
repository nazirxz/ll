from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime, timedelta
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Well Management API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class WellUpdateRequest(BaseModel):
    data: List[Dict[str, Any]]
    source_well: str
    target_well: str
    insert_position: Optional[str] = "before"

def format_date_string(date_value: Any) -> str:
    if pd.isna(date_value) or date_value == '':
        return ''
    try:
        if isinstance(date_value, str):
            dt = pd.to_datetime(date_value)
        else:
            dt = date_value
        return dt.strftime('%d-%b-%Y')
    except:
        return str(date_value) if date_value is not None else ''

def calculate_finish_date(start_ew, duration, persen_rl):
    if pd.isna(start_ew):
        return pd.NaT
    adjusted_duration = (1 - persen_rl) * duration
    return start_ew + pd.Timedelta(days=adjusted_duration)

def calculate_rfd(finish_date):
    if pd.isna(finish_date):
        return pd.NaT
    return finish_date + pd.Timedelta(days=10)

def calculate_delta(drmi, rfd):
    if pd.isna(drmi) or pd.isna(rfd):
        return 0
    return (drmi - rfd).days

def recalculate_fleet_dates(fleet_data: pd.DataFrame) -> pd.DataFrame:
    """Recalculate dates for a fleet's wells"""
    if len(fleet_data) == 0:
        return fleet_data
        
    for i in range(len(fleet_data)):
        if i == 0:
            start_date = fleet_data.iloc[i]['RFC_MAX_REQUIRED']
        else:
            start_date = fleet_data.iloc[i-1]['FINISH_DATE']
        
        fleet_data.iloc[i, fleet_data.columns.get_loc('START_EW')] = start_date
        
        finish_date = calculate_finish_date(
            start_date,
            float(fleet_data.iloc[i]['DURATION']),
            float(fleet_data.iloc[i]['PERSEN_RL'])
        )
        fleet_data.iloc[i, fleet_data.columns.get_loc('FINISH_DATE')] = finish_date
        fleet_data.iloc[i, fleet_data.columns.get_loc('EST_COMPLETION_EARTHWORK')] = finish_date
        
        rfd_date = calculate_rfd(finish_date)
        fleet_data.iloc[i, fleet_data.columns.get_loc('RFD')] = rfd_date
        fleet_data.iloc[i, fleet_data.columns.get_loc('EST_COMPLETION_PARTIAL_RFD')] = rfd_date
        
        drmi = pd.to_datetime(fleet_data.iloc[i]['DRMI'])
        fleet_data.iloc[i, fleet_data.columns.get_loc('DELTA')] = calculate_delta(drmi, rfd_date)
    
    return fleet_data

@app.post("/update-well-position")
async def update_well_position(request: WellUpdateRequest):
    """Endpoint for handling well position updates and recalculating dates"""
    try:
        df = pd.DataFrame(request.data)
        
        # Convert date columns to datetime
        date_columns = ['START_EW', 'FINISH_DATE', 'DRMI', 'RFD', 'RFC_MAX_REQUIRED',
                       'EST_COMPLETION_EARTHWORK', 'EST_COMPLETION_PARTIAL_RFD']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

        # Get the source well being moved
        source_well_data = df[df['WELL_NAME'] == request.source_well].iloc[0].copy()
        original_fleet = source_well_data['FLEET']
        
        # Get target well's fleet
        target_well_data = df[df['WELL_NAME'] == request.target_well].iloc[0]
        target_fleet = target_well_data['FLEET']
        
        # Remove the source well from its current position
        df = df[df['WELL_NAME'] != request.source_well]
        
        # Find the target position
        target_index = df[df['WELL_NAME'] == request.target_well].index[0]
        if request.insert_position == "after":
            target_index += 1
            
        # If moving to a different fleet, update the well's fleet
        if original_fleet != target_fleet:
            source_well_data['FLEET'] = target_fleet
        
        # Insert the well at the new position
        df = pd.concat([
            df.iloc[:target_index],
            pd.DataFrame([source_well_data]),
            df.iloc[target_index:]
        ]).reset_index(drop=True)
        
        # Process each fleet
        result_dfs = []
        for fleet in df['FLEET'].unique():
            fleet_data = df[df['FLEET'] == fleet].copy().reset_index(drop=True)
            fleet_data = recalculate_fleet_dates(fleet_data)
            result_dfs.append(fleet_data)
        
        # Combine results
        result = pd.concat(result_dfs, ignore_index=True)
        
        # Format dates back to strings
        for col in date_columns:
            if col in result.columns:
                result[col] = result[col].apply(format_date_string)

        return {
            "success": True,
            "message": f"Well {request.source_well} {'moved to different fleet' if original_fleet != target_fleet else 'position updated'} successfully",
            "fleetChanged": original_fleet != target_fleet,
            "data": result.to_dict('records')
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)