# ---------------------------
# Project paths configuration
# ---------------------------

# Personal OneDrive root (your own machine)
ONEDRIVE_ROOT <- "/path/to/your/OneDrive/root"

# Personal econ server root (your own machine)
SERVER_ROOT <- "/path/to/your/server/root"

# Personal switchdrive root (your own machine)
SWITCHDRIVE_ROOT <- "/path/to/your/switchdrive/root"

# Personal overleaf root (your own machine)
OVERLEAF_ROOT <- "/path/to/your/overleaf/root"

# Data folder
DATA_ROOT <- file.path(SERVER_ROOT, "data")

# Backup data folder
BACKUP_ROOT <- file.path(DATA_ROOT, "11_Backup")

# Data subfolders
LABS_LIST <- file.path(DATA_ROOT, "9_Lab_Name_Location")
WAVE1_LABS_LIST <- file.path(LABS_LIST, "1_MeFMNF")
WAVE2_LABS_LIST <- file.path(LABS_LIST, "2_VetsuisseUSZ")
COMBINED_WAVES_LABS_LIST <- file.path(LABS_LIST, "3_Combined")
DATA_TO_MERGE <- file.path(DATA_ROOT, "10_Data_To_Merge")
ENUMERATORS <- file.path(DATA_TO_MERGE, "1_Enumerators")
WAVE1_ENUMERATORS <- file.path(ENUMERATORS, "1_MeFMNF")
WAVE2_ENUMERATORS <- file.path(ENUMERATORS, "2_VetsuisseUSZ")
COMBINED_WAVES_ENUMERATORS <- file.path(ENUMERATORS, "3_Combined")
SURVEY_DICTIONARIES <- file.path(DATA_TO_MERGE, "2_Survey_Dictionaries")
DATA_DICTIONARIES <- file.path(DATA_TO_MERGE, "3_Data_Dictionaries")
CLEANING_WORKBOOKS <- file.path(DATA_TO_MERGE, "4_Cleaning_Workbooks")
SPARK_DATA <- file.path(DATA_TO_MERGE, "5_SPARK_Calculator_Data")

# BL data folders
BL_DATA_ROOT <- file.path(DATA_ROOT, "12_BL_Data")
BL_RAW_SAMPLE <- file.path(BL_DATA_ROOT, "1_Sample")
BL_RAW_SURVEY <- file.path(BL_DATA_ROOT, "2_Raw_Survey")
BL_RAW_CHECKLIST <- file.path(BL_DATA_ROOT, "3_Raw_Checklist")

# BL backup data folders
BL_DATA_BACKUP <- file.path(BACKUP_ROOT, "12_BL_Data")
BL_RAW_SAMPLE_BACKUP <- file.path(BL_DATA_BACKUP, "1_Sample")
BL_RAW_SURVEY_BACKUP <- file.path(BL_DATA_BACKUP, "2_Raw_Survey")
BL_RAW_CHECKLIST_BACKUP <- file.path(BL_DATA_BACKUP, "3_Raw_Checklist")

# Calculators folder
CALCULATORS_ROOT <- file.path(DATA_ROOT, "13_Calculators")
CALCULATORS_WITH_TIPS <- file.path(CALCULATORS_ROOT, "8_Final_Calculators")

# EL survey folder (empty)
EL_EMPTY_ROOT <- file.path(DATA_ROOT, "14_EL_Empty")

# EL data folders
EL_DATA_ROOT <- file.path(DATA_ROOT, "15_EL_Data")
EL_RAW_SAMPLE <- file.path(EL_DATA_ROOT, "1_Sample")
EL_RAW_SURVEY <- file.path(EL_DATA_ROOT, "2_Raw_Survey")

# EL backup data folders
EL_DATA_BACKUP <- file.path(BACKUP_ROOT, "15_EL_Data")
EL_RAW_SAMPLE_BACKUP <- file.path(EL_DATA_BACKUP, "1_Sample")
EL_RAW_SURVEY_BACKUP <- file.path(EL_DATA_BACKUP, "2_Raw_Survey")

# Processed data folder
PROCESSED_DATA <- file.path(DATA_ROOT, "16_Processed_Data")

# Clean data folder
CLEAN_DATA <- file.path(DATA_ROOT, "17_Clean_Data")

# Sensitive data folder
SENSITIVE_DATA <- file.path(DATA_ROOT, "18_Sensitive_Data")

# Output folder
OUTPUT <- file.path(OVERLEAF_ROOT, "2_Output")

# Set secret seed (for creating IDs)
SEED <- NULL

# FC confidential data
ELEC_PER_M3 <- NULL
GAS_PER_M3  <- NULL