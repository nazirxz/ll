from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime, timedelta
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Well Management API")

class WellData(BaseModel):
    data: List[Dict[str, Any]]
    moved_well: Optional[Dict[str, Any]] = None  # Information about moved well if any
    source_fleet: Optional[str] = None           # Source fleet if well was moved
    target_fleet: Optional[str] = None           # Target fleet if well was moved
    new_index: Optional[int] = None              # New index in target fleet

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ProcessingLog:
    def __init__(self):
        self.errors = []
        
    def add_error(self, well_name: str, error_type: str, details: str):
        self.errors.append({
            "well_name": well_name,
            "error_type": error_type,
            "details": details,
            "timestamp": datetime.now().strftime("%d-%b-%Y")
        })
        
    def get_errors(self):
        return self.errors
        
    def has_errors(self):
        return len(self.errors) > 0

def format_date_string(date_value: Any) -> str:
    """Format date value to string in dd-MMM-yyyy format"""
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

def parse_date_safe(date_str: str, well_name: str, column: str, log: ProcessingLog) -> pd.Timestamp:
    """Safely parse date string with error logging"""
    if pd.isna(date_str) or not date_str:
        return pd.NaT
        
    try:
        return pd.to_datetime(date_str)
    except Exception as e:
        log.add_error(
            well_name=well_name,
            error_type="Date Parse Error",
            details=f"Invalid date format in column {column}: {date_str}"
        )
        return pd.NaT

def calculate_finish_date(start_ew, duration, persen_rl):
    """Calculate finish date based on formula"""
    if pd.isna(start_ew):
        return pd.NaT
    adjusted_duration = (1 - persen_rl) * duration
    return start_ew + pd.Timedelta(days=adjusted_duration)

def calculate_rfd(finish_date):
    """Calculate RFD (finish date + 10 days)"""
    if pd.isna(finish_date):
        return pd.NaT
    return finish_date + pd.Timedelta(days=10)

def calculate_delta(drmi, rfd):
    """Calculate delta between DRMI and RFD"""
    if pd.isna(drmi) or pd.isna(rfd):
        return 0
    return (drmi - rfd).days

def process_fleet_movement(df: pd.DataFrame, moved_well: Dict[str, Any], 
                         source_fleet: str, target_fleet: str, new_index: int) -> pd.DataFrame:
    """Handle processing when a well is moved between fleets"""
    df = df.copy()
    
    # Convert date columns to datetime
    date_columns = ['START_EW', 'FINISH_DATE', 'DRMI', 'RFD', 'RFC_MAX_REQUIRED',
                   'EST_COMPLETION_EARTHWORK', 'EST_COMPLETION_PARTIAL_RFD']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format='%d-%b-%Y', errors='coerce')
    
    # Get target fleet data
    target_fleet_data = df[df['FLEET'] == target_fleet].copy()
    
    # Update the moved well's fleet
    well_mask = df['WELL_NAME'] == moved_well['WELL_NAME']
    df.loc[well_mask, 'FLEET'] = target_fleet
    
    # If inserting at the beginning of target fleet
    if new_index == 0:
        # Use RFC_MAX_REQUIRED as start date
        start_date = df.loc[well_mask, 'RFC_MAX_REQUIRED'].iloc[0]
    else:
        # Use previous well's finish date
        prev_well = target_fleet_data.iloc[new_index - 1]
        start_date = prev_well['FINISH_DATE']
    
    # Update start date for moved well
    df.loc[well_mask, 'START_EW'] = start_date
    
    # Recalculate dates for moved well
    duration = float(moved_well['DURATION'])
    persen_rl = float(moved_well['PERSEN_RL'])
    
    finish_date = calculate_finish_date(start_date, duration, persen_rl)
    rfd_date = calculate_rfd(finish_date)
    
    df.loc[well_mask, 'FINISH_DATE'] = finish_date
    df.loc[well_mask, 'RFD'] = rfd_date
    df.loc[well_mask, 'EST_COMPLETION_EARTHWORK'] = finish_date
    df.loc[well_mask, 'EST_COMPLETION_PARTIAL_RFD'] = rfd_date
    
    # Recalculate DELTA
    drmi = df.loc[well_mask, 'DRMI'].iloc[0]
    df.loc[well_mask, 'DELTA'] = calculate_delta(drmi, rfd_date)
    
    # Update subsequent wells in target fleet
    target_fleet_data = df[df['FLEET'] == target_fleet].copy()
    target_fleet_data = target_fleet_data.sort_index()
    
    for i in range(new_index + 1, len(target_fleet_data)):
        current_well = target_fleet_data.iloc[i]
        prev_finish_date = df[df['WELL_NAME'] == target_fleet_data.iloc[i-1]['WELL_NAME']]['FINISH_DATE'].iloc[0]
        
        df.loc[df['WELL_NAME'] == current_well['WELL_NAME'], 'START_EW'] = prev_finish_date
        
        new_finish_date = calculate_finish_date(
            prev_finish_date,
            float(current_well['DURATION']),
            float(current_well['PERSEN_RL'])
        )
        new_rfd = calculate_rfd(new_finish_date)
        
        mask = df['WELL_NAME'] == current_well['WELL_NAME']
        df.loc[mask, 'FINISH_DATE'] = new_finish_date
        df.loc[mask, 'RFD'] = new_rfd
        df.loc[mask, 'EST_COMPLETION_EARTHWORK'] = new_finish_date
        df.loc[mask, 'EST_COMPLETION_PARTIAL_RFD'] = new_rfd
        df.loc[mask, 'DELTA'] = calculate_delta(current_well['DRMI'], new_rfd)
    
    # Format dates back to strings
    for col in date_columns:
        if col in df.columns:
            df[col] = df[col].apply(format_date_string)
    
    return df

