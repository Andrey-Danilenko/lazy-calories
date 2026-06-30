# CI/CD: настройка и деплой

Документ описывает, как устроены CI/CD пайплайны проекта и как настроить деплой
на VPS «в одну кнопку» из GitHub.

## Что есть в проекте

| Файл | Назначение |
|---|---|
| `.github/workflows/ci.yml` | **CI** — на каждый push и pull request проверяет `ruff format` и `ruff check`. |
| `.github/workflows/deploy.yml` | **CD** — деплой на VPS вручную по кнопке (`workflow_dispatch`). |
| `Dockerfile` | Образ бота на базе официального uv-образа (Python 3.14). |
| `docker-compose.yml` | Запуск контейнера на VPS с volume для данных и `.env`. |
| `.dockerignore` | Что не попадает в образ (`.venv`, `.git`, данные, секреты). |

---

## CI — проверка кода

`ci.yml` запускается автоматически на каждый commit (push) и pull request. Шаги:

1. Установка [uv](https://github.com/astral-sh/uv) (`astral-sh/setup-uv`).
2. `uv sync --frozen --no-install-project` — установка зависимостей из `uv.lock`.
3. `ruff format --check .` — падает, если код не отформатирован.
4. `ruff check .` — падает, если есть нарушения линтера.

Никакой настройки не требуется — пайплайн работает сразу после пуша в репозиторий.

Чтобы починить упавший CI локально перед пушем:

```bash
uv run ruff format .
uv run ruff check --fix .
```

---

## CD — деплой на VPS

Деплой запускается вручную: **GitHub → вкладка Actions → Deploy → Run workflow**.
Workflow заходит на VPS по SSH, подтягивает свежий код и пересобирает контейнер:

```bash
git pull --ff-only
docker compose up -d --build
docker image prune -f
```

### Шаг 1. Подготовка VPS

На сервере должны быть установлены **git**, **Docker** и **Docker Compose plugin**.

```bash
# Docker + compose plugin (Debian/Ubuntu)
curl -fsSL https://get.docker.com | sh

# Клонируем репозиторий в рабочую папку
sudo mkdir -p /opt/lazy-calories
sudo chown "$USER" /opt/lazy-calories
git clone https://github.com/Andrey-Danilenko/lazy-calories.git /opt/lazy-calories
cd /opt/lazy-calories
```

Создаём `.env` рядом с `docker-compose.yml` (он **не** хранится в git и **не**
попадает в образ — читается контейнером во время запуска):

```bash
cp .env-template .env
nano .env   # заполняем DEEPSEEK_API_KEY, TELEGRAM_BOT_TOKEN, LANGSMITH_* и т.д.
```

Проверяем, что всё запускается вручную:

```bash
docker compose up -d --build
docker compose logs -f        # должно появиться "Starting bot..."
```

Папки `stored_data/` и `logs/` монтируются как volume, поэтому данные пользователей
переживают пересборку контейнера.

### Шаг 2. SSH-ключ для GitHub Actions

Создаём **отдельный** ключ для деплоя (на своей машине или на VPS):

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f deploy_key -N ""
```

Появятся два файла:
- `deploy_key` — приватный ключ (его → в GitHub secret `VPS_SSH_KEY`);
- `deploy_key.pub` — публичный ключ (его → на VPS).

Добавляем публичный ключ в авторизованные на VPS:

```bash
cat deploy_key.pub >> ~/.ssh/authorized_keys
```

### Шаг 3. Secrets в GitHub

**Settings → Secrets and variables → Actions → New repository secret.** Заводим:

| Secret | Значение | Пример |
|---|---|---|
| `VPS_HOST` | IP или домен сервера | `203.0.113.10` |
| `VPS_USER` | Пользователь SSH | `deploy` или `root` |
| `VPS_SSH_KEY` | Приватный ключ целиком (содержимое `deploy_key`, включая строки `BEGIN`/`END`) | `-----BEGIN OPENSSH PRIVATE KEY----- …` |
| `VPS_PORT` | Порт SSH | `22` |
| `VPS_APP_DIR` | Путь к папке с проектом на VPS | `/opt/lazy-calories` |

### Шаг 4. Деплой по кнопке

1. Открываем вкладку **Actions** в репозитории.
2. Слева выбираем workflow **Deploy**.
3. Жмём **Run workflow** → **Run workflow**.

Через несколько секунд Action подключится к VPS, обновит код и перезапустит бота.
Прогресс и логи видны прямо в интерфейсе Action.

---

## Проверка и отладка

На VPS:

```bash
cd /opt/lazy-calories
docker compose ps          # статус контейнера
docker compose logs -f     # живые логи бота
docker compose restart     # ручной перезапуск
```

Частые проблемы:

- **`Permission denied (publickey)`** в Action — публичный ключ не добавлен в
  `~/.ssh/authorized_keys` нужного пользователя, либо в `VPS_SSH_KEY` лежит не тот
  ключ / не полностью (нужно содержимое приватного ключа целиком).
- **`docker: command not found`** — Docker не установлен или пользователь не в группе
  `docker` (`sudo usermod -aG docker $USER`, затем переподключиться по SSH).
- **Бот не отвечает** — проверьте `.env` на VPS и `docker compose logs`.
- **`git pull` падает** — на сервере есть локальные изменения. Деплой ожидает чистое
  дерево (`git pull --ff-only`); приведите рабочую копию в порядок (`git reset --hard`).
