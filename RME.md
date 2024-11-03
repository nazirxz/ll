# Contoh 1: Basic Request
curl -X POST \
  http://localhost:8001/update-well-position \
  -H 'Content-Type: application/json' \
  -d '{
    "data": [
        {
            "WELL_NAME": "WELL1",
            "DURATION": 71,
            "START_EW": "14-Jul-2024",
            "FINISH_DATE": "23-Sep-2024",
            "FLEET": "RDP #1",
            "NO_FLEET": 1.0,
            "STATUS": "Soil Filling 71% - 99%",
            "PLOT": "1Plot",
            "ERROR_CHECKING": 0,
            "PERSEN_RL": 0.95,
            "DELTA": -27.0,
            "FIELD": "Minas",
            "RIG_HP": 550,
            "MK": "RDP",
            "DT": 24.0,
            "RFC_MAX_REQUIRED": "23-Jul-2024",
            "RFD": "03-Oct-2024",
            "DRMI": "06-Sep-2024"
        },
        {
            "WELL_NAME": "WELL2",
            "DURATION": 7,
            "START_EW": "23-Sep-2024",
            "FINISH_DATE": "30-Sep-2024",
            "FLEET": "RDP #1",
            "NO_FLEET": 1.0,
            "STATUS": "RFC (RL not Started)",
            "PLOT": "1Plot",
            "ERROR_CHECKING": 0,
            "PERSEN_RL": 0,
            "DELTA": 70.0,
            "FIELD": "Minas",
            "RIG_HP": 550,
            "MK": "RDP",
            "DT": 24.0,
            "RFC_MAX_REQUIRED": "04-Nov-2024",
            "RFD": "10-Oct-2024",
            "DRMI": "19-Dec-2024"
        },
        {
            "WELL_NAME": "WELL3",
            "DURATION": 7,
            "START_EW": "23-Sep-2024",
            "FINISH_DATE": "30-Sep-2024",
            "FLEET": "RDP #2",
            "NO_FLEET": 1.0,
            "STATUS": "RFC (RL not Started)",
            "PLOT": "1Plot",
            "ERROR_CHECKING": 0,
            "PERSEN_RL": 0,
            "DELTA": 70.0,
            "FIELD": "Minas",
            "RIG_HP": 550,
            "MK": "RDP",
            "DT": 24.0,
            "RFC_MAX_REQUIRED": "04-Nov-2024",
            "RFD": "10-Oct-2024",
            "DRMI": "19-Dec-2024"
        }
    ],
    "source_well": "WELL2",
    "target_well": "WELL3",
    "insert_position": "before"
}'

# Contoh 2: Format yang lebih singkat (minimal required fields)
curl -X POST \
  http://localhost:8001/update-well-position \
  -H 'Content-Type: application/json' \
  -d '{
    "data": [
        {
            "WELL_NAME": "WELL1",
            "DURATION": 71,
            "FLEET": "RDP #1",
            "PERSEN_RL": 0.95,
            "RFC_MAX_REQUIRED": "23-Jul-2024",
            "DRMI": "06-Sep-2024"
        },
        {
            "WELL_NAME": "WELL2",
            "DURATION": 7,
            "FLEET": "RDP #1",
            "PERSEN_RL": 0,
            "RFC_MAX_REQUIRED": "04-Nov-2024",
            "DRMI": "19-Dec-2024"
        },
        {
            "WELL_NAME": "WELL3",
            "DURATION": 7,
            "FLEET": "RDP #2",
            "PERSEN_RL": 0,
            "RFC_MAX_REQUIRED": "04-Nov-2024",
            "DRMI": "19-Dec-2024"
        }
    ],
    "source_well": "WELL2",
    "target_well": "WELL3",
    "insert_position": "before"
}'

# Contoh 3: Menggunakan Windows CMD
curl -X POST ^
  http://localhost:8001/update-well-position ^
  -H "Content-Type: application/json" ^
  -d "{\"data\":[{\"WELL_NAME\":\"WELL1\",\"DURATION\":71,\"FLEET\":\"RDP #1\"},{\"WELL_NAME\":\"WELL2\",\"DURATION\":7,\"FLEET\":\"RDP #1\"},{\"WELL_NAME\":\"WELL3\",\"DURATION\":7,\"FLEET\":\"RDP #2\"}],\"source_well\":\"WELL2\",\"target_well\":\"WELL3\",\"insert_position\":\"before\"}"

# Contoh 4: Menggunakan PowerShell
$body = @{
    data = @(
        @{
            WELL_NAME = "WELL1"
            DURATION = 71
            FLEET = "RDP #1"
        },
        @{
            WELL_NAME = "WELL2"
            DURATION = 7
            FLEET = "RDP #1"
        },
        @{
            WELL_NAME = "WELL3"
            DURATION = 7
            FLEET = "RDP #2"
        }
    )
    source_well = "WELL2"
    target_well = "WELL3"
    insert_position = "before"
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://localhost:8001/update-well-position" -Body $body -ContentType "application/json"