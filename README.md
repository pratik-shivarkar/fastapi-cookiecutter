# FastAPI CookieCutter

## Features
- JWT
- OTP Login & Password Reset
- Emailing
- SQLAlchemy
- RBAC
- Login History
- CORS
- Modularity
- Admin API (WIP)

## License

MIT licensed.

## Using Cookie-Cutter

```bash
pip3 install cookiecutter
cookiecutter https://github.com/pratik-shivarkar/fastapi-cookiecutter.git
```

**Project name should not use special characters except _ (underscore)**

```bash
cd {project_name}
pip install .
```

Once installed the `project_name` command will be available

### Required environment variables

- `PYTHONUNBUFFERED` set to 1 when using Docker
- `AUTH_MODE` set value to `native` or `api-gateway`
- `AUTH_HEADER` set value to authenticated user header when using `api-gateway` based authentication
- `MASTER_DB_URI` URI for postgres master database and master user (will be used for creating project role and database)
- `DB_URI` URI for project database, role, and password
- `DB_PASSWORD` password for project database
- `SECRET_KEY` secret key for JWT
- `REFRESH_KEY` secret key for JWT refresh tokens
- `SMTP_SERVER` SMTP server host
- `SMTP_PORT` SMTP server port
- `SMTP_USERNAME` SMTP server username
- `SMTP_PASSWORD` SMTP server password
- `SENDER_EMAIL` SMTP sender email
- `ORIGINS` Comma separated origins to allow (eg. https://example.com,http://localhost:8080)

## Command Reference

```bash
Usage: project_name [OPTIONS] COMMAND [ARGS]...

Options:
  --production / --no-production
  --help                          Show this message and exit.

Commands:
  clean
  init
  run
  test
```


#### Create database and schema
```bash
project_name init
```

#### Clean database and schema
```bash
project_name clean
```

#### Run application
```bash
project_name run
```

#### Run tests
```bash
project_name test
```