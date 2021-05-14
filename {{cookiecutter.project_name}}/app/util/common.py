"""
Copyright (C) Pratik Shivarkar - All Rights Reserved

This source code is protected under international copyright law.  All rights
reserved and protected by the copyright holders.
This file is confidential and only available to authorized individuals with the
permission of the copyright holders.  If you encounter this file and do not have
permission, please contact the copyright holders and delete this file.
"""


from pydantic import BaseModel


# --Schemas--

class Address(BaseModel):
    address_line1: str
    address_line2: str
    state: str
    country: str
    zip: str


# --Requests--

# --Response--

class CommonResponse(BaseModel):
    message: str


