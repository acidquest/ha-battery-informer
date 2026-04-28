# Changelog

Все заметные изменения в проекте `Battery Informer` фиксируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/), а версии рекомендуется вести по [Semantic Versioning](https://semver.org/lang/ru/).

## [Unreleased]

### Added

- сервис `battery_informer.send_test_notification` для проверки отправки уведомлений
- сенсор `Tracked batteries` с атрибутами по всем найденным батарейкам
- сенсор `Critical batteries` с атрибутами по батарейкам в критическом уровне
- локальные PNG-ассеты брендинга внутри `custom_components/battery_informer/brand/`
- настраиваемый параметр `Full rescan interval (minutes)` для периодического полного поиска батареек
- поддержка `binary_sensor` low-battery
- настраиваемые шаблоны уведомлений через UI
- режим мониторинга `include only`

### Changed

- выбор notify-цели в UI теперь поддерживает `notify` entities и legacy `notify.<service>`
- валидация notify-цели переведена на entity registry и legacy service lookup
- поиск батареек теперь совмещает стартовый snapshot, `state_changed` и периодический full rescan

## [0.1.0] - 2026-04-27

### Added

- HACS-совместимый каркас кастомной интеграции
- UI-настройка через `config_flow` и `options_flow`
- автоматическое обнаружение поддерживаемых батарейных сенсоров
- контроль уровней `warning` и `critical`
- уведомления через настраиваемый `notify` сервис
- список исключённых сущностей
- мультиязычность по языку Home Assistant: English и Русский
- базовые unit-тесты
- бренд-ассеты `brand/icon.svg` и `brand/logo.svg`
- русскоязычная документация и шаблон GitHub release notes
