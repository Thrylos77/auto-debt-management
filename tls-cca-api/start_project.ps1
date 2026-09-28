$ErrorActionPreference = 'Stop'

function Run-Step {
    param ([string]$Title, [scriptblock]$Command)
    Write-Host "`n[STEP] $Title..." -ForegroundColor Cyan
    & $Command
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Etape echouee : $Title (Code : $LASTEXITCODE)" -ForegroundColor Red
        Write-Host "[STOP] Arret du script." -ForegroundColor Red
        exit $LASTEXITCODE
    }
    Write-Host "[OK] Etape reussie." -ForegroundColor Green
}

Run-Step "Verification Django (Check)" { 
    poetry run python manage.py check 
}
Run-Step "Migration des apps platform" { 
    poetry run python manage.py makemigrations audit configuration core rbac users notifications
}
Run-Step "Migration des apps metiers" { 
    poetry run python manage.py makemigrations crm receivables reporting sales 
}
Run-Step "Application des migrations" { 
    poetry run python manage.py migrate 
}
Run-Step "Verification absence de migration manquante" { 
    poetry run python manage.py makemigrations --check --dry-run 
}
Run-Step "Apercu synchronisation RBAC (DRY-RUN)" { 
    poetry run python manage.py sync_rbac --dry-run --strict 
}
Run-Step "Synchronisation declarative RBAC" { 
    poetry run python manage.py sync_rbac --strict 
}
Run-Step "Tests Pytest + pagination sans warning" { 
    poetry run pytest -v -W error::django.core.paginator.UnorderedObjectListWarning 
}

Write-Host "`n[START] Lancement du serveur sur http://0.0.0.0:7000..." -ForegroundColor Green
poetry run python manage.py runserver 0.0.0.0:7000