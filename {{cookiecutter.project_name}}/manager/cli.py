"""
Copyright (C) Pratik Shivarkar - All Rights Reserved

This source code is protected under international copyright law.  All rights
reserved and protected by the copyright holders.
This file is confidential and only available to authorized individuals with the
permission of the copyright holders.  If you encounter this file and do not have
permission, please contact the copyright holders and delete this file.
"""


import os
import sys
import click
from datetime import date
from urllib.parse import urlparse
from sqlalchemy.orm import Session
from hypercorn.asyncio import serve
from hypercorn.config import Config
from sqlalchemy import create_engine, sql
from dotenv import load_dotenv, find_dotenv

from app.config import logger
from models import UserBase
from models.user import User, Role, Permission, Resource, Policy

load_dotenv(find_dotenv())

# Platform specific imports
try:
    import uvloop
except ImportError:
    import asyncio
else:
    import asyncio


# TODO: Change commit  code to "commit as you go" style.
# Ref: https://docs.sqlalchemy.org/en/14/tutorial/dbapi_transactions.html#committing-changes


class RootOptions(object):
    def __init__(self, production: bool):
        self.production: bool = production


@click.group()
@click.option("--production/--no-production", default=False)
@click.pass_context
def cli(ctx, production):
    click.echo("Production mode is %s" % ('on' if production else 'off'))
    if production:
        os.environ["PRODUCTION"] = "1"
    else:
        os.environ["PRODUCTION"] = "0"

    if not os.getenv("AUTH_MODE") or os.getenv("AUTH_MODE") != "native":
        click.secho("WARNING! SERVER RUNNING WITHOUT NATIVE SECURITY, ENSURE PRIVATE DEPLOYMENT BEHIND API GATEWAY",
                    fg="yellow")
    ctx.obj = RootOptions(production)


@cli.command()
@click.argument("connection_uri", envvar="MASTER_DB_URI")
@click.argument("db_password", envvar="DB_PASSWORD")
@click.pass_obj
def init(options, connection_uri, db_password):
    click.echo("Initializing database ...")
    try:
        engine = create_engine(connection_uri, future=True)
        conn = engine.connect()
        conn.execute(sql.text("commit"))
        conn.execute(sql.text("CREATE DATABASE {{cookiecutter.project_name}}"))
        conn.close()
    except Exception as e:
        click.secho("Failed to create database ...", fg="red")
        click.echo(e)
    else:
        click.secho("Database created successfully ...", fg="green")

    try:
        engine = create_engine(connection_uri, future=True)
        conn = engine.connect()
        conn.execute(sql.text("commit"))
        create_user_query = sql.text(
            "CREATE USER {{cookiecutter.project_name}} WITH PASSWORD :password;"
        )
        conn.execute(create_user_query, {"password": db_password})
        conn.close()
    except Exception as e:
        click.secho("Failed to create user ...", fg="red")
        click.echo(e)
    else:
        click.secho("User '{{cookiecutter.project_name}}' created successfully ...", fg="green")

    try:
        parsed_uri = urlparse(connection_uri)
        parsed_uri = parsed_uri._replace(path="/{{cookiecutter.project_name}}").geturl()
        engine = create_engine(parsed_uri, future=True)
        conn = engine.connect()
        conn.execute(sql.text("commit"))
        conn.execute(sql.text("GRANT CONNECT ON DATABASE {{cookiecutter.project_name}} TO {{cookiecutter.project_name}};"))
        conn.execute(sql.text("GRANT USAGE ON SCHEMA public TO {{cookiecutter.project_name}};"))
        conn.execute(sql.text("""
            GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO {{cookiecutter.project_name}};
            GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO {{cookiecutter.project_name}};
        """))
        conn.execute(sql.text("""
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
        GRANT ALL ON TABLES TO {{cookiecutter.project_name}};
        
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
        GRANT ALL ON SEQUENCES TO {{cookiecutter.project_name}};
        """))
        conn.close()
    except Exception as e:
        click.secho("Failed to assign db privileges ...", fg="red")
        click.echo(e)
    else:
        click.secho("User '{{cookiecutter.project_name}}' given priviledges successfully ...", fg="green")

    try:
        parsed_uri = urlparse(connection_uri)
        parsed_uri = parsed_uri._replace(path="/{{cookiecutter.project_name}}").geturl()
        engine = create_engine(parsed_uri, future=True)
        UserBase.metadata.create_all(engine)
    except Exception as e:
        click.secho("Failed to implement database models ...", fg="red")
        click.echo(e)
    else:
        click.secho("Database models initialized successfully ...", fg="green")

    if not options.production:
        try:
            parsed_uri = urlparse(connection_uri)
            parsed_uri = parsed_uri._replace(path="/{{cookiecutter.project_name}}").geturl()
            engine = create_engine(parsed_uri, future=True)
            session = Session(engine)

            admin_role = Role(title='Admin')
            session.add(admin_role)
            session.commit()
            session.refresh(admin_role)

            resource_all = Resource(name='*')
            session.add(resource_all)
            session.commit()
            session.refresh(resource_all)

            admin_permission = Permission(action='*', resource_id=resource_all.id)
            session.add(admin_permission)
            session.commit()
            session.refresh(admin_permission)

            admin_policy = Policy(name='Admin', permission_id=admin_permission.id, role_id=admin_role.id)
            session.add(admin_policy)
            session.commit()
            session.refresh(admin_policy)

            admin_user = User(
                first_name='Pratik',
                last_name='Shivarkar',
                username='pratik.shivarkar',
                phone_number='+19999999998',
                email='pratik@shivarkar.org',
                role_id=admin_role.id,
                dob=date(1989, 1, 1)
            )
            admin_user.set_password("reset123")
            session.add(admin_user)
            session.commit()
            session.refresh(admin_user)
        except Exception as e:
            click.secho("Failed to insert development data ...", fg="red")
            click.echo(e)
        else:
            click.secho("Development data added ...", fg="green")