def adjust_fleet_data(df: pd.DataFrame) -> tuple[pd.DataFrame, ProcessingLog]:
    """Regular fleet data adjustment without movement"""
    log = ProcessingLog()
    df = df.copy()
    
    # Convert date columns to datetime
    date_columns = [
        'START_EW', 'FINISH_DATE', 'DRMI', 'RFD', 'RFC_MAX_REQUIRED',
        'EST_COMPLETION_EARTHWORK', 'EST_COMPLETION_PARTIAL_RFD'
    ]
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format='%d-%b-%Y', errors='coerce')
    
    # Process each fleet separately
    adjusted_fleets = []
    for fleet in df['FLEET'].unique():
        fleet_data = df[df['FLEET'] == fleet].copy().reset_index(drop=True)
        
        for i in range(len(fleet_data)):
            well_name = fleet_data.iloc[i]['WELL_NAME']
            
            # Handle start date
            if i == 0:
                start_date = fleet_data.iloc[i]['RFC_MAX_REQUIRED']
            else:
                start_date = fleet_data.iloc[i-1]['FINISH_DATE']
                
            fleet_data.iloc[i, fleet_data.columns.get_loc('START_EW')] = start_date
            
            # Calculate FINISH_DATE
            duration = float(fleet_data.iloc[i]['DURATION'])
            persen_rl = float(fleet_data.iloc[i]['PERSEN_RL'])
            
            finish_date = calculate_finish_date(start_date, duration, persen_rl)
            fleet_data.iloc[i, fleet_data.columns.get_loc('FINISH_DATE')] = finish_date
            
            # Calculate RFD
            rfd = calculate_rfd(finish_date)
            fleet_data.iloc[i, fleet_data.columns.get_loc('RFD')] = rfd
            
            # Calculate DELTA
            drmi = fleet_data.iloc[i]['DRMI']
            delta = calculate_delta(drmi, rfd)
            fleet_data.iloc[i, fleet_data.columns.get_loc('DELTA')] = delta

            # Update EST_COMPLETION dates
            fleet_data.iloc[i, fleet_data.columns.get_loc('EST_COMPLETION_EARTHWORK')] = finish_date
            fleet_data.iloc[i, fleet_data.columns.get_loc('EST_COMPLETION_PARTIAL_RFD')] = rfd
        
        adjusted_fleets.append(fleet_data)
    
    # Combine all adjusted fleets
    result = pd.concat(adjusted_fleets, ignore_index=True)
    
    # Format dates back to strings
    for col in date_columns:
        if col in result.columns:
            result[col] = result[col].apply(format_date_string)
    
    return result, log

@app.post("/adjust-data")
async def adjust_data(request: WellData):
    try:
        df = pd.DataFrame(request.data)
        
        # Check if this is a fleet movement operation
        if request.moved_well and request.source_fleet and request.target_fleet is not None and request.new_index is not None:
            # Handle fleet movement
            result_df = process_fleet_movement(
                df,
                request.moved_well,
                request.source_fleet,
                request.target_fleet,
                request.new_index
            )
            processing_log = ProcessingLog()  # Create empty log for movement operations
        else:
            # Regular data adjustment
            result_df, processing_log = adjust_fleet_data(df)
        
        response = {
            "success": True,
            "message": "Data processed successfully",
            "data": result_df.to_dict('records')
        }
        
        if processing_log.has_errors():
            response["errors"] = processing_log.get_errors()
            response["message"] = "Data processed with some date format errors"
            
        return response
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
def start_server():
    """Function to start the server with specific settings"""
    print("Starting Well Management API...")
    print("Documentation available at:")
    print("- Swagger UI: http://localhost:8000/docs")
    print("- ReDoc: http://localhost:8000/redoc")
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        reload_excludes=["*.pyc", "*.log"],
        log_level="info"
    )

if __name__ == "__main__":
    start_server()