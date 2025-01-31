
# Jira Analysis - Pełna wersja aplikacji

## 📌 Wymagania systemowe:
- Python 3.8+
- Docker (opcjonalnie)
- Biblioteki wymagane do działania aplikacji

## 📥 Instalacja lokalna

1️⃣ Pobierz aplikację i rozpakuj ZIP.
2️⃣ Zainstaluj wymagane zależności:
```
pip install -r requirements.txt
```
3️⃣ Uruchom aplikację:
```
python app.py
```
4️⃣ Otwórz aplikację w przeglądarce:
```
http://127.0.0.1:5000/
```

## 🐳 Uruchomienie w Dockerze

1️⃣ Zbuduj obraz Docker:
```
docker build -t jira-analysis .
```
2️⃣ Uruchom kontener:
```
docker run -p 5000:5000 jira-analysis
```
3️⃣ Otwórz aplikację:
```
http://localhost:5000/
```

## 🎯 Kluczowe funkcjonalności:
✅ Pobieranie logów pracy z Jira (taski, przekierowania)  
✅ Przypisywanie użytkowników do portfeli klientów i projektów  
✅ Analiza aktywności użytkowników (wykresy, heatmapa)  
✅ Eksport raportów do CSV/PDF  
✅ Superadmin (pełne uprawnienia)  