@cli.command()
@click.pass_obj
def test(options):
    click.echo("Running tests ...")


@cli.command()
@click.argument("connection_uri", envvar="DB_URI")
@click.pass_obj
def run(options, connection_uri):
    from app.main import app
    click.secho("Checking configuration ...", fg="yellow")
    try:
        urlparse(connection_uri)._replace(path="/{{cookiecutter.project_name}}").geturl()
        assert (hasattr(options, 'production'))
    except Exception as e:
        click.echo(e)
        click.secho("Failed to validate database URI and password", fg="red")

    click.secho("Starting server ...", fg="yellow")
    config = Config()
    config.bind = ["0.0.0.0:8080"]
    config.errorlog = logger
    config.accesslog = logger
    if options.production:
        config.loglevel = "DEBUG"
    else:
        config.loglevel = "INFO"

    if 'uvloop' in sys.modules:
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(serve(app, config))
    else:
        asyncio.run(serve(app, config))


@cli.command()
@click.argument("connection_uri", envvar="MASTER_DB_URI")
@click.pass_obj
def clean(options, connection_uri):
    click.secho("CLEAR ALL DATA AND DATABASES ...", fg="red")
    if click.confirm("Do you want to continue?"):
        click.echo("This will clear all data")
        try:
            engine = create_engine(connection_uri, future=True)
            conn = engine.connect()
            conn.execute(sql.text("commit"))
            conn.execute(sql.text("DROP DATABASE IF EXISTS {{cookiecutter.project_name}}"))
            conn.execute(sql.text("DROP USER IF EXISTS {{cookiecutter.project_name}}"))
            conn.close()
        except Exception as e:
            click.secho("Failed to clean all data ...", fg="red")
            click.echo(e)
        else:
            click.secho("All data and databases are removed ...", fg="green")
            click.echo("Run `{{cookiecutter.project_name}} init` to initialize database again.")
