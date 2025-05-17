import pandas as pd
from sqlalchemy import create_engine

data_path = '/workspace/WA_Fn-UseC_-HR-Employee-Attrition.csv'
df = pd.read_csv(data_path)

def transform_data(df):
    employee_fact = df[['EmployeeNumber', 'Age', 'DailyRate', 'DistanceFromHome',
                         'MonthlyIncome', 'NumCompaniesWorked', 'YearsAtCompany',
                         'YearsInCurrentRole', 'YearsSinceLastPromotion',
                         'TrainingTimesLastYear', 'PerformanceRating',
                         'JobSatisfaction', 'RelationshipSatisfaction',
                         'EnvironmentSatisfaction', 'Attrition']].copy()

    dim_demographics = df[['EmployeeNumber', 'Gender', 'MaritalStatus', 'Over18', 'Age']].copy()
    dim_business_travel = df[['BusinessTravel']].drop_duplicates().reset_index(drop=True)
    dim_business_travel['BusinessTravelID'] = dim_business_travel.index + 1
    dim_department = df[['Department']].drop_duplicates().reset_index(drop=True)
    dim_department['DepartmentID'] = dim_department.index + 1
    dim_education = df[['Education', 'EducationField']].drop_duplicates().reset_index(drop=True)
    dim_education['EducationID'] = dim_education.index + 1
    dim_job_roles = df[['JobRole', 'JobLevel', 'JobInvolvement', 'HourlyRate',
                        'StockOptionLevel', 'WorkLifeBalance']].drop_duplicates().reset_index(drop=True)
    dim_job_roles['JobRoleID'] = dim_job_roles.index + 1

    return employee_fact, dim_demographics, dim_business_travel, dim_department, dim_education, dim_job_roles

employee_fact, dim_demographics, dim_business_travel, dim_department, dim_education, dim_job_roles = transform_data(df)

db_path = 'sqlite:////workspace/database.db'
engine = create_engine(db_path)

employee_fact.to_sql('Employee_Fact', engine, if_exists='replace', index=False)
dim_demographics.to_sql('Dim_Demographics', engine, if_exists='replace', index=False)
dim_business_travel.to_sql('Dim_BusinessTravel', engine, if_exists='replace', index=False)
dim_department.to_sql('Dim_Department', engine, if_exists='replace', index=False)
dim_education.to_sql('Dim_Education', engine, if_exists='replace', index=False)
dim_job_roles.to_sql('Dim_JobRoles', engine, if_exists='replace', index=False)

print("ETL process completed successfully.")