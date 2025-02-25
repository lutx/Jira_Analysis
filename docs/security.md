# Zabezpieczenia API

## CSRF Protection
Wszystkie modyfikujące endpointy (POST, PUT, PATCH, DELETE) wymagają tokenu CSRF.

### Jak używać:
1. Pobierz token CSRF:
```bash
curl http://api.example.com/api/csrf-token
```

2. Użyj tokenu w nagłówku:
```bash
curl -X POST \
  -H "X-CSRF-Token: <token>" \
  http://api.example.com/api/teams/1/export/workload
```

### Obsługa błędów:
- 400 Bad Request - brak lub nieprawidłowy token CSRF
- 403 Forbidden - wygasły token CSRF 

## Rate Limiting
API posiada limity requestów dla ochrony przed nadużyciami:

- `/api/csrf-token`: 10 requestów/minutę
- Pozostałe endpointy: 200 requestów/dzień, 50 requestów/godzinę

### Obsługa błędów rate limitingu:
- 429 Too Many Requests - przekroczono limit requestów
- Nagłówek `Retry-After` informuje o czasie do resetu limitu

## Monitorowanie bezpieczeństwa
System monitoruje:
- Próby ataków CSRF
- Przekroczenia limitów requestów
- Podejrzane wzorce ruchu

Alerty są wysyłane do zespołu bezpieczeństwa przy wykryciu anomalii. 