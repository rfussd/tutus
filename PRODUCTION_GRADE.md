# De 8 a 10 — Production-grade Checklist

## 1. CD / Publicación
- [ ] **PyPI**: Configurar `twine` + GitHub Action para publicar `tutus` en PyPI al hacer tag (v*)
- [ ] **Installer Windows**: Usar `PyInstaller` + GitHub Action para buildear `.exe` auto-contenido
- [ ] **Release automation**: GitHub Action que al pushear tag v* genere release notes + assets (exe, wheel)

## 2. Coverage obligatorio
- [ ] **Fijar mínimo 90%**: `[tool.coverage.report] fail_under = 90` en pyproject.toml
- [ ] **Métrica exacta**: CI debe fallar si coverage baja del mínimo
- [ ] **Cobertura real hoy**: ejecutar `pytest --cov --cov-report=term-missing` y ver qué módulos están pobres
- [ ] **Tests faltantes**: engine.py, pipeline.py, direct_voice.py, hotword.py, web/server.py, ui/window.py

## 3. Benchmarks (CI)
- [ ] **LLM call latency**: test que mide tiempo de `classify()` + `think()` con mock y alerta si > X ms
- [ ] **RAG query time**: benchmark de ChromaDB retrieval
- [ ] **Voice pipeline**: TTS + STT latencia (mockeando modelos)
- [ ] **Startup time**: test que mide `import tutus` y `TutusEngine()` creación
- [ ] **Regresión**: comparar contra baseline en cada PR

## 4. Security Audit (CI)
- [ ] **`pip-audit`**: agregar a CI job que revisa dependencias por CVEs conocidos
- [ ] **Bandit**: scanner estático de seguridad en el código
- [ ] **Secrets scanning**: `trufflehog` o `gitleaks` en CI para evitar commits con tokens
- [ ] **Sandbox**: revisar que `code_sandbox_skill.py` no tenga escapes (AST analysis + lista negra)
- [ ] **Dependabot**: activar en GitHub para PRs automáticos de updates

## 5. Badges reales
- [ ] **Repo real**: el badge de CI apunta a `dan/tutus` que no existe → cambiarlo al repo real
- [ ] **Coverage badge**: conectar codecov o coveralls al repo real
- [ ] **License badge**: apuntar a `LICENSE` real

## 6. Changelog / Releases
- [ ] **`CHANGELOG.md`**: mantener registro de cambios por versión (mantener manual o con `git-cliff`)
- [ ] **Versionado semántico**: `MAJOR.MINOR.PATCH` en `pyproject.toml`
- [ ] **GitHub Releases**: Action que al pushear tag v* genere release automático
- [ ] **`__version__`**: definir en `core/__init__.py` para acceso programático

## 7. Monitoreo / Telemetría
- [ ] **Logging estructurado**: usar `structlog` o JSON logs
- [ ] **Métricas**: contadores de queries, errores, latencia (exportables vía web)
- [ ] **Health check endpoint**: web server `/api/health` ya existe, extenderlo con uptime, versión
- [ ] **Error tracking**: Sentry opcional (opt-in) para bugs en producción

## Orden sugerido
1. Coverage real → métrica → mínimo obligatorio en CI
2. pip-audit + bandit + secret scanning en CI
3. Changelog + versionado + GitHub Releases
4. CD (PyPI + exe)
5. Benchmarks
6. Badges reales
7. Monitoreo
