# Data Model

## Institution

id
name

## Teacher

id
institution_id
name
email

## Student

id
institution_id
student_id
roll_number
name
class
section

## Attendance Session

id
institution_id
teacher_id
subject
date
created_at

## Attendance Result

id
session_id
student_id
status
confidence
source

## ERP Connection

id
institution_id
erp_type
status