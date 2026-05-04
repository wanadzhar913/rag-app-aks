#!/bin/sh
set -eu

APP_ENV="${APP_ENV:-${ENVIRONMENT:-development}}"

load_env_file() {
    env_file="$1"
    echo "Loading environment from ${env_file}"

    while IFS= read -r line || [ -n "$line" ]; do
        case "$line" in
            "" | \#*)
                continue
                ;;
        esac

        key=${line%%=*}
        eval "current_value=\${$key-}"

        if [ -z "$current_value" ]; then
            export "$line"
        else
            echo "Keeping existing value for ${key}"
        fi
    done < "$env_file"
}

echo "Starting with these environment variables:"
echo "APP_ENV: ${APP_ENV}"
echo "Initial Database Host: $( [ -n "${POSTGRES_HOST:-${DB_HOST:-}}" ] && echo "set" || echo "Not set" )"
echo "Initial Database Port: $( [ -n "${POSTGRES_PORT:-${DB_PORT:-}}" ] && echo "set" || echo "Not set" )"
echo "Initial Database Name: $( [ -n "${POSTGRES_DB:-${DB_NAME:-}}" ] && echo "set" || echo "Not set" )"
echo "Initial Database User: $( [ -n "${POSTGRES_USER:-${DB_USER:-}}" ] && echo "set" || echo "Not set" )"

if [ -f ".env.${APP_ENV}" ]; then
    load_env_file ".env.${APP_ENV}"
elif [ -f ".env" ]; then
    load_env_file ".env"
else
    echo "Warning: No .env file found. Using system environment variables."
fi

if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "ERROR: OPENAI_API_KEY is required."
    exit 1
fi

echo
echo "Final environment configuration:"
echo "Environment: ${APP_ENV}"
echo "Database Host: $( [ -n "${POSTGRES_HOST:-${DB_HOST:-}}" ] && echo "set" || echo "Not set" )"
echo "Database Port: $( [ -n "${POSTGRES_PORT:-${DB_PORT:-}}" ] && echo "set" || echo "Not set" )"
echo "Database Name: $( [ -n "${POSTGRES_DB:-${DB_NAME:-}}" ] && echo "set" || echo "Not set" )"
echo "Database User: $( [ -n "${POSTGRES_USER:-${DB_USER:-}}" ] && echo "set" || echo "Not set" )"
echo "LLM Model: ${DEFAULT_LLM_MODEL:-Not set}"
echo "Debug Mode: ${DEBUG:-false}"

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    echo "Running Alembic migrations"
    uv run alembic upgrade head
fi

exec "$@"
