"""
Copyright (C) Pratik Shivarkar - All Rights Reserved

This source code is protected under international copyright law.  All rights
reserved and protected by the copyright holders.
This file is confidential and only available to authorized individuals with the
permission of the copyright holders.  If you encounter this file and do not have
permission, please contact the copyright holders and delete this file.
"""


import os

from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.modules import auth
from app.internal import admin
from app.config import logger, origins


app = FastAPI()

app.include_router(
    admin.router,
    prefix="/admin",
    tags=['admin']
)

app.include_router(
    auth.router,
    prefix="/auth",
    tags=['auth']
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ServiceResponse(BaseModel):
    service: str = "{{cookiecutter.project_name}}-backend"
    docs: str = "http://localhost:8080/docs"
    redoc: str = "http://localhost:8080/redoc"
    version: str = "0.0.1a"


@app.on_event("startup")
async def startup_event():
    logger.info(f"Auth mode: {os.getenv('AUTH_MODE')}")


@app.get("/", response_model=ServiceResponse)
async def index():
    return ServiceResponse()
