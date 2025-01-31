import csv
from datetime import datetime, timedelta
import random

# Dane przykładowe
users = [
    {"name": "jan.kowalski", "role": "Developer", "team": "Backend"},
    {"name": "anna.nowak", "role": "Developer", "team": "Frontend"},
    {"name": "piotr.wisniewski", "role": "QA", "team": "Testing"},
    {"name": "maria.dabrowska", "role": "Developer", "team": "Mobile"},
    {"name": "tomasz.lewandowski", "role": "PM", "team": "Management"},
    {"name": "ewa.wojcik", "role": "QA", "team": "Testing"},
    {"name": "adam.kaczmarek", "role": "Developer", "team": "Backend"},
    {"name": "zofia.zielinska", "role": "Developer", "team": "Frontend"}
]

projects = [
    "PROJ-1: E-commerce Platform",
    "PROJ-2: Mobile App",
    "PROJ-3: CRM System",
    "PROJ-4: Analytics Dashboard",
    "PROJ-5: API Integration"
]

tasks = {
    "Development": [
        "Implementation",
        "Code Review",
        "Bug Fix",
        "Refactoring",
        "Documentation"
    ],
    "QA": [
        "Test Case Creation",
        "Manual Testing",
        "Automated Testing",
        "Regression Testing",
        "Bug Reporting"
    ],
    "PM": [
        "Sprint Planning",
        "Team Meeting",
        "Client Meeting",
        "Documentation",
        "Resource Planning"
    ]
}

# Generowanie danych
start_date = datetime.now() - timedelta(days=30)
worklogs = []

for _ in range(100):
    user = random.choice(users)
    project = random.choice(projects)
    
    # Wybierz odpowiednie zadania bazując na roli
    if user["role"] == "Developer":
        task_type = "Development"
    elif user["role"] == "QA":
        task_type = "QA"
    else:
        task_type = "PM"
    
    task = random.choice(tasks[task_type])
    
    # Losowa data z ostatnich 30 dni (tylko dni robocze)
    random_days = random.randint(0, 30)
    log_date = start_date + timedelta(days=random_days)
    while log_date.weekday() >= 5:  # Pomijamy weekendy
        log_date += timedelta(days=1)
    
    # Losowa liczba godzin (4-8 godzin)
    hours = random.randint(4, 8)
    
    worklogs.append({
        "user_name": user["name"],
        "role": user["role"],
        "team": user["team"],
        "project": project,
        "task": task,
        "hours": hours,
        "date": log_date.strftime("%Y-%m-%d")
    })

# Zapisz do CSV
with open('sample_worklogs.csv', 'w', newline='', encoding='utf-8') as file:
    writer = csv.DictWriter(file, fieldnames=["user_name", "role", "team", "project", "task", "hours", "date"])
    writer.writeheader()
    writer.writerows(worklogs)

print("Wygenerowano przykładowe dane do pliku sample_worklogs.csv") 