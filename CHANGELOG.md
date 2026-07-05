# Changelog

## [2.0.0] — 2026-07-05

### Added
- **Mypy strict**: 0 errores en todo el código base
- **UI Tests**: 14 tests offscreen para avatar, chat_bubble, chat_area, input_bar, indicators, theme
- **Skill Tests**: 57 tests para code_sandbox, vision_skill, window_control_skill
- **Integration Tests**: 15 tests para web server, pipeline, plugin_loader, user_profile
- **CI/CD**: Jobs separados para lint, typecheck, test (3 Python versions), security
- **Security**: pip-audit + bandit en CI, Pillow actualizado (CVE fixes)
- **Coverage**: fail_under = 40% en CI
- **README**: Badges actualizados, tabla de tests, instrucciones dev install

### Changed
- `Pillow>=12.2` (arregla 6 CVEs)
- Dependencias dev: pytest-cov, pip-audit, bandit

### Fixed
- 0 errores de mypy strict en todo el proyecto
- 0 errores de ruff
- 207 → 287 tests, 0 fallan

## [1.0.0] — 2026-06-XX

### Added
- Proyecto inicial: UI PyQt6, agentes multi-dominio, skills, RAG, voz
