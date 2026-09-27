$ErrorActionPreference = 'Stop'

function Run-Step {
    param (
        [string]$Title,
        [scriptblock]$Command
    )
    Write-Host "`n[STEP] $Title..." -ForegroundColor Cyan
    & $Command
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Etape echouee : $Title (Code : $LASTEXITCODE)" -ForegroundColor Red
        Write-Host "[STOP] Arret du script." -ForegroundColor Red
        exit $LASTEXITCODE
    }
    Write-Host "[OK] Etape reussie." -ForegroundColor Green
}

# 1. Verification Django
Run-Step "Verification Django (Check)" {
    poetry run python manage.py check
}

# 2. Detection des migrations
Run-Step "Detection des migrations" {
    poetry run python manage.py makemigrations core rbac crm sales receivables users
}

# 3. Application des migrations
Run-Step "Application des migrations" {
    poetry run python manage.py migrate
}

# 4. Tests unitaires
Run-Step "Execution des tests Pytest" {
    poetry run pytest
}

# 5. Demarrage du serveur
Write-Host "`n[START] Lancement du serveur sur http://0.0.0.0:7000..." -ForegroundColor Green
poetry run python manage.py runserver 0.0.0.0:7000