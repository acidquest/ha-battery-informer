# Battery Informer

`Battery Informer` — сторонняя интеграция для Home Assistant с установкой через HACS. Она автоматически находит поддерживаемые батарейные сенсоры, отслеживает разряд и отправляет уведомления через выбранный `notify` сервис, например через Telegram.

## Возможности

- автоматическое обнаружение поддерживаемых батарейных сенсоров в Home Assistant
- контроль двух уровней разряда: `warning` и `critical`
- отправка уведомлений только при смене уровня, без спама на каждом обновлении
- поддержка любого существующего `notify` сервиса
- исключение отдельных сущностей из мониторинга через настройки интеграции
- мультиязычные UI-тексты и уведомления по языку Home Assistant

## Что считается поддерживаемой батарейной сущностью

В версии `0.1.0` логика намеренно строгая, чтобы минимизировать ложные срабатывания.

Сущность попадает под мониторинг, только если одновременно выполняются все условия:

- домен сущности: `sensor`
- `device_class`: `battery`
- состояние числовое
- значение в диапазоне `0..100`
- единица измерения `%` или отсутствует

В `v1` не поддерживаются:

- `binary_sensor` с признаком low battery
- эвристики по имени сущности
- vendor-specific атрибуты вроде `battery_level`, `low_battery` и подобные

## Логика уведомлений

Интеграция использует три внутренних состояния:

- `normal`
- `warning`
- `critical`

Уведомление отправляется только при переходе между уровнями:

- `normal -> warning`
- `normal -> critical`
- `warning -> critical`
- `warning -> normal`
- `critical -> normal`

Уведомление не отправляется:

- при начальном снимке состояний после запуска Home Assistant
- когда процент изменился, но уровень остался тем же
- когда состояние сущности `unknown`, `unavailable` или не подходит под правила детекта

## Установка через HACS

1. Откройте HACS.
2. Добавьте этот репозиторий как `Custom repository` с типом `Integration`.
3. Установите `Battery Informer`.
4. Перезапустите Home Assistant.
5. Перейдите в `Settings -> Devices & Services`.
6. Добавьте интеграцию `Battery Informer`.

## Первичная настройка

При добавлении интеграции запрашиваются:

- `Warning threshold (%)`
- `Critical threshold (%)`
- `Notify service name`

Правила валидации:

- оба порога должны быть в диапазоне `1..100`
- `critical` должен быть строго меньше `warning`
- указанный `notify` сервис должен существовать в Home Assistant

## Настройка Telegram

Если у вас уже настроен Telegram Bot как `notify` сервис, в поле нужно указывать только имя сервиса внутри домена `notify`.

Примеры:

- для `notify.telegram` укажите `telegram`
- для `notify.telegram_home` укажите `telegram_home`

Полное имя `notify.telegram` вводить не нужно.

## Параметры интеграции

После создания интеграции в `Options` можно изменить:

- warning threshold
- critical threshold
- notify service
- excluded battery sensors

Список исключений строится из найденных батарейных сенсоров. Если исключённая сущность временно пропадёт из Home Assistant, её `entity_id` сохранится в настройках.

## Пример поведения

Если заданы:

- warning threshold = `20`
- critical threshold = `10`

Тогда:

- `34% -> 19%`: отправится warning-уведомление
- `19% -> 18%`: уведомления не будет
- `18% -> 10%`: отправится critical-уведомление
- `10% -> 9%`: уведомления не будет
- `9% -> 28%`: отправится уведомление о восстановлении

## Примеры текстов уведомлений

- `Battery low: Window Sensor Battery (sensor.window_sensor_battery) is at 19%. Warning threshold: 20%.`
- `Battery critical: Door Lock Battery (sensor.door_lock_battery) is at 8%. Replace or recharge the battery soon. Critical threshold: 10%.`
- `Battery recovered: Motion Sensor Battery (sensor.motion_sensor_battery) is back to 52% and above the warning threshold.`
- `Низкий заряд батареи: Window Sensor Battery (sensor.window_sensor_battery) имеет 19%. Порог предупреждения: 20%.`
- `Критический заряд батареи: Door Lock Battery (sensor.door_lock_battery) имеет 8%. Замените батарею или зарядите устройство как можно скорее. Критический порог: 10%.`
- `Заряд восстановлен: Motion Sensor Battery (sensor.motion_sensor_battery) снова имеет 52% и находится выше порога предупреждения.`

## Поддержка языков

Интеграция использует активный язык Home Assistant.

В первом релизе поддерживаются:

- English
- Русский

Что локализовано:

- тексты `config_flow` и `options_flow`
- runtime-уведомления о warning, critical и recovery

Если язык Home Assistant не `ru`, интеграция использует английский язык по умолчанию.

## Ограничения текущей версии

- интеграция не создаёт собственные сенсоры или устройства
- детект батарейных сущностей намеренно консервативный
- текст уведомлений пока не настраивается через UI
- интеграция работает только с теми значениями батареи, которые уже есть в Home Assistant

## Структура проекта

Основные файлы:

- `custom_components/battery_informer/manifest.json`
- `custom_components/battery_informer/config_flow.py`
- `custom_components/battery_informer/manager.py`
- `custom_components/battery_informer/detector.py`
- `custom_components/battery_informer/strings.json`
- `hacs.json`
- `brand/icon.svg`
- `brand/logo.svg`

## Релизы и changelog

- текущие изменения ведутся в [CHANGELOG.md](./CHANGELOG.md)
- шаблон генерации GitHub release notes лежит в [`.github/release.yml`](./.github/release.yml)

Рекомендуемый формат релиза:

1. Обновить версию в `custom_components/battery_informer/manifest.json`.
2. Добавить запись в `CHANGELOG.md`.
3. Создать git tag вида `v0.1.1`.
4. Опубликовать GitHub Release.

## Локальная проверка

```bash
python3 -m compileall custom_components tests
pytest -q tests
```

## Планы на развитие

- поддержка `binary_sensor` low-battery
- настраиваемые шаблоны сообщений
- ручной include-only режим
- сервис для отправки тестового уведомления
