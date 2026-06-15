# АИС «Электронная библиотека»

Flask-приложение на Flask-SQLAlchemy с Blueprint-структурой и миграциями Flask-Migrate.

## Установка

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Миграции

Перед первым запуском укажите приложение:

```powershell
$env:FLASK_APP = "app"
```

Инициализация папки миграций:

```powershell
flask db init
```

Создание миграции по моделям:

```powershell
flask db migrate -m "Initial schema"
```

Применение миграций к SQLite-базе `library.db`:

```powershell
flask db upgrade
```

Заполнение ролей, жанров и тестовых пользователей:

```powershell
flask seed-db
```

Запуск:

```powershell
flask run
```

Тестовые пользователи: `admin/admin`, `moderator/moderator`, `user/user`.
